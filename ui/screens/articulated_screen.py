"""Piece identity and rigid pose entry for Mixup and Tangram."""
import math
import random
import threading
from time import monotonic
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from app.i18n import tr
from cube.articulated import ArticulatedCube,multiply,turn_frame,frame_key
from renderer.articulated_view import ArticulatedView
from renderer.polyhedral_view import CUBE_PALETTE
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.screens.entry_mixin import EntryActionsMixin


class RigidEntryScreen(EntryActionsMixin,Screen):
    entry_twist_screen='PolyhedralTwistScreen'
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None;self._recorded=set();self._history=[]
        self._position=0;self._rigid_pose=0;self._job=None;self._cancel=threading.Event()
        root=AdaptiveSceneLayout()
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back');back.bind(on_release=lambda *_:self.back())
        self.title=Label();gear=UIButton(icon_name='gear');gear.bind(on_release=lambda *_:self.customize())
        for w in (back,self.title,gear):top.add_widget(w)
        root.add_widget(top)
        self.view=ArticulatedView();self.view.on_pick=self.pick
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=6)
        self.preview=ArticulatedView();self.preview.fit_piece=True
        panel.add_widget(self.preview)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        for icon,delta in (('prev',-1),('next',1)):
            button=UIButton(icon_name=icon);button.bind(on_release=lambda *_,d=delta:self.select_piece(d));row.add_widget(button)
        self.piece_label=Label();row.add_widget(self.piece_label);panel.add_widget(row)
        self.axis=Spinner(values=('X','Y','Z'),text='X',size_hint_y=None,height=44)
        panel.add_widget(self.axis)
        row=ResponsiveBoxLayout(height_px=46,gap_px=6)
        for icon,delta in (('prev',-1),('next',1)):
            button=UIButton(icon_name=icon);button.bind(on_release=lambda *_,d=delta:self.rotate_piece(d));row.add_widget(button)
        self.confirm=PrimaryButton(icon_name='check');self.confirm.bind(on_release=lambda *_:self.confirm_piece());row.add_widget(self.confirm)
        panel.add_widget(row)
        self.hint=Label(text=tr('rigid.entry_hint'),size_hint_y=None,height=66,font_size='13sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.hint)
        actions=ResponsiveBoxLayout(height_px=48,gap_px=5)
        for cls,icon,fn in ((UIButton,'twist',self.open_twist),(UIButton,'random',self.randomize),
                            (DangerButton,'clear',self.clear),(UIButton,'undo',self.undo),
                            (UIButton,'target',self.assign_initial),(PrimaryButton,'solve',self.solve)):
            b=cls(icon_name=icon);b.bind(on_release=lambda *_,f=fn:f());actions.add_widget(b)
        panel.add_widget(actions)
        self.status=Label(size_hint_y=None,height=48,font_size='13sp',halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size));panel.add_widget(self.status)
        root.set_content(self.view,panel);self.add_widget(root)
    def on_pre_enter(self,*_):
        cube=App.get_running_app().cube
        if cube is not self._cube:
            self._cube=cube;self._recorded=set();self._history=[];self._position=0
        self._position=max(0,min(self._position,len(cube.solids)-1))
        from app.prefs import get
        palette=get('poly_palette_'+cube.puzzle_kind,None)
        if isinstance(palette,list) and len(palette)==6:self.view.palette=tuple(tuple(c) for c in palette)
        else:self.view.palette=CUBE_PALETTE
        self.view.set_cube(cube)
        if palette and len(palette)==6:self.view.palette=tuple(tuple(c) for c in palette)
        self.axis.values=('X','Y','Z') if cube.family=='mixup' else tuple(tr('poly.axis',i=i+1) for i in range(4))
        self.axis.text=self.axis.values[0];self._rigid_pose=cube.frames[self._position]
        self.retranslate();self._refresh()
    def retranslate(self):
        if self._cube:self.title.text=tr('directory.'+self._cube.puzzle_kind)
        self.hint.text=tr('rigid.entry_hint')
    def refresh_theme(self):
        theme=App.get_running_app().theme
        for w in (self.title,self.hint,self.status,self.piece_label):w.color=theme.text
    def _refresh(self):
        if self._cube is None:return
        preview=self._cube.clone();frames=list(preview.frames);frames[self._position]=self._rigid_pose;preview.colors=frames
        self.view.cube=preview;self.view.recorded=set(self._recorded)|{self._position};self.view.refresh()
        self.preview.set_cube(preview);self.preview.palette=self.view.palette
        self.preview.piece_filter=self._position;self.preview.recorded=None;self.preview.refresh()
        self.view.selected=self._cube.geometry.pieces[self._position][0]
        self.piece_label.text=f'{self._position+1}/{len(self._cube.solids)}'
        self.status.text=tr('rigid.progress',done=len(self._recorded),total=len(self._cube.solids))
        if self._cube.puzzle_kind in ('mixup_333','mixup_plus_333') and len(self._recorded)==len(self._cube.solids):
            from cube.mixup import exchange_counts
            centres,edges=exchange_counts(self._cube)
            self.status.text+='\n'+tr('mixup.exchanged',centres=centres,edges=edges)
        self.refresh_theme()
    def pick(self,index):
        if not self.entry_can_edit():return
        self._position=self._cube.geometry.stickers[index].piece
        self._rigid_pose=self._cube.frames[self._position];self._refresh()
    def select_piece(self,delta):
        if not self.entry_can_edit():return
        self._position=(self._position+delta)%len(self._cube.solids)
        self._rigid_pose=self._cube.frames[self._position];self._refresh()
    def rotate_piece(self,direction):
        if not self.entry_can_edit():return
        cube=self._cube;axis=self.axis.values.index(self.axis.text)
        angle=math.pi/4 if cube.family=='mixup' else math.pi if axis<3 else math.pi/(3 if cube.family=='tangram_extreme' else 1.5)
        turn=turn_frame(cube.geometry.spec.axes[axis],angle*direction)
        frame=cube.orientations[self._rigid_pose]
        # Corners have 90-degree orientations; a 45-degree intermediate
        # orientation is only meaningful for the exchangeable inner pieces.
        for _ in range(2):
            frame=multiply(turn,frame);pose=cube._pose_index.get(frame_key(frame))
            if pose is not None and cube.pose_allowed(self._position,pose):
                self._rigid_pose=pose;self._refresh();return
        self.status.text=tr('rigid.blocked')
    def _remember(self):
        self._history.append((self._cube.clone(),set(self._recorded)));self._history=self._history[-40:]
        App.get_running_app().polyhedral_solution=None
    def confirm_piece(self):
        if not self.entry_can_edit():return
        candidate=self._cube.clone()
        try:candidate.record_pose(self._position,self._rigid_pose,self._recorded)
        except ValueError as exc:self.status.text=tr(str(exc));return
        self._remember();self._cube.colors=candidate.frames;self._recorded.add(self._position)
        self.entry_commit_state()
    def clear(self):
        if not self.entry_can_edit():return
        self._remember();self._cube.colors=(0,)*len(self._cube.solids);self._recorded=set();self._rigid_pose=0
        self.entry_commit_state()
    def undo(self):
        if not self.entry_can_edit() or not self._history:return
        self._cube,self._recorded=self._history.pop();self._rigid_pose=self._cube.frames[self._position];self.entry_commit_state()
    def entry_reset_solved(self):
        self._remember()
        if hasattr(self._cube,'reset'):
            self._cube.reset()
        else:
            self._cube.colors=(0,)*len(self._cube.solids)
        self._recorded=set(range(len(self._cube.solids)));self._rigid_pose=0
    def entry_commit_state(self):
        app=App.get_running_app();app.cube=self._cube;app.polyhedral_solution=None;self._refresh()
    def entry_set_status(self,text,error=False):self.status.text=text
    def entry_can_twist(self):
        if len(self._recorded)!=len(self._cube.solids):self.status.text=tr('rigid.incomplete');return False
        return True
    def entry_prepare_twist(self):App.get_running_app().cube=self._cube
    def randomize(self):
        if not self.entry_can_edit():return
        self._remember();self._cancel.clear();self._job=object();self.status.text=tr('rigid.shuffling')
        def cube_shaped(cube):
            from cube.mastermorphix import ROTATIONS
            proper={frame_key(f) for f in ROTATIONS}
            return all(frame_key(cube.orientations[pose]) in proper for pose in cube.frames)
        def run():
            error=None
            try:
                if self._cube.family=='mixup':
                    from cube.mixup import scramble_mixup
                    work=scramble_mixup(self._cube.puzzle_kind,self._cancel.is_set)
                    Clock.schedule_once(lambda _:finish(work,None),0)
                    return
                # A short face-turn-only sequence can leave the silhouette a
                # perfect cube. Retry until the scramble also shifts a middle
                # layer, so the input does not look almost solved.
                work=type(self._cube)(self._cube.puzzle_kind)
                for _attempt in range(8):
                    candidate=type(self._cube)(self._cube.puzzle_kind)
                    deadline=monotonic()+4.;previous=None
                    for _ in range(30):
                        if self._cancel.is_set() or monotonic()>deadline:break
                        choices=list(candidate.moves());random.shuffle(choices)
                        for move in choices:
                            if self._cancel.is_set() or monotonic()>deadline:break
                            if (move.axis,move.layer)==previous:continue
                            if random.randrange(2):move=move.inverse(candidate.geometry.spec.turn_order)
                            try:candidate.apply_move(move)
                            except ValueError:continue
                            previous=(move.axis,move.layer);break
                    if candidate.history and not candidate.is_solved() and not cube_shaped(candidate):
                        work=candidate;break
                    work=candidate
            except Exception as exc:
                import traceback;traceback.print_exc();error=str(exc)
            Clock.schedule_once(lambda _:finish(work if error is None else None,error),0)
        def finish(work,error):
                self._job=None
                if self._cancel.is_set():return
                if error:self.status.text=tr(error) if error.startswith(('rigid.','mixup.')) else tr('rigid.invalid');return
                if not work.history:self.status.text=tr('rigid.no_scramble');return
                self._cube=work;self._recorded=set(range(len(work.solids)))
                self._rigid_pose=work.frames[self._position];self.entry_commit_state()
        threading.Thread(target=run,daemon=True).start()
    def solve(self):
        if not self.entry_can_edit() or not self.entry_can_twist():return
        entered=self._cube.clone();palette=tuple(self.view.palette)
        def solved(result):
            App.get_running_app().solve_result=result
            App.get_running_app().polyhedral_solution=(entered,result.moves,palette)
            self.manager.current='PolyhedralPlaybackScreen'
        screen=self.manager.get_screen('SolvingScreen')
        screen.configure(entered,self.name,solved,ArticulatedView,palette);self.manager.current='SolvingScreen'
    def palette_colors(self):return self.view.palette
    def default_palette_colors(self):return CUBE_PALETTE
    def apply_palette_colors(self,colors):
        from app.prefs import set
        set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in colors]);self.view.palette=tuple(colors);self._refresh()
    def customize(self):
        if not self.entry_can_edit():return
        screen=self.manager.get_screen('PiecePaletteScreen');screen.configure(self)
        self.manager.current='PiecePaletteScreen'
    def back(self):
        self._cancel.set();self.manager.current='HomeScreen'

    def reset_interaction(self):
        self.view.cancel_touch();self.view.cancel_animation();self.preview.cancel_touch()


from ui.screens.articulated_observation_screen import ArticulatedObservationEntry


class ArticulatedEntryScreen(ArticulatedObservationEntry,RigidEntryScreen):
    """Public entry uses polygon observations; retains shared solve actions."""
