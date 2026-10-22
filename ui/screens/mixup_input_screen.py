"""Traditional Mixup input: choose a real block assembly, then paint it."""
import threading
from copy import deepcopy
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from app.i18n import tr
from app.prefs import get as pref_get
from cube.articulated_observation import polygon_key,match_observations
from cube.mixup_entry import MixupEntryDraft
from cube.mixup_assembly import assemblies,inner_pattern,inner_arrangement,assembly_group
from cube.articulated import MIXUP_MODELS
from renderer.mixup_entry_view import MixupEntryView
from renderer.polyhedral_view import CUBE_PALETTE
from renderer.camera_follow import reset_camera_view
from ui.screens.articulated_screen import RigidEntryScreen
from ui.screens.mastermorphix_screen import _Swatch
from ui.widgets.mixup_entry import AssemblyCard
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.widgets.camera_follow import follow_panel
from ui.widgets.dialogs import theme_popup
from ui.widgets import metrics as m


def _assembly_label(assembly):
    pattern=inner_arrangement(assembly.pieces)
    if pattern:return tr('mixup.entry_inner_'+pattern)
    counts=assembly.counts
    return ' + '.join(tr('mixup.entry_role_count',role=tr('mixup.entry_'+role),n=counts[role])
                      for role in ('edge','centre','inner_edge') if counts[role])


def _group_assemblies(options):
    groups={}
    for assembly in options:
        groups.setdefault(assembly.group_key,[]).append(assembly)
    return tuple(tuple(group) for group in groups.values())


class MixupInputScreen(RigidEntryScreen):
    def __init__(self,**kwargs):
        Screen.__init__(self,**kwargs)
        self._cube=None;self._recorded=set();self._history=[];self._job=None;self._cancel=threading.Event()
        self._mx_state=None;self._mx_applied=None;self._mx_cube_key=None;self._mx_selected=None;self._mx_undo=[]
        self._draft=None;self._stamp=None;self._color=0;self._paint_enabled=False;self._message=''
        self._known_state_key=None;self._known_signature=None
        self._assemblies=();self._assembly_region=None;self._assembly_job=None
        self._assembly_originals={};self._clear_popup=None
        root=AdaptiveSceneLayout();self._root_layout=root
        top=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self._button(top,'back',self.back);self.title=Label(font_size='18sp');top.add_widget(self.title)
        self._button(top,'gear',self.customize);root.add_widget(top)
        self.view=MixupEntryView();self.view.on_pick=self.pick;self.preview=self.view
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=6)
        self.colors=GridLayout(cols=6,size_hint_y=None,height=m.h(42),spacing=m.h(4));panel.add_widget(self.colors)
        row=ResponsiveBoxLayout(height_px=32,gap_px=4)
        self.selection=Label(font_size='13sp');row.add_widget(self.selection)
        self.clear_area_button=self._button(row,'',self.clear_choices,DangerButton);self.clear_area_button.size_hint_x=.55
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=30,gap_px=4)
        self.kind_label=Label(font_size='12sp');row.add_widget(self.kind_label)
        panel.add_widget(row)
        self.gallery=GridLayout(cols=3,size_hint_y=None,spacing=m.h(4))
        self.gallery.bind(minimum_height=self.gallery.setter('height'))
        self.gallery_scroll=ScrollView(size_hint_y=None,height=m.h(156),do_scroll_x=False)
        self.gallery_scroll.add_widget(self.gallery);panel.add_widget(self.gallery_scroll)
        self.rotation_row=ResponsiveBoxLayout(height_px=36,gap_px=4)
        self.rotate_previous=self._button(self.rotation_row,'prev',lambda:self.rotate_assembly(-1))
        self.rotation_label=Label(font_size='12sp');self.rotation_row.add_widget(self.rotation_label)
        self.rotate_next=self._button(self.rotation_row,'next',lambda:self.rotate_assembly(1))
        panel.add_widget(self.rotation_row)
        self.hint=Label(size_hint_y=None,height=m.h(35),font_size='12sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.hint)
        row=ResponsiveBoxLayout(height_px=44,gap_px=4)
        self._button(row,'twist',self.open_twist);self._button(row,'check',self.apply,PrimaryButton)
        self._button(row,'cancel',self.cancel_matching);panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=4)
        for icon,fn in (('cube',self.assign_initial),('random',self.randomize),('clear',self.clear),
                        ('undo',self.undo),('target',lambda:reset_camera_view(self.view)),('solve',self.solve)):
            self._button(row,icon,fn)
        panel.add_widget(row)
        self.status=Label(size_hint_y=None,height=m.h(44),font_size='12sp',halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.status)
        wrapper,self.follow=follow_panel(panel,self.view)
        root.set_content(self.view,wrapper);self.add_widget(root)

    def _button(self,row,icon,fn,cls=UIButton):
        button=cls(icon_name=icon,font_size='12sp');button.bind(on_release=lambda *_:fn());row.add_widget(button);return button
    def _get_draft(self):
        if self._draft is None or self._stamp is not self._mx_state:
            self._draft=MixupEntryDraft(self._cube.puzzle_kind,self._mx_state);self._stamp=self._mx_state
            if self._mx_state is not None and (self._mx_state.get('version',0)<8 or self._draft.repaired):
                # Migration can move an old child index into its proper whole
                # piece region. Do not retain a selection of another child.
                self._mx_state=self._draft.state();self._stamp=self._mx_state
                if self._draft.repaired:self._mx_applied=None
                self._mx_selected=None;self._clear_options()
        return self._draft
    def _applied(self):return self._cube is not None and self._mx_applied==tuple(self._cube.frames)
    def _reconcile_known_state(self):
        # A full turn (or restoring a colour) can return the draft to the exact
        # playable cube we still hold. Keep that cube and its verified history;
        # rematching would discard the path used for Mixup shape reduction.
        key=(self._cube.puzzle_kind,tuple(self._cube.frames))
        if key!=self._known_state_key:
            self._known_signature=MixupEntryDraft.from_cube(self._cube).physical_signature()
            self._known_state_key=key
        signature=self._get_draft().physical_signature()
        self._mx_applied=(key[1] if signature is not None and signature==self._known_signature else None)
    def _clear_options(self):
        self._assemblies=();self._assembly_region=None;self._assembly_job=None
    def _selected(self):
        draft=self._get_draft()
        if self._mx_selected is None:return None
        bi,ci=self._mx_selected
        if not 0<=bi<len(draft.blocks) or not 0<=ci<len(draft.blocks[bi]['cells']):self._mx_selected=None;return None
        return draft.blocks[bi],draft.blocks[bi]['cells'][ci]

    def restore_legacy(self,cube,fields,known=False):
        applied=known or (fields.get('_ao_applied')==tuple(cube.frames) and not fields.get('_ao_dirty',True))
        source=fields.get('_ao_state')
        draft=(MixupEntryDraft.from_cube(cube) if applied else
               MixupEntryDraft.from_observations(cube.puzzle_kind,source) if source else MixupEntryDraft(cube.puzzle_kind))
        self._cube=cube;self._mx_state=draft.state();self._mx_cube_key=tuple(cube.frames)
        self._mx_applied=tuple(cube.frames) if applied else None;self._mx_selected=None
        self._draft=None;self._stamp=None
        if source and not applied:self._message=tr('mixup.entry_migrated')

    def on_pre_enter(self,*_):
        self._paint_enabled=False
        cube=App.get_running_app().cube
        if self._cube is not None and self._cube is not cube:
            self._mx_state=None;self._mx_applied=None;self._mx_selected=None;self._mx_undo=[];self._history=[];self._clear_options()
            self._assembly_originals={}
        self._cube=cube;self.view.set_cube(cube)
        self.view.palette=tuple(tuple(c) for c in pref_get('poly_palette_'+cube.puzzle_kind,CUBE_PALETTE))
        if self._mx_state is None or self._mx_state['kind']!=cube.puzzle_kind:
            self._mx_state=MixupEntryDraft(cube.puzzle_kind).state();self._mx_applied=None;self._recorded=set()
        elif self._mx_cube_key is not None and tuple(self._mx_cube_key)!=tuple(cube.frames):
            self._mx_state=MixupEntryDraft.from_cube(cube).state();self._mx_applied=tuple(cube.frames)
            self._mx_selected=None;self._clear_options()
            self._assembly_originals={}
        self._mx_cube_key=tuple(cube.frames);self._absorb_history();self._build_colors();self._refresh()
        self._load_assemblies();Clock.schedule_once(lambda *_:self._root_layout._adapt(),0)
    def _build_colors(self):
        self.colors.clear_widgets();self._swatches=[]
        for c,rgba in enumerate(self.view.palette):
            button=_Swatch(rgba,active=self._paint_enabled and c==self._color);button.bind(on_release=lambda *_,i=c:self.select_color(i))
            self.colors.add_widget(button);self._swatches.append(button)
    def _remember(self):
        self._absorb_history()
        self._mx_undo.append((self._cube.clone(),deepcopy(self._mx_state),self._mx_applied,self._mx_selected))
        self._mx_undo=self._mx_undo[-24:];App.get_running_app().polyhedral_solution=None
    def _absorb_history(self):
        for cube,_ in self._history:
            self._mx_undo.append((cube.clone(),MixupEntryDraft.from_cube(cube).state(),tuple(cube.frames),None))
        self._history=[];self._mx_undo=self._mx_undo[-24:]
    def _sync(self):
        self._mx_state=self._draft.state();self._stamp=self._mx_state;self._mx_applied=None
        self._reconcile_known_state()
        self.view.set_draft(self._draft,force=True)
        App.get_running_app().polyhedral_solution=None;self._message='';self._refresh()
    def _refresh(self):
        if self._cube is None:return
        draft=self._get_draft();selected=self._selected()
        linked=draft.linked_positions(self._mx_selected[0]) if selected else ()
        self.title.text=tr('directory.'+draft.kind)
        self.clear_area_button.text=tr('mixup.entry_clear_options')
        self.clear_area_button.disabled=self._job is not None or not selected
        self.view.cube=self._cube;self.view.set_draft(draft);self.view.candidate=None
        # Keep the same geometry and picking IDs before and after the first
        # edit of a generated scramble.
        self.view.selected=self._mx_selected[0]*1024+self._mx_selected[1] if selected else None
        pairs=draft.linked_cells(*self._mx_selected) if selected else ()
        self.view.linked_selection=tuple(bi*1024+ci for bi,ci in pairs)
        self.view.refresh()
        self.selection.text=tr('mixup.entry_pick')
        self.kind_label.text=tr('mixup.entry_assemblies')
        if selected:
            block,cell=selected
            shared=MIXUP_MODELS[draft.kind][1] and block['role'] in ('centre','edge')
            self.selection.text=(tr('mixup.entry_observation_position') if shared else
                                 tr('mixup.entry_position',position=tr('mixup.position_'+block['role'])))
            if len(linked)>1:self.selection.text+=' · '+tr('mixup.entry_linked')
            if cell.get('panel_role'):self.selection.text+=' · '+tr('mixup.face_'+cell['panel_role'])
            if self._assembly_job is not None:self.kind_label.text=tr('mixup.entry_loading_assemblies')
        self.hint.text=tr('mixup.entry_brush_hint' if self._paint_enabled else
                         'mixup.entry_inner_hint' if selected and selected[1].get('panel_role')=='inner_edge' else 'mixup.entry_paint_hint')
        worlds={}
        for block in draft.blocks:
            for cell in block['cells']:
                key=polygon_key(cell['world'] or cell['guide'])
                worlds[key]=max(worlds.get(key,-1),cell['color'])
        self.status.text=self._message or tr('mixup.entry_progress',done=sum(c>=0 for c in worlds.values()),total=len(worlds))
        for c,button in enumerate(self._swatches):button.active=self._paint_enabled and c==self._color;button.disabled=self._job is not None
        self.gallery.clear_widgets()
        active=self._current_assembly()
        entered=draft.assembly_at(self._mx_selected[0]) if selected else None
        if selected:
            # Keep the opening geometry as a real, reusable choice. Previously
            # this card was rebuilt from the live draft, so changing a preset
            # silently removed the only way to choose the original geometry.
            original=self._original_assembly()
            shared=MIXUP_MODELS[draft.kind][1] and selected[0]['role'] in ('centre','edge')
            original_group=assembly_group(original['assembly'].pieces) if original is not None and shared else None
            if original is not None and all(a.key!=original['assembly'].key and
                    (original_group is None or a.group_key!=original_group) for a in self._assemblies):
                source=original['assembly']
                is_active=entered is not None and (entered.key==source.key or
                    selected[0].get('assembly_source')==source.key)
                preview=entered if is_active else source
                card=AssemblyCard(preview.diagram(draft.blocks,self._mx_selected[0]),tr('mixup.entry_original_assembly'),
                    active=is_active,size_hint_y=None,height=m.h(76),disabled=self._job is not None)
                card.assembly_key=source.key
                card.bind(on_release=lambda *_,r=linked:self.restore_original(r))
                self.gallery.add_widget(card)
            for group in _group_assemblies(self._assemblies):
                assembly=active if active in group else group[0]
                preview=entered if assembly==active and entered is not None else assembly
                card=AssemblyCard(preview.diagram(draft.blocks,self._mx_selected[0]),_assembly_label(preview),
                    active=assembly==active,size_hint_y=None,height=m.h(76),disabled=self._job is not None)
                card.assembly_key=group[0].group_key
                card.bind(on_release=lambda *_,a=assembly:self.select_assembly(a));self.gallery.add_widget(card)
        rows=(len(self.gallery.children)+2)//3
        self.gallery_scroll.height=m.h(min(156,76*rows+4*max(0,rows-1)) if rows else 1)
        can_rotate=bool(selected and draft.can_rotate_assembly(self._mx_selected[0]))
        self.rotation_row._height_px=36 if selected and selected[0]['role']!='corner' else 0
        self.rotation_row.opacity=1 if self.rotation_row._height_px else 0
        self.rotation_row.disabled=not can_rotate
        self.rotation_row._sync_metrics()
        self.rotate_previous.disabled=self.rotate_next.disabled=self._job is not None or not can_rotate
        step=draft.rotation_step(self._mx_selected[0]) if selected else 1
        self.rotation_label.text=tr('mixup.entry_rotation_degrees',angle=90*selected[0]['rotation'] if selected else 0,step=90*step)
        self.refresh_theme()

    def _original_assembly(self):
        selected=self._selected()
        if selected is None or selected[0]['role'] in ('corner','inner_edge'):return None
        draft=self._get_draft();region=draft.linked_positions(self._mx_selected[0])
        entered=draft.assembly_at(self._mx_selected[0])
        if entered is not None and inner_pattern(entered.pieces) is not None:return None
        if region not in self._assembly_originals:
            assembly=draft.assembly_at(self._mx_selected[0])
            if assembly is None:return None
            self._assembly_originals[region]={'assembly':assembly,
                'blocks':{i:deepcopy(draft.blocks[i]) for i in region}}
        return self._assembly_originals[region]

    def restore_original(self,region):
        if not self.entry_can_edit() or self._selected() is None:return
        draft=self._get_draft();index=self._mx_selected[0]
        if region!=draft.linked_positions(index):return
        original=self._assembly_originals.get(region)
        if original is None:return
        entered=draft.assembly_at(index)
        if (entered is not None and entered.key==original['assembly'].key and
                all(draft.blocks[i]['rotation']==original['blocks'][i]['rotation'] for i in region)):
            # Clicking an already selected shape must not erase later colour
            # edits. The retained snapshot is used when switching back to it.
            return
        candidate=MixupEntryDraft(draft.kind,self._mx_state)
        try:candidate.restore_region(index,original['blocks'])
        except ValueError as exc:self._message=tr(str(exc));self._refresh();return
        if candidate.state()==self._mx_state:return
        self._remember();self._draft=candidate
        if not candidate.blocks[index]['cells']:
            index=next(i for i in region if candidate.blocks[i]['cells'])
        self._mx_selected=(index,0);self._sync()

    def _current_assembly(self):
        selected=self._selected()
        if selected is None:return None
        key=selected[0].get('assembly_source') or selected[0]['composition']
        current=next((a for a in self._assemblies if a.key==key),None)
        if current is not None:return current
        draft=self._get_draft();region=draft.linked_positions(self._mx_selected[0])
        cells=[c for i in region for c in draft.blocks[i]['cells']]
        if not cells or any(c['world'] is None for c in cells):return None
        actual={polygon_key(c['world']) for c in cells}
        inner_bodies={c['body_key'] for c in cells if c.get('body_key') is not None}
        found=next((a for a in self._assemblies if
            {polygon_key(p) for piece in a.pieces for p in piece.panels}==actual and
            {tuple(sorted(polygon_key(p) for p in piece.body)) for piece in a.pieces if piece.body}==inner_bodies),None)
        if found is not None:return found
        entered=draft.assembly_at(self._mx_selected[0])
        if (entered is not None and inner_pattern(entered.pieces) is not None or
                MIXUP_MODELS[draft.kind][1] and selected[0]['role'] in ('centre','edge')):
            group=assembly_group(entered.pieces) if entered is not None else None
            return next((a for a in self._assemblies if a.group_key==group),None)
        return None

    def rotate_assembly(self,delta):
        if not self.entry_can_edit() or self._selected() is None:return
        index=self._mx_selected[0];current=self._current_assembly()
        original=self._original_assembly()
        candidate=MixupEntryDraft(self._cube.puzzle_kind,self._mx_state)
        source=current.key if current is not None else original['assembly'].key if original else None
        try:candidate.rotate_assembly(index,delta*candidate.rotation_step(index),source)
        except ValueError as exc:self._message=tr(str(exc));self._refresh();return
        self._remember();self._draft=candidate;self._sync()

    def pick(self,slot):
        if not self.entry_can_edit():return
        found=divmod(slot,1024)
        old_region=self._assembly_region
        self._mx_selected=found;selected=self._selected()
        if selected is None:return
        if old_region!=self._get_draft().linked_positions(found[0]):self._clear_options()
        if not self._paint_enabled and selected[1]['color']>=0:self._color=selected[1]['color']
        self._message='' if selected[1]['world'] is not None or selected[0]['role']=='corner' else tr('mixup.entry_composition_first')
        # Capture the opening assembly before the first brush stroke, so its
        # retained choice does not accidentally include the newly painted colour.
        self._original_assembly()
        if self._paint_enabled and (selected[1]['world'] is not None or selected[0]['role']=='corner'):
            self._paint()
        else:self._refresh()
        self._load_assemblies()

    def _load_assemblies(self):
        selected=self._selected()
        if selected is None:return
        draft=self._get_draft();region=draft.linked_positions(self._mx_selected[0])
        if region==self._assembly_region and (self._assemblies or self._assembly_job):return
        self._assembly_region=region;self._assemblies=();self._assembly_job=None
        if selected[0]['role']=='corner':self._refresh();return
        token=object();self._assembly_job=token;kind=draft.kind
        blocks=tuple({k:b[k] for k in ('face','role','outline','bounds')} for b in draft.blocks)
        self._refresh()
        def cancelled():return self._assembly_job is not token
        def run():
            result=();error=None
            try:result=assemblies(kind,blocks,region,cancelled)
            except InterruptedError:return
            except Exception as exc:error=str(exc) if str(exc).startswith('mixup.') else 'observe.invalid'
            def finish(_):
                if cancelled():return
                self._assembly_job=None;self._assemblies=result
                if self._job is None:
                    self._message=tr(error) if error else '' if result else tr('mixup.entry_keep_shape')
                self._refresh()
            Clock.schedule_once(finish,0)
        threading.Thread(target=run,daemon=True).start()

    def select_assembly(self,assembly):
        if not self.entry_can_edit() or self._selected() is None:return
        # A queued release from a card that disappeared during selection must
        # never apply its old position's assembly to the newly selected block.
        if tuple(assembly.positions)!=self._get_draft().linked_positions(self._mx_selected[0]):return
        current=self._current_assembly()
        if current is not None and current.key==assembly.key:return
        candidate=MixupEntryDraft(self._cube.puzzle_kind,self._mx_state);index=self._mx_selected[0]
        try:candidate.set_assembly(index,assembly)
        except ValueError as exc:self._message=tr(str(exc));self._refresh();return
        self._remember();self._draft=candidate;self._mx_selected=(index,0);self._sync()

    def _paint(self):
        if not self.entry_can_edit() or self._selected() is None:return
        candidate=MixupEntryDraft(self._cube.puzzle_kind,self._mx_state)
        try:candidate.paint(*self._mx_selected,self._color)
        except ValueError as exc:self._message=tr(str(exc));self._refresh();return
        if candidate.state()==self._mx_state:self._refresh();return
        self._remember();self._draft=candidate;self._sync()

    def select_color(self,color):
        if not self.entry_can_edit():return
        # Swatches choose a brush, never repaint the last selected panel.
        # Tapping its active swatch again returns to shape-only selection.
        self._paint_enabled=not(self._paint_enabled and self._color==color)
        self._color=color;self._message='';self._refresh()

    def clear_selected(self):
        if not self.entry_can_edit() or self._selected() is None:return
        self._remember();self._get_draft().clear_paint(*self._mx_selected);self._sync()

    def clear_choices(self):
        if not self.entry_can_edit() or self._selected() is None:return
        selection=self._mx_selected
        content=ResponsiveBoxLayout(orientation='vertical',gap_px=8,padding_px=8)
        popup=Popup(title=tr('mixup.entry_clear_options'),content=content,size_hint=(.85,None),height=m.h(235))
        def perform(action):
            popup.dismiss()
            if self._mx_selected==selection and self.entry_can_edit():action()
        for key,action in (('mixup.entry_clear_panel_color',self.clear_selected),
                           ('mixup.entry_reset_assembly',self.clear_position)):
            button=UIButton(text=tr(key));button.bind(on_release=lambda *_,fn=action:perform(fn));content.add_widget(button)
        button=UIButton(text=tr('confirm.cancel'));button.bind(on_release=lambda *_:popup.dismiss());content.add_widget(button)
        self._clear_popup=popup
        popup.bind(on_dismiss=lambda *_:setattr(self,'_clear_popup',None))
        theme_popup(popup,App.get_running_app().theme).open()

    def clear_position(self):
        if not self.entry_can_edit() or self._selected() is None:return
        self._remember();self._get_draft().clear_position(self._mx_selected[0])
        self._mx_selected=(self._mx_selected[0],0);self._sync()

    def _start(self,worker,finish,message):
        if not self.entry_can_edit():return
        token=object();self._job=token;self._cancel.clear();self._message=tr(message);self._refresh()
        def cancel():return self._cancel.is_set() or self._job is not token
        def run():
            result=None;error=None
            try:result=worker(cancel)
            except InterruptedError:return
            except Exception as exc:
                known=str(exc).startswith(('mixup.','observe.','rigid.'))
                error=str(exc) if known else 'observe.invalid'
                if not known:Logger.exception('Mixup input: background operation failed')
            def done(_):
                if cancel():return
                self._job=None
                if error:self._message=tr(error);self._refresh()
                else:finish(result)
            Clock.schedule_once(done,0)
        threading.Thread(target=run,daemon=True).start()
    def apply(self,after=None):
        if not self.entry_can_edit():return
        if not self._applied():self._reconcile_known_state()
        if self._applied():
            if after=='twist':super().open_twist()
            elif after=='solve':super().solve()
            return
        source=MixupEntryDraft(self._cube.puzzle_kind,self._mx_state)
        def worker(cancel):
            result=match_observations(source.observations(),cancel)
            draft=MixupEntryDraft.from_cube(result.cube) if result.status=='matched' else None
            if cancel():raise InterruptedError()
            return result,draft
        def finish(prepared):
            result,draft=prepared
            self._message=tr('observe.'+result.status)
            if result.status=='matched':
                self._remember();self._cube=result.cube;self.entry_commit_state(draft);self._message=tr('observe.matched')
            self._refresh()
            if result.status=='matched':
                if after=='twist':super(MixupInputScreen,self).open_twist()
                elif after=='solve':super(MixupInputScreen,self).solve()
        self._start(worker,finish,'observe.matching')
    def entry_can_twist(self):return self._applied()
    def entry_prepare_twist(self):App.get_running_app().cube=self._cube
    def open_twist(self):self.apply('twist')
    def solve(self):self.apply('solve')
    def entry_commit_state(self,draft=None):
        self._paint_enabled=False
        draft=MixupEntryDraft.from_cube(self._cube) if draft is None else draft
        state=draft.state()
        App.get_running_app().cube=self._cube;App.get_running_app().polyhedral_solution=None
        self._mx_state=state;self._draft=draft;self._stamp=state
        self._mx_applied=self._mx_cube_key=tuple(self._cube.frames)
        self._assembly_originals={}
        self._recorded=set(range(len(self._cube.solids)));self._mx_selected=None;self._clear_options();self._message='';self._refresh()
    def entry_reset_solved(self):
        self._remember();self._cube.colors=(0,)*len(self._cube.solids)
    def entry_set_status(self,text,error=False):self._message=text;self._refresh()
    def clear(self):
        if not self.entry_can_edit():return
        self._remember();self._draft=MixupEntryDraft(self._cube.puzzle_kind);self._mx_selected=None;self._clear_options();self._sync()
        self._assembly_originals={}
    def undo(self):
        if not self.entry_can_edit():return
        self._absorb_history()
        if not self._mx_undo:return
        self._cube,self._mx_state,self._mx_applied,self._mx_selected=self._mx_undo.pop()
        self._mx_cube_key=tuple(self._cube.frames);App.get_running_app().cube=self._cube;self._clear_options();self._message='';self._refresh();self._load_assemblies()
    def randomize(self):
        if not self.entry_can_edit():return
        # A stale combination enumeration must not compete with the limited
        # scramble search for CPU time.
        self._clear_options()
        kind=self._cube.puzzle_kind
        from cube.mixup import scramble_mixup
        def worker(cancel):
            cube=scramble_mixup(kind,cancel)
            if cancel():raise InterruptedError()
            draft=MixupEntryDraft.from_cube(cube)
            if cancel():raise InterruptedError()
            return cube,draft
        def finish(result):
            cube,draft=result
            self._remember()
            self._cube=cube;self.entry_commit_state(draft)
            if getattr(cube,'scramble_limited',False):self._message=tr('observe.scramble_limited',n=len(cube.history));self._refresh()
        self._start(worker,finish,'rigid.shuffling')
    def cancel_matching(self):
        self._cancel.set();self._job=None;self._clear_options();self._message=tr('observe.cancelled');self._refresh()
    def back(self):self.cancel_matching();self.manager.current='HomeScreen'
    def reset_interaction(self):
        if self._clear_popup is not None:self._clear_popup.dismiss()
        self.view.cancel_touch();self.view.cancel_animation()
        self._assembly_job=None
        if self._job is not None:self.cancel_matching()
    def on_pre_leave(self,*_):self.reset_interaction()
    def retranslate(self):
        self.follow.retranslate();self._refresh()
    def refresh_theme(self):
        for w in (self.title,self.selection,self.kind_label,self.rotation_label,self.hint,self.status):w.color=App.get_running_app().theme.text
    def apply_palette_colors(self,colors):
        from app.prefs import set
        set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in colors]);self.view.palette=tuple(colors);self._build_colors();self._refresh()
