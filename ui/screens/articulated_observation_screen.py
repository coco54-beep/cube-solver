"""Observation-first entry shared by Mixup and Tangram."""
import threading
from copy import deepcopy
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from app.i18n import tr
from app.prefs import get as pref_get,set as pref_set
from cube.articulated_observation import (ObservationDraft,FACE_ORDER,FACES,contains,
    outlines_at,match_observations,polygon_key,color_templates)
from renderer.polyhedral_view import CUBE_PALETTE
from ui.widgets.articulated_observation import ObservationBoard,OutlineCard,ObservationPreview
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.widgets import metrics as m


class ArticulatedObservationEntry:
    """UI mixin; existing entry actions supply palette/solver integration."""
    def __init__(self,**kwargs):
        Screen.__init__(self,**kwargs)
        self._cube=None;self._recorded=set();self._history=[];self._position=0;self._rigid_pose=0
        self._job=None;self._cancel=threading.Event();self._draft=None;self._draft_stamp=None
        self._ao_state=None;self._ao_face=2;self._ao_undo=[];self._ao_applied=None;self._ao_cube_key=None
        self._ao_dirty=True;self._ao_region=0;self._color=0;self._point=None;self._groups=[];self._shape=0
        self._variant=0;self._page=0;self._depth=None;self._message='';self._buttons=[];self._mode_kind=None
        root=AdaptiveSceneLayout();self._root_layout=root
        top=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self._button(top,'back',self.back);self.title=Label(font_size='17sp');top.add_widget(self.title)
        self._button(top,'gear',self.customize);root.add_widget(top)
        scene=ResponsiveBoxLayout(orientation='vertical',gap_px=4)
        self.face_label=Label(size_hint_y=None,height=m.h(30),font_size='14sp');scene.add_widget(self.face_label)
        self.board=ObservationBoard();self.board.on_point=self.query_point;self.board.on_region=self.new_region
        scene.add_widget(self.board)
        self.reference=Label(size_hint_y=None,height=m.h(32),font_size='12sp');scene.add_widget(self.reference)
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=5)
        tabs=ResponsiveBoxLayout(height_px=38,gap_px=4);self.tabs={}
        for face in FACE_ORDER:self.tabs[face]=self._button(tabs,'',lambda f=face:self.change_face(f))
        panel.add_widget(tabs)
        self.colors=GridLayout(cols=6,size_hint_y=None,height=m.h(38),spacing=m.h(4));panel.add_widget(self.colors)
        row=ResponsiveBoxLayout(height_px=38,gap_px=5)
        self._count_row=row
        self.count_label=Label(font_size='12sp');row.add_widget(self.count_label)
        self.count=Spinner(values=tuple(str(i) for i in range(1,13)),text='1',size_hint_x=.4)
        self.count.bind(text=self.change_count);row.add_widget(self.count)
        self.group_button=self._button(row,'check',self.complete_region,PrimaryButton);panel.add_widget(row)
        self.gallery=GridLayout(cols=3,size_hint_y=None,height=m.h(106),spacing=m.h(4));panel.add_widget(self.gallery)
        row=ResponsiveBoxLayout(height_px=34,gap_px=4)
        self._page_row=row
        self._button(row,'prev',lambda:self.change_page(-1));self.page_label=Label(font_size='12sp');row.add_widget(self.page_label)
        self._button(row,'next',lambda:self.change_page(1));panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=38,gap_px=4)
        self._direction_row=row
        self._button(row,'prev',lambda:self.change_variant(-1));self.direction_label=Label(font_size='12sp');row.add_widget(self.direction_label)
        self._button(row,'next',lambda:self.change_variant(1));self.confirm_button=self._button(row,'check',self.record,PrimaryButton)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=36,gap_px=4)
        self.depth_button=self._button(row,'',self.change_depth);self._button(row,'clear',self.remove_panel,DangerButton)
        self.face_done=self._button(row,'',self.complete_face);self.skip_button=self._button(row,'next',self.skip_face)
        panel.add_widget(row)
        self.hint=Label(size_hint_y=None,height=m.h(42),font_size='12sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.hint)
        self.view=ObservationPreview(size_hint_y=None,height=m.h(130));self.preview=self.view;panel.add_widget(self.view)
        self.preview_label=Label(size_hint_y=None,height=m.h(23),font_size='12sp');panel.add_widget(self.preview_label)
        row=ResponsiveBoxLayout(height_px=42,gap_px=4)
        for icon,fn in (('undo',self.undo),('clear',self.clear),('check',self.apply),('cancel',self.cancel_matching)):
            self._button(row,icon,fn)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=4)
        for icon,fn in (('twist',self.open_twist),('random',self.randomize),('target',self.assign_initial),('solve',self.solve)):
            self._button(row,icon,fn)
        panel.add_widget(row)
        self.status=Label(size_hint_y=None,height=m.h(50),font_size='12sp',halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.status)
        root.set_content(scene,panel);self.add_widget(root)
        self._color_layout=None

    def _button(self,row,icon,fn,cls=UIButton):
        button=cls(icon_name=icon,font_size='12sp');button.bind(on_release=lambda *_:fn());row.add_widget(button)
        self._buttons.append(button);return button

    def _get_draft(self):
        if self._draft is None or self._draft_stamp is not self._ao_state:
            self._draft=ObservationDraft(self._cube.puzzle_kind,self._ao_state);self._draft_stamp=self._ao_state
        if self._cube.puzzle_kind.startswith('tangram'):self._ao_region=0
        return self._draft

    def _set_mode(self):
        kind=self._cube.puzzle_kind
        if kind==self._mode_kind:return
        self._mode_kind=kind;color_only=kind=='tangram';regions=kind.startswith('mixup_')
        tangram=kind.startswith('tangram')
        if tangram and self._color_layout is None:
            from ui.screens.tangram_color_layout import TangramColorLayout
            self._color_layout=TangramColorLayout(self)
        if self._color_layout is not None:self._color_layout.show(tangram)
        for row,height,show in ((self._count_row,38,regions),(self._page_row,34,not color_only),
                                (self._direction_row,38,not color_only)):
            row._height_px=height if show else 0;row.opacity=1 if show else 0;row.disabled=not show;row._sync_metrics()
        self.gallery.height=m.h(106) if not color_only else 0
        self.gallery.opacity=0 if color_only else 1;self.gallery.disabled=color_only
        self.depth_button.size_hint_x=1 if regions else None;self.depth_button.width=0 if not regions else m.h(90)
        self.depth_button.opacity=1 if regions else 0;self.depth_button.disabled=not regions
        self.board.fill_mode=color_only;self.board.allow_regions=regions;self.board.on_stroke=self.paint_colors
        self.board.templates=color_templates()[self._ao_face] if color_only else ()
        if not regions:self._ao_region=0
        self._root_layout._layout_trigger()

    def on_pre_enter(self,*_):
        cube=App.get_running_app().cube
        if self._cube is not None and self._cube is not cube:
            self._ao_state=None;self._ao_undo=[];self._ao_applied=None;self._history=[]
            self._clear_options();self._point=None;self._ao_region=0
        old_key=self._ao_cube_key;self._cube=cube
        self.view.set_cube(cube)
        self.view.palette=tuple(tuple(c) for c in pref_get('poly_palette_'+cube.puzzle_kind,CUBE_PALETTE))
        if self._ao_state is None or self._ao_state['kind']!=cube.puzzle_kind:
            self._ao_state=ObservationDraft(cube.puzzle_kind).state();self._ao_dirty=True;self._ao_region=0
            self._recorded=set();self._ao_applied=None
        elif old_key is not None and tuple(old_key)!=tuple(cube.frames):
            self._ao_state=ObservationDraft.from_cube(cube).state();self._ao_dirty=False
            self._ao_applied=tuple(cube.frames);self._recorded=set(range(len(cube.solids)));self._ao_region=0
        self._ao_cube_key=tuple(cube.frames);self._build_colors();self.retranslate()
        Clock.schedule_once(lambda *_:self._root_layout._adapt(),0)

    def _build_colors(self):
        from ui.screens.mastermorphix_screen import _Swatch
        self.colors.clear_widgets();self._swatches=[]
        for color,rgba in enumerate(self.view.palette):
            button=_Swatch(rgba,active=color==self._color,
                           text=str(color+1) if self._cube.puzzle_kind=='tangram' else '')
            button.bind(on_release=lambda *_,c=color:self.select_color(c));self.colors.add_widget(button);self._swatches.append(button)

    def _remember(self):
        self._ao_undo.append((self._cube.clone(),deepcopy(self._ao_state),self._ao_applied,self._ao_dirty,self._ao_face,self._ao_region))
        self._ao_undo=self._ao_undo[-24:];App.get_running_app().polyhedral_solution=None

    def _sync(self):
        self._ao_state=self._draft.state();self._draft_stamp=self._ao_state;self._ao_dirty=True
        self._ao_applied=None;self._message='';App.get_running_app().polyhedral_solution=None;self._refresh()

    def _option(self):
        return self._groups[self._shape][self._variant] if self._groups else None

    def _refresh(self):
        if self._cube is None:return
        self._set_mode()
        draft=self._get_draft();face=self._ao_face;option=self._option()
        if draft.kind=='tangram':self.board.templates=color_templates()[face]
        self.title.text=tr('directory.'+draft.kind)
        self.face_label.text=tr('input.face',face=tr('face.'+FACES[face]),code=FACES[face])
        self.reference.text=tr('six.face_reference',top=tr('face.'+('B','U','U','F','U','U')[face]),right=tr('face.'+('R','B','R','R','F','L')[face]))
        self.board.items=draft.views[face];self.board.palette=self.view.palette;self.board.face=face
        self.board.pending=option['outline'] if option else None
        region=draft.regions[self._ao_region-1] if 0<self._ao_region<=len(draft.regions) else None
        self.board.region=region['bounds'] if region and region['face']==face else None;self.board.redraw()
        for f,button in self.tabs.items():button.text=tr('face.'+FACES[f])+(' ✓' if draft.complete[f] else '');button.active=f==face
        for c,button in enumerate(getattr(self,'_swatches',())):button.active=c==self._color;button.disabled=self._job is not None
        done=sum(p.get('region',0)==self._ao_region for p in draft.views[face]) if region else 0
        if region and self.count.text!=str(region['count']):self.count.text=str(region['count'])
        self.group_button.active=bool(region and region['complete']);self.face_done.active=draft.complete[face]
        self.count_label.text=tr('observe.count',done=done,total=region['count'] if region else int(self.count.text))
        self.direction_label.text=tr('observe.direction',n=self._variant+1 if option else 0,total=len(self._groups[self._shape]) if option else 0)
        self.depth_button.text=tr('observe.auto_depth') if self._depth is None else tr('observe.depth',n=1+sorted({p.depth for p in option['panels']},reverse=True).index(self._depth)) if option else tr('observe.auto_depth')
        self.face_done.text=tr('observe.face_done');self.skip_button.text=tr('observe.skip')
        hint='observe.color_hint' if draft.kind=='tangram' else 'observe.shape_hint' if draft.kind=='tangram_extreme' else 'observe.hint'
        self.hint.text=tr(hint);self.preview_label.text=tr('observe.preview_applied' if self._applied() and option is None else 'observe.preview')
        if not draft.kind.startswith('tangram'):
            self.view.cube=self._cube;self.view.matched=self._applied() and option is None
            self.view.panels=tuple((p['preview'],p['color']) for view in draft.views for p in view)
            pending=next((p for p in option['panels'] if self._depth is None or abs(p.depth-self._depth)<1e-6),None) if option else None
            self.view.pending=(pending.world,-2) if pending else None;self.view.refresh()
        self.status.text=self._message or (tr('observe.color_progress',done=sum(map(len,draft.views)),total=sum(map(len,color_templates())),faces=sum(draft.complete))
            if draft.kind=='tangram' else tr('observe.progress',panels=sum(map(len,draft.views)),faces=sum(draft.complete)))
        self.board.disabled=self._job is not None;self.count.disabled=self._job is not None
        self.confirm_button.disabled=self._job is not None or not option or (draft.kind.startswith('mixup_') and (not region or region['complete']))
        self._draw_gallery();self.refresh_theme()

    def _applied(self):return not self._ao_dirty and self._ao_applied==tuple(self._cube.frames)

    def _draw_gallery(self):
        self.gallery.clear_widgets()
        pages=max(1,(len(self._groups)+5)//6);self._page%=pages
        self.page_label.text=f'{self._page+1}/{pages}'
        for index in range(self._page*6,min(len(self._groups),self._page*6+6)):
            card=OutlineCard(self._groups[index][0]['outline'],active=index==self._shape)
            card.bind(on_release=lambda *_,i=index:self.select_shape(i));self.gallery.add_widget(card)

    def _clear_options(self):
        self._groups=[];self._shape=self._variant=self._page=0;self._depth=None
        if self._color_layout is not None:self._color_layout.shapes.clear()
    def change_face(self,face):
        if not self.entry_can_edit():return
        self._ao_face=face;self._ao_region=0;self._point=None;self._clear_options();self._message='';self._refresh()
    def new_region(self,bounds):
        if not self.entry_can_edit() or bounds is None or not self._cube.puzzle_kind.startswith('mixup_'):return
        self._remember();draft=self._get_draft()
        draft.regions.append({'face':self._ao_face,'bounds':bounds,'count':int(self.count.text),'complete':False})
        self._ao_region=len(draft.regions);draft.complete[self._ao_face]=False;self._clear_options();self._sync()
    def change_count(self,*_):
        if self._cube is None or not self.entry_can_edit() or not self._cube.puzzle_kind.startswith('mixup_'):return
        draft=self._get_draft()
        if 0<self._ao_region<=len(draft.regions):
            region=draft.regions[self._ao_region-1]
            if region['count']!=int(self.count.text):
                self._remember();region['count']=int(self.count.text);region['complete']=False;self._sync()
    def select_color(self,color):
        if not self.entry_can_edit():return
        self._color=color
        if self._cube.puzzle_kind=='tangram':self._refresh();return
        if self._point is not None:self.query_point(self._point)
        else:self._refresh()

    def paint_colors(self,stroke):
        if not self.entry_can_edit() or self._cube.puzzle_kind!='tangram' or not stroke:return
        points=[stroke[0]]
        for a,b in zip(stroke,stroke[1:]):
            count=max(1,int(max(abs(a[0]-b[0]),abs(a[1]-b[1]))/.025)+1)
            points.extend(tuple(x+(y-x)*i/count for x,y in zip(a,b)) for i in range(1,count+1))
        templates=color_templates()[self._ao_face]
        indices={next((i for i,outline in enumerate(templates) if contains(outline,p)),None) for p in points}
        indices.discard(None)
        if not indices:return
        self._point=stroke[-1];draft=self._get_draft()
        painted={polygon_key(p['outline']):p['color'] for p in draft.views[self._ao_face]}
        if all(painted.get(polygon_key(templates[i]))==self._color for i in indices):return
        self._remember();draft.paint_samples(self._ao_face,sorted(indices),self._color);self._clear_options();self._sync()

    def _start(self,worker,finish,message):
        if not self.entry_can_edit():return
        token=object();self._job=token;self._cancel.clear();self._message=tr(message);self._refresh()
        def cancelled():return self._cancel.is_set() or self._job is not token
        def run():
            result=None;error=None
            try:result=worker(cancelled)
            except InterruptedError:return
            except Exception as exc:error=str(exc) if str(exc).startswith(('observe.','rigid.','mixup.')) else 'observe.invalid'
            def done(_):
                if cancelled():return
                self._job=None
                if error:self._message=tr(error);self._refresh()
                else:finish(result)
            Clock.schedule_once(done,0)
        threading.Thread(target=run,daemon=True).start()

    def query_point(self,point):
        if not self.entry_can_edit():return
        if self._cube.puzzle_kind=='tangram':self.paint_colors((point,));return
        if self._cube.puzzle_kind=='tangram_extreme':
            self._color_layout.shapes.query_point(point);return
        self._point=point;draft=self._get_draft()
        # Re-enter an existing region by tapping inside its drawn boundary.
        found=next((i for i,r in reversed(list(enumerate(draft.regions,1))) if r['face']==self._ao_face and r['bounds'][0]<=point[0]<=r['bounds'][2] and r['bounds'][1]<=point[1]<=r['bounds'][3]),None)
        if found:self._ao_region=found
        if not self._ao_region and draft.kind.startswith('mixup_'):
            self.new_region((max(-1.8,point[0]-.22),max(-1.8,point[1]-.22),min(1.8,point[0]+.22),min(1.8,point[1]+.22)))
        self._clear_options()
        kind=draft.kind;face=self._ao_face;color=self._color
        def finish(options):
            groups={}
            for option in options:groups.setdefault(option['shape'],[]).append(option)
            self._groups=list(groups.values());self._shape=self._variant=self._page=0;self._depth=None
            self._message='' if options else tr('observe.no_outline');self._refresh()
        self._start(lambda cancel:outlines_at(kind,face,color,point,cancel),finish,'observe.finding')

    def select_shape(self,index):
        if self.entry_can_edit():self._shape=index;self._variant=0;self._depth=None;self._refresh()
    def change_variant(self,delta):
        if self.entry_can_edit() and self._groups:
            self._variant=(self._variant+delta)%len(self._groups[self._shape]);self._depth=None;self._refresh()
    def change_page(self,delta):
        if self.entry_can_edit():self._page+=delta;self._draw_gallery()
    def change_depth(self):
        option=self._option()
        if not self.entry_can_edit() or not option:return
        values=[None]+sorted({p.depth for p in option['panels']},reverse=True)
        self._depth=values[(values.index(self._depth)+1)%len(values)];self._refresh()
    def record(self):
        option=self._option()
        if not self.entry_can_edit() or not option:return
        draft=self._get_draft();regional=draft.kind.startswith('mixup_')
        if regional and not self._ao_region:return
        region=draft.regions[self._ao_region-1] if regional else None
        if region and region['complete']:return
        existing=next((p for p in draft.views[self._ao_face] if polygon_key(p['outline'])==polygon_key(option['outline'])),None)
        count=sum(p.get('region',0)==self._ao_region for p in draft.views[self._ao_face])
        if region and count>=region['count'] and existing is None:
            self._message=tr('observe.region_full');self._refresh();return
        self._remember();draft.record(self._ao_face,option,self._color,self._depth,self._ao_region)
        if existing and existing.get('region',0) and existing['region']!=self._ao_region:draft.regions[existing['region']-1]['complete']=False
        self._clear_options();self._sync()
    def complete_region(self):
        if not self.entry_can_edit() or not self._ao_region:return
        draft=self._get_draft();region=draft.regions[self._ao_region-1]
        if sum(p.get('region',0)==self._ao_region for p in draft.views[self._ao_face])!=region['count']:
            self._message=tr('observe.region_count');self._refresh();return
        self._remember();region['complete']=not region['complete'];self._sync()
    def complete_face(self):
        if not self.entry_can_edit():return
        draft=self._get_draft()
        if draft.kind=='tangram':
            if len(draft.views[self._ao_face])!=len(color_templates()[self._ao_face]):
                self._message=tr('observe.colors_missing');self._refresh();return
            self._remember();draft.complete[self._ao_face]=True;self._sync();return
        if not draft.views[self._ao_face] or any(not r['complete'] for r in draft.regions if r['face']==self._ao_face):
            self._message=tr('observe.panels_missing' if draft.kind=='tangram_extreme' else 'observe.region_count');self._refresh();return
        self._remember();draft.complete[self._ao_face]=not draft.complete[self._ao_face];self._sync()
    def skip_face(self):self.change_face(FACE_ORDER[(FACE_ORDER.index(self._ao_face)+1)%6])
    def remove_panel(self):
        if not self.entry_can_edit():return
        draft=self._get_draft();items=draft.views[self._ao_face]
        selected=next((i for i in reversed(range(len(items))) if contains(items[i]['outline'],self._point)),None) if self._point else None
        if selected is None:
            # An empty region must be removable after a missed drag or a
            # position with no candidates, without clearing the whole draft.
            if self._ao_region and not any(p.get('region',0)==self._ao_region for view in draft.views for p in view):
                self._remember();draft.regions.pop(self._ao_region-1)
                for view in draft.views:
                    for p in view:
                        if p.get('region',0)>self._ao_region:p['region']-=1
                self._ao_region=0;self._clear_options();self._sync()
            return
        self._remember();item=items.pop(selected)
        if item.get('region',0):draft.regions[item['region']-1]['complete']=False
        draft.complete[self._ao_face]=False;self._clear_options();self._sync()
    def clear(self):
        if not self.entry_can_edit():return
        self._remember();self._draft=ObservationDraft(self._cube.puzzle_kind);self._ao_region=0;self._recorded=set();self._clear_options();self._sync()
    def undo(self):
        if not self.entry_can_edit():return
        if self._history:
            self._cube,self._recorded=self._history.pop();self.entry_commit_state();return
        if not self._ao_undo:return
        self._cube,self._ao_state,self._ao_applied,self._ao_dirty,self._ao_face,self._ao_region=self._ao_undo.pop()
        self._recorded=set(range(len(self._cube.solids))) if not self._ao_dirty else set()
        self._ao_cube_key=tuple(self._cube.frames);App.get_running_app().cube=self._cube;self._clear_options();self._message='';self._refresh()
    def apply(self,after=None):
        if not self.entry_can_edit():return
        if self._option() is not None:
            self._message=tr('observe.pending');self._refresh();return
        if self._applied():
            if after=='twist':super().open_twist()
            elif after=='solve':super().solve()
            return
        draft=ObservationDraft(self._cube.puzzle_kind,deepcopy(self._ao_state))
        def finish(result):
            prefix=('color_' if draft.kind=='tangram' else 'shape_' if draft.kind=='tangram_extreme' else '') if result.status in ('incomplete','conflict','ambiguous') else ''
            self._message=tr('observe.'+prefix+result.status)
            if result.face is not None:self._ao_face=result.face
            if result.status=='matched':
                self._remember();self._cube=result.cube;self._recorded=set(range(len(self._cube.solids)))
                self._ao_applied=self._ao_cube_key=tuple(self._cube.frames);self._ao_dirty=False
                App.get_running_app().cube=self._cube;App.get_running_app().polyhedral_solution=None
            self._refresh()
            if result.status=='matched':
                if after=='twist':super(ArticulatedObservationEntry,self).open_twist()
                elif after=='solve':super(ArticulatedObservationEntry,self).solve()
        self._start(lambda cancel:match_observations(draft,cancel),finish,'observe.matching')
    def entry_can_twist(self):return self._applied()
    def entry_set_status(self,text,error=False):self._message=text;self._refresh()
    def open_twist(self):self.apply('twist')
    def solve(self):self.apply('solve')
    def entry_reset_solved(self):
        self._remember();self._cube.colors=(0,)*len(self._cube.solids);self._recorded=set(range(len(self._cube.solids)))
    def entry_commit_state(self):
        App.get_running_app().cube=self._cube;App.get_running_app().polyhedral_solution=None
        self._ao_state=ObservationDraft.from_cube(self._cube).state();self._ao_region=0;self._ao_dirty=False
        self._ao_applied=self._ao_cube_key=tuple(self._cube.frames);self._clear_options();self._message='';self._refresh()
    def randomize(self):
        if not self.entry_can_edit():return
        if self._ao_dirty and any(self._get_draft().views):
            self._message=tr('observe.clear_first');self._refresh();return
        self._remember();kind=self._cube.puzzle_kind
        if kind.startswith('mixup_'):
            from cube.mixup import scramble_mixup
            def worker(cancel):return scramble_mixup(kind,cancel)
            self._start(worker,self._accept_scramble,'rigid.shuffling')
        else:
            import random
            from time import monotonic
            from cube.articulated_observation import new_cube
            def worker(cancel):
                cube=new_cube(kind);deadline=monotonic()+6.;previous=None;best=None
                def guard():
                    if cancel():raise InterruptedError()
                    if monotonic()>deadline:raise ValueError('rigid.no_scramble')
                for _ in range(40):
                    moves=list(cube.moves());random.shuffle(moves)
                    for move in moves:
                        if (move.axis,move.layer)==previous:continue
                        if random.randrange(2):move=move.inverse(cube.geometry.spec.turn_order)
                        try:cube.apply_move(move,guard=guard)
                        except ValueError as exc:
                            if str(exc)=='rigid.no_scramble':
                                if best is not None:return best
                                raise
                            continue
                        previous=move.axis,move.layer
                        if not cube.is_solved():best=cube.clone()
                        break
                    else:break
                if best is None:raise ValueError('rigid.no_scramble')
                return best
            self._start(worker,self._accept_scramble,'rigid.shuffling')
    def _accept_scramble(self,cube):
        self._cube=cube;self._recorded=set(range(len(cube.solids)));self.entry_commit_state()
        if getattr(cube,'scramble_limited',False):
            self._message=tr('observe.scramble_limited',n=len(cube.history));self._refresh()
    def cancel_matching(self):
        self._cancel.set();self._job=None;self._clear_options();self._message=tr('observe.cancelled');self._refresh()
    def back(self):self.cancel_matching();self.manager.current='HomeScreen'
    def reset_interaction(self):
        if self._color_layout is not None:self._color_layout.cancel_turn()
        self.board.cancel_touch();self.view.cancel_touch();self.view.cancel_animation()
        if self._job is not None:self.cancel_matching()
    def on_pre_leave(self,*_):self.reset_interaction()
    def retranslate(self):self._refresh()
    def refresh_theme(self):
        for w in (self.title,self.face_label,self.reference,self.hint,self.status,self.preview_label,self.count_label,self.direction_label,self.page_label):w.color=App.get_running_app().theme.text
        if self._cube:self.board.redraw()
        if self._color_layout is not None:self._color_layout.refresh()
    def apply_palette_colors(self,colors):
        pref_set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in colors]);self.view.palette=tuple(colors);self._build_colors();self._refresh()
