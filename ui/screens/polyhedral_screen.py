"""Responsive polyhedral sticker entry and solution playback."""
import math
import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from ui.screens.entry_mixin import EntryActionsMixin
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner

from app.i18n import tr
from cube.polyhedral import Move, solved_colors
from renderer.polyhedral_view import PolyhedralView, PolyhedralTwistView, default_palette
from renderer.cube_orientation import CubeOrientation
from renderer.mat4 import Mat4
from renderer.camera_follow import follow_turn, polyhedral_target, cancel_follow, FOLLOW_SETTINGS, reset_camera_view
from ui.widgets.camera_follow import follow_panel
from ui.screens.mastermorphix_screen import _Swatch
from ui.widgets.buttons import UIButton,PrimaryButton,DangerButton
from ui.widgets.dialogs import theme_popup
from ui.widgets.layouts import AdaptiveSceneLayout,ResponsiveBoxLayout
from ui.widgets import metrics as m


def _app():
    return App.get_running_app()


def _puzzle_title(cube):
    kind=cube.puzzle_kind
    if kind=='dino':
        kind='dinosaur' if cube.n==2 else 'lattice'
    return tr('directory.'+kind)


def _view_for(cube,twist=False):
    if cube is not None and getattr(cube,'puzzle_kind','').startswith(('cuboid_','camouflage_3')):
        from renderer.cuboid_view import CuboidView,CuboidTwistView
        return CuboidTwistView if twist else CuboidView
    if cube is not None and getattr(cube,'puzzle_kind',None)=='ghost_pyramid':
        from renderer.ghost_pyramid_view import GhostPyramidView,GhostPyramidTwistView
        return GhostPyramidTwistView if twist else GhostPyramidView
    if cube is not None and getattr(cube,'puzzle_kind',None)=='fisher_skewb':
        from renderer.fisher_skewb_view import FisherSkewbView,FisherSkewbTwistView
        return FisherSkewbTwistView if twist else FisherSkewbView
    if cube is not None and getattr(cube,'puzzle_kind',None)=='mirror_skewb':
        from renderer.mirror_skewb_view import MirrorSkewbView,MirrorSkewbTwistView
        return MirrorSkewbTwistView if twist else MirrorSkewbView
    if cube is not None and getattr(cube,'puzzle_kind',None)=='mirror_pyraminx':
        from renderer.mirror_pyraminx_view import MirrorPyraminxView,MirrorPyraminxTwistView
        return MirrorPyraminxTwistView if twist else MirrorPyraminxView
    if cube is not None and getattr(cube,'puzzle_kind',None)=='mirror_tower':
        from renderer.mirror_tower_view import MirrorTowerView,MirrorTowerTwistView
        return MirrorTowerTwistView if twist else MirrorTowerView
    return PolyhedralTwistView if twist else PolyhedralView


def _entry_for(cube):
    return {'ghost_pyramid':'GhostPyramidScreen','fisher_skewb':'FisherSkewbScreen','mirror_tower':'MirrorTowerScreen',
            'mirror_skewb':'MirrorSkewbScreen',
            'mirror_pyraminx':'MirrorPyraminxScreen'}.get(cube.puzzle_kind,'PolyhedralScreen')


class PolyhedralScreen(EntryActionsMixin, Screen):
    view_class=PolyhedralView
    customize_icon='gear'
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None
        self._history=[]
        self._face=0
        self._axis=0
        self._layer=0
        self._color=0
        self._job=None
        self._solve_popup=None
        self._cancel=threading.Event()
        self._view_busy=False
        self._view_direction=None
        self._view_orientation=None
        self._poly_orientation=None
        self._build()

    def _build(self):
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8],gap_px=8)
        self._root_layout=root
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=.16)
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp')
        help_button=UIButton(icon_name='demo',size_hint_x=.16)
        help_button.bind(on_release=lambda *_:self.open_demo())
        self.demo_button=help_button
        for item in (back,self.title,help_button):
            top.add_widget(item)
        root.add_widget(top)
        self.view=(_view_for(getattr(_app(),'cube',None)) if self.view_class is PolyhedralView else self.view_class)()
        self.view.on_pick=self.paint
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=7,size_hint_y=None)
        self.palette=ResponsiveBoxLayout(height_px=44,gap_px=5)
        panel.add_widget(self.palette)
        self.palette2=ResponsiveBoxLayout(height_px=44,gap_px=5)
        panel.add_widget(self.palette2)
        self._extra_palette_rows=[]
        for _ in range(2):
            row=ResponsiveBoxLayout(height_px=0,gap_px=5)
            row.opacity=0
            row.disabled=True
            panel.add_widget(row)
            self._extra_palette_rows.append(row)
        self.hint=Label(text=tr('poly.input_hint'),size_hint_y=None,height=m.h(54),
                        font_size='13sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.hint)
        observation=ResponsiveBoxLayout(height_px=44,gap_px=6)
        prev=UIButton(icon_name='prev')
        prev.bind(on_release=lambda *_:self.change_view(-1))
        customize=UIButton(icon_name=self.customize_icon)
        customize.bind(on_release=lambda *_:self.customize())
        nxt=UIButton(icon_name='next')
        nxt.bind(on_release=lambda *_:self.change_view(1))
        for widget in (prev,customize,nxt):
            observation.add_widget(widget)
        panel.add_widget(observation)
        actions=ResponsiveBoxLayout(height_px=48,gap_px=6)
        for cls,icon,callback in ((UIButton,'twist',self.open_twist),
                                  (UIButton,'random',self.randomize),(DangerButton,'clear',self.clear),
                                  (UIButton,'undo',self.undo),(UIButton,'target',self.assign_initial),
                                  (PrimaryButton,'solve',self.solve)):
            button=cls(icon_name=icon)
            button.bind(on_release=lambda *_,fn=callback:fn())
            actions.add_widget(button)
        panel.add_widget(actions)
        self.status=Label(size_hint_y=None,height=m.h(34),font_size='14sp',
                          halign='center',valign='middle')
        self.status.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.status)
        self.panel=panel
        panel,self.follow_control=follow_panel(panel,self.view)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        if type(self.view) is not _view_for(_app().cube):
            self.view.cancel_animation()
            self.clear_widgets()
            self._build()
            self._cube=None
        if self._cube is not _app().cube:
            self._cube=_app().cube
            self._history=[]
            self._axis=self._layer=self._color=self._face=0
            self.view.set_cube(self._cube)
            self._view_orientation=None
            self._poly_orientation=None
            if self._cube.puzzle_kind in ('skewb', 'dino', 'eight_petals', 'void_cube', 'helicopter','clover', 'ivy', 'super_ivy', 'mosaic', 'tins', 'dino_skewb', 'dayan_dino_skewb'):
                self._view_orientation=CubeOrientation(self._cube.n)
                self.view.set_whole_world(self._view_orientation.world)
                self.view.yaw=self.view.pitch=0
                self._face=2  # F, matching ordinary input's initial face.
            elif isinstance(self.view,PolyhedralView):
                from renderer.polyhedral_orientation import PolyhedralOrientation
                self._poly_orientation=PolyhedralOrientation(self._cube.geometry.spec,self._face_roll(0))
                self.view.set_whole_world(self._poly_orientation.world)
                self.view.yaw=self.view.pitch=self.view.roll=0
            from app.prefs import get as pref_get
            saved=pref_get('poly_palette_'+self._cube.puzzle_kind,None)
            if isinstance(saved,list) and len(saved)==getattr(
                    self._cube,'color_count',len(self._cube.geometry.spec.normals)) and all(
                isinstance(c,list) and len(c)==4 and all(isinstance(v,(int,float)) and 0<=v<=1 for v in c)
                for c in saved):
                self.view.palette=tuple(tuple(c) for c in saved)
            self.view.selected=None
            self._build_palette()
        self.retranslate()
        self.refresh_theme()
        self._refresh()

    def _build_palette(self):
        count=getattr(self._cube,'color_count',len(self._cube.geometry.spec.normals))
        width=8 if count>20 else 5 if count>12 else 6
        rows=[self.palette,self.palette2]+self._extra_palette_rows
        for index,row in enumerate(rows):
            row.clear_widgets()
            visible=index*width<count
            row.height=m.h(44) if visible else 0
            row._height_px=44 if visible else 0
            row.opacity=1 if visible else 0
            row.disabled=not visible
        self._swatches=[]
        for i in range(count):
            button=_Swatch(self.view.palette[i],text=str(i+1),active=i==self._color)
            button.bind(on_release=lambda *_,color=i:self.choose_color(color))
            rows[i//width].add_widget(button)
            self._swatches.append(button)

    def choose_color(self,color):
        self._color=color
        for i,button in enumerate(self._swatches):
            button.active=i==color

    def _remember(self):
        self._history.append(self._cube.clone() if self._cube.puzzle_kind.startswith(('crazy_','cuboid_','camouflage_3')) else tuple(self._cube.colors))
        self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def paint(self,index):
        if self._job is not None or self._view_busy:
            return
        self._remember()
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            self._cube.paint(index,self._color)
        else:
            self._cube.colors[index]=self._color
        self.view.selected=index
        self._refresh()

    def _refresh(self):
        if self._cube is None:
            return
        has_demo=self._cube.n<=5 and not self._cube.puzzle_kind.startswith(('crazy_','cuboid_','camouflage_3'))
        self.demo_button.disabled=not has_demo
        self.demo_button.opacity=1 if has_demo else 0
        done,total=(self._cube.entry_progress() if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')) else
                    (sum(c>=0 for c in self._cube.colors),len(self._cube.colors)))
        self.status.text=tr('poly.progress',done=done,total=total)
        self.view.refresh()

    def open_demo(self):
        if self._job is not None or self._cube is None or self.demo_button.disabled:
            return
        self.manager.get_screen('DemoMenuScreen').set_mode((self._cube.puzzle_kind,self._cube.n))
        self.manager.current='DemoMenuScreen'

    def change_view(self,direction):
        if self._view_busy or self._job is not None:
            return
        self._view_busy=True
        self.panel.disabled=True
        if self._poly_orientation is not None:
            transition=self._poly_orientation.transition(direction)
            index,angle,axis=transition
            def finish():
                self._face=self._poly_orientation.commit(*transition)
                self.view.set_whole_world(self._poly_orientation.world)
                self._finish_face_view()
            self.view.animate_whole_turn(axis,angle,.55,on_done=finish)
            return
        if self._view_orientation is not None:
            self._view_direction=direction
            ori=self._view_orientation
            angle,axis=ori.prev_axis_deg() if direction<0 else ori.next_axis_deg()
            self.view.animate_whole_turn(axis,angle,.55,on_done=self._finish_cube_view)
            return
        self._face=(self._face+direction)%len(self._cube.geometry.spec.normals)
        yaw,pitch=self._face_camera(self._face)
        roll=self._face_roll(self._face)
        while yaw-self.view.yaw>180:
            yaw-=360
        while yaw-self.view.yaw<-180:
            yaw+=360
        while roll-self.view.roll>180:
            roll-=360
        while roll-self.view.roll<-180:
            roll+=360
        Animation.cancel_all(self.view,'yaw','pitch','roll')
        animation=Animation(yaw=yaw,pitch=pitch,roll=roll,duration=.55,t='in_out_sine')
        animation.bind(on_complete=lambda *_:self._finish_face_view())
        animation.start(self.view)

    def _face_camera(self,index):
        x,y,z=self._cube.geometry.spec.normals[index]
        yaw=math.degrees(math.atan2(x,z))
        # Rotated normals can round past +/-1; atan2 also handles the poles.
        pitch=math.degrees(math.atan2(y,math.hypot(x,z)))
        return yaw,pitch

    def _set_face_camera(self,index):
        self.view.yaw,self.view.pitch=self._face_camera(index)
        self.view.roll=self._face_roll(index)

    def _face_roll(self,index):
        # Keep each tetrahedral face upright, with the same convention for
        # both Pyraminx and the curved Tower model.
        if self._cube.puzzle_kind in ('pyraminx','pyraminx_duo','coin_tetrahedron','moyu','void_tower'):
            return 180 if self._cube.geometry.spec.normals[index][1]>0 else 0
        return 0

    def _finish_cube_view(self):
        direction=self._view_direction
        if direction is None:
            return
        ori=self._view_orientation
        ori.turn_prev() if direction<0 else ori.turn_next()
        self.view.set_whole_world(ori.world)
        self._face={'U':0,'R':1,'F':2,'D':3,'L':4,'B':5}[ori.current_face()]
        self._view_direction=None
        self._finish_face_view()

    def _finish_face_view(self):
        self._view_busy=False
        self.panel.disabled=self._job is not None

    def reset_interaction(self):
        self.view.cancel_touch()
        self.view.cancel_animation()
        self._view_direction=None
        if self._poly_orientation is not None:
            self.view.set_whole_world(self._poly_orientation.world)
        elif self._view_orientation is not None:
            self.view.set_whole_world(self._view_orientation.world)
        elif self._cube is not None and self._view_busy:
            self._set_face_camera(self._face)
        self._finish_face_view()

    def _axis_selected(self,widget,text):
        pass

    # ---- EntryActionsMixin 钩子 ----
    entry_twist_screen = 'PolyhedralTwistScreen'

    def entry_can_twist(self):
        return self._job is None

    def randomize(self):
        if self._cube is None or self._job is not None or self._view_busy:
            return
        try:
            from cube.polyhedral_scramble import scramble, scramble_length
            # Prepare on a separate state. Failed imports or moves must not
            # erase the user's painted stickers or partially scramble them.
            if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
                from cube.cuboid import CuboidCube
                work=CuboidCube.solved(self._cube.puzzle_kind)
            else:
                work=self._cube.clone()
            work.colors=list(solved_colors(work))
            word=scramble(work,scramble_length(work))
            if hasattr(work,'scramble_history'):
                work.scramble_history=tuple(word)
        except Exception:
            from kivy.logger import Logger
            Logger.exception('Polyhedral: random scramble failed (%s, order %s)',
                             self._cube.puzzle_kind,self._cube.n)
            self.status.text=tr('poly.scramble_failed')
            return
        self._remember()
        self._cube.colors=list(work.colors)
        if hasattr(self._cube,'scramble_history'):
            self._cube.scramble_history=getattr(work,'scramble_history',None)
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            self._cube.frames=work.frames
            self._cube.history=work.history
            self._cube._snapshot=(tuple(work.colors),work.frames)
            self._cube._geometry_cache=None
        if self._cube.puzzle_kind.startswith('crazy_'):
            self._cube.circle_history=work.circle_history
            self._cube._circle_snapshot=tuple(work.colors)
        self.view.selected=None
        self._refresh()

    def undo(self):
        if not self.entry_can_edit():
            return
        if self._history:
            previous=self._history.pop()
            self._cube.colors=list(previous.colors if hasattr(previous,'colors') else previous)
            if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')) and hasattr(previous,'frames'):
                self._cube.frames=previous.frames
                self._cube.history=previous.history
                self._cube._snapshot=(tuple(previous.colors),previous.frames)
                self._cube._geometry_cache=None
            if self._cube.puzzle_kind.startswith('crazy_'):
                self._cube.circle_history=getattr(previous,'circle_history',None)
                self._cube._circle_snapshot=tuple(self._cube.colors)
            _app().polyhedral_solution=None
            self._refresh()

    def clear(self):
        if not self.entry_can_edit():
            return
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        actions=ResponsiveBoxLayout(height_px=44,gap_px=8)
        cancel=UIButton(text=tr('poly.cancel'))
        button=DangerButton(text=tr('poly.confirm'))
        actions.add_widget(cancel)
        actions.add_widget(button)
        box.add_widget(actions)
        popup=self._popup(tr('poly.clear'),box,(.8,.26))
        def confirm(*args):
            if not self.entry_can_edit():
                popup.dismiss()
                return
            self._remember()
            self._cube.colors=[-1]*len(self._cube.colors)
            popup.dismiss()
            self._refresh()
        button.bind(on_release=confirm)
        cancel.bind(on_release=lambda *_:popup.dismiss())

    def validate(self):
        if not self.entry_can_edit():
            return
        from solver.polyhedral import identify
        try:
            if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
                from solver.cuboid import validate_cuboid
                validate_cuboid(self._cube)
                if self._cube.puzzle_kind=='cuboid_133':
                    from solver.super_floppy import entered_index
                    entered_index(self._cube)
            elif self._cube.puzzle_kind.startswith('crazy_'):
                from solver.circle_cube import validate_circle
                validate_circle(self._cube)
            elif self._cube.puzzle_kind=='coin_tetrahedron':
                from solver.coin_tetrahedron import solve_coin_tetrahedron
                solve_coin_tetrahedron(self._cube)
            elif self._cube.puzzle_kind=='pyraminx_duo':
                from solver.pyraminx_duo import solve_pyraminx_duo
                solve_pyraminx_duo(self._cube)
            else:
                identify(self._cube)
            self.status.text=tr('circle.counts_only') if self._cube.puzzle_kind.startswith(('crazy_','cuboid_','camouflage_3')) and self._cube.puzzle_kind!='cuboid_133' else tr('poly.valid')
        except ValueError as exc:
            self.error(str(exc))

    def entry_can_assign(self):
        return self._job is None

    def entry_reset_solved(self):
        self._remember()
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            from cube.cuboid import CuboidCube
            solved=CuboidCube.solved(self._cube.puzzle_kind)
            self._cube.frames=solved.frames
            self._cube.history=[]
            self._cube._geometry_cache=None
        self._cube.colors=list(solved_colors(self._cube))
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            self._cube._snapshot=(tuple(self._cube.colors),self._cube.frames)

    def entry_commit_state(self):
        app=_app()
        app.cube=self._cube
        app.puzzle_kind=getattr(self._cube,'puzzle_kind',app.puzzle_kind)
        app.polyhedral_solution=None
        self._refresh()

    def entry_set_status(self, text, error=False):
        self.status.text=text

    def solve(self):
        if not self.entry_can_edit():
            return
        if self._job is not None:
            return
        entered=self._cube.entered()
        palette=tuple(self.view.palette)
        def solved(result):
            _app().polyhedral_solution=(entered,result.moves,palette)
            self.manager.current='PolyhedralPlaybackScreen'
        screen=self.manager.get_screen('SolvingScreen')
        screen.configure(entered,self.name,solved,_view_for(entered),palette)
        self.manager.current='SolvingScreen'

    def customize(self):
        picker=ColorPicker(color=self.view.palette[self._color])
        box=ResponsiveBoxLayout(orientation='vertical',gap_px=8)
        box.add_widget(picker)
        actions=ResponsiveBoxLayout(height_px=44,gap_px=8)
        restore=UIButton(text=tr('poly.restore_colors'))
        apply=PrimaryButton(text=tr('poly.apply'))
        actions.add_widget(restore)
        actions.add_widget(apply)
        box.add_widget(actions)
        popup=self._popup(tr('poly.palette'),box,(.9,.85))
        def save(*args):
            palette=list(self.view.palette)
            palette[self._color]=tuple(picker.color[:3])+(1,)
            self._save_palette(palette)
            popup.dismiss()
        def reset(*args):
            self._save_palette(default_palette(self._cube))
            picker.color=self.view.palette[self._color]
        restore.bind(on_release=reset)
        apply.bind(on_release=save)

    def _save_palette(self,palette):
        self.view.palette=tuple(palette)
        from app.prefs import set as pref_set
        pref_set('poly_palette_'+self._cube.puzzle_kind,[list(c) for c in palette])
        self._build_palette()
        self.view.refresh()

    def _popup(self,title,content,size=(.85,.4),**kwargs):
        popup=Popup(title=title,content=content,size_hint=size,**kwargs)
        theme_popup(popup,_app().theme)
        popup.open()
        return popup

    def error(self,message):
        errors={
            'Please enter every sticker':'incomplete',
            'The color counts do not match this puzzle':'counts',
            'A piece has an impossible color combination or position':'piece',
            'A piece has a mirrored or impossible orientation':'orientation',
            'Repeated color on a piece':'piece', 'Duplicate piece':'piece',
            'The entered core has an impossible orientation':'orientation',
            'The entered core violates an orientation constraint':'orientation',
            'Position must be restored before adjusting orientation':'illegal',
            'Mirrored or impossible core orientation':'orientation',
            'The entered puzzle is not a legal state':'illegal',
            'Odd orbit permutation':'illegal',
            'The entered pieces violate an orientation or permutation constraint':'illegal',
        }
        input_error=message in errors
        if message in ('Polyhedral reduction replay failed','Blossom reduction replay failed'):
            message=tr('poly.error.replay')
        else:
            message=tr('poly.error.'+errors[message]) if input_error else tr('poly.error.solver',detail=message)
        content=Label(text=message,halign='center',valign='middle',color=_app().theme.text)
        content.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self._popup(tr('poly.error' if input_error else 'poly.error.solve_title'),content)

    def help(self):
        label=Label(text=tr('poly.help'),halign='left',valign='middle',color=_app().theme.text)
        label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        self._popup(tr('poly.help_title'),label,(.94,.78))

    def back(self):
        self._cancel_solve()
        self.reset_interaction()
        self.panel.disabled=False
        if getattr(_app(),'input_from_camera',False):
            self.manager.current='CameraScreen'
            return
        self.manager.current='HomeScreen'

    def on_leave(self,*args):
        self._cancel_solve()
        self.reset_interaction()
        self.panel.disabled=False

    def _cancel_solve(self):
        self._cancel.set()
        self._job=None
        if self._solve_popup:
            self._solve_popup.dismiss()
            self._solve_popup=None

    def retranslate(self):
        self.follow_control.retranslate()
        if self._cube:
            self.title.text=f'{_puzzle_title(self._cube)} · {tr("directory.order",order=self._cube.n)}'
            if self._cube.puzzle_kind.startswith(('crazy_','cuboid_','camouflage_3')) or self._cube.puzzle_kind in ('helicopter','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb'):
                self.title.text=_puzzle_title(self._cube)
        kind=self._cube.puzzle_kind if self._cube else ''
        self.hint.text=tr('poly.super_floppy_input') if kind=='cuboid_133' else tr('poly.camouflage_input') if kind=='camouflage_3' else tr('poly.cuboid_input') if kind.startswith(('cuboid_','camouflage_3')) else tr('poly.circle_input') if kind.startswith('crazy_') else tr('poly.'+kind+'_input') if kind in ('helicopter','clover','eight_petals','football','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb','fisher_skewb','ghost_pyramid','dino','war_drum','pentahedron') else tr('poly.input_hint')

    def refresh_theme(self):
        for label in (self.title,self.hint,self.status):
            label.color=_app().theme.text


class PolyhedralPlaybackScreen(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._playing=False
        self._hold=None
        self._hold_time=0.5
        self._work=None
        self._index=0
        self._seek_job=None
        self._pending_move=None
        self.build_ui()

    def build_ui(self):
        from ui.screens.playback_screen import _ProgressTrack
        self._simple=bool(getattr(_app(),'simple_input',False))
        root=AdaptiveSceneLayout(padding_px=[28,8,28,8],gap_px=6)
        initial=getattr(_app(),'polyhedral_solution',None)
        self._render_kind=initial[0].puzzle_kind if initial else None
        self.view=_view_for(initial[0] if initial else None)()
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=8,size_hint_y=None)
        self.view.lock_rotation=self._simple
        info=ResponsiveBoxLayout(orientation='vertical',height_px=72,gap_px=4)
        self.title=Label(font_size='15sp',halign='center')
        self.status=Label(font_size='18sp',halign='center')
        for label in (self.title,self.status):
            label.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
            info.add_widget(label)
        panel.add_widget(info)
        self.track=_ProgressTrack(maximum=1,value=0,size_hint_y=None,height=m.h(6))
        panel.bind(height=lambda *_:setattr(self.track,'height',m.h(6)))
        panel.add_widget(self.track)
        controls=ResponsiveBoxLayout(orientation='vertical',height_px=110,gap_px=6)
        row=ResponsiveBoxLayout(gap_px=8)
        self._playback_buttons={}
        for icon,fn in (('first',self.to_start),('prev',self.prev),('solve',self.play),
                        ('next',self.next),('last',self.to_end)):
            button=PrimaryButton(icon_name=icon) if icon=='solve' else UIButton(icon_name=icon)
            button.bind(on_release=lambda *_,f=fn:f())
            self._playback_buttons[icon]=button
            if not self._simple or icon not in ('first','last'):
                row.add_widget(button)
            if icon=='solve':
                self.play_button=button
        controls.add_widget(row)
        row=ResponsiveBoxLayout(gap_px=8)
        for icon,fn in (('reset',self.reset_view),('back',self.confirm_back)):
            b=UIButton(icon_name=icon)
            b.bind(on_release=lambda *_,f=fn:f())
            if not self._simple or icon=='back':
                row.add_widget(b)
        controls.add_widget(row)
        panel.add_widget(controls)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.speed_label=Label(text=tr('playback.speed'),font_size='15sp',size_hint_x=.24)
        self.speed=Slider(min=.25,max=2,value=getattr(self,'_speed_value',1),step=.25,size_hint_x=.76)
        self.speed.bind(value=lambda w,v:setattr(self,'_speed_value',v))
        row.add_widget(self.speed_label)
        row.add_widget(self.speed)
        panel.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.hold_label=Label(text=tr('playback.hold'),font_size='15sp',size_hint_x=.24)
        self.hold=Slider(min=0.0,max=6.0,value=self._hold_time,step=0.1,size_hint_x=.76)
        self.hold.bind(value=lambda inst,val:setattr(self,'_hold_time',max(0.0,val)))
        row.add_widget(self.hold_label)
        row.add_widget(self.hold)
        panel.add_widget(row)
        panel,self.follow_control=follow_panel(panel,self.view)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def retranslate(self):
        self.speed_label.text=tr('playback.speed')
        self.hold_label.text=tr('playback.hold')
        self.follow_control.retranslate()
        if self._work is not None:
            self._refresh()

    def refresh_theme(self):
        if self._work is not None:
            self._refresh()

    def on_pre_enter(self,*args):
        self.stop()
        self._cancel_step()
        if self._simple!=bool(getattr(_app(),'simple_input',False)) or self._render_kind!=_app().polyhedral_solution[0].puzzle_kind:
            self.view.cancel_animation()
            self.clear_widgets()
            self.build_ui()
        self._initial,self._moves,palette=_app().polyhedral_solution
        self._work=self._initial.clone()
        self._index=0
        self._checkpoints={0:self._work.clone() if self._work.puzzle_kind.startswith(('cuboid_','camouflage_3')) else tuple(self._work.colors)}
        self.view.set_cube(self._work)
        if len(palette)==len(self._work.geometry.spec.normals):
            self.view.palette=palette
        self.track.maximum=max(1,len(self._moves))
        self.title.text=tr('poly.solution',total=len(self._moves))
        self._refresh()

    def _refresh(self):
        from demo.irregular_cases import token
        active=self.view._move if self.view._move is not None else self._pending_move
        current=(token(active,self._work.geometry.spec) if active is not None else
                 token(self._moves[self._index-1],self._work.geometry.spec) if self._index else tr('playback.ready'))
        if self._work.puzzle_kind in ('football','war_drum','pentahedron'):
            move=active if active is not None else self._moves[self._index-1] if self._index else None
            if move is not None:
                order=self._work.geometry.spec.turn_order
                amount=move.amount%order
                if amount>order/2:
                    amount-=order
                current=tr('poly.face_turn',face=move.axis+1,layer=move.layer+1,angle=amount*360//order)
        elif self._work.puzzle_kind in ('helicopter','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre'):
            move=active if active is not None else self._moves[self._index-1] if self._index else None
            if move is not None:
                from cube.polyhedral import dot
                spec=self._work.geometry.spec
                axis=spec.axes[move.axis]
                nearest=max(dot(n,axis) for n in spec.normals)
                faces='/'.join(str(i+1) for i,n in enumerate(spec.normals)
                               if abs(dot(n,axis)-nearest)<1e-7)
                current=tr('poly.blossom_turn',faces=faces)
        self.title.text=tr('playback.current',move=current)
        self.status.text=tr('poly.step',done=self._index,total=len(self._moves))
        self.track.value=self._index
        self.play_button.icon_name='pause' if self._playing else 'solve'
        busy=active is not None or self._seek_job is not None
        self._playback_buttons['prev'].disabled=busy or self._index<=0
        self._playback_buttons['next'].disabled=busy or self._index>=len(self._moves)
        self._playback_buttons['first'].disabled=busy or self._index<=0
        self._playback_buttons['last'].disabled=busy or self._index>=len(self._moves)
        self.view.refresh()
        for label in (self.title,self.status,self.speed_label,self.hold_label):
            label.color=_app().theme.text

    def next(self,*args):
        self.stop()
        self._advance()

    def _advance(self,*args):
        if self.view._move is not None or self._pending_move is not None or self._seek_job is not None:
            return
        if self._index>=len(self._moves):
            self.stop()
            return
        def done():
            self._index+=1
            if self._index%128==0:
                self._checkpoints[self._index]=self._work.clone() if self._work.puzzle_kind.startswith(('cuboid_','camouflage_3')) else tuple(self._work.colors)
            self._refresh()
            if self._playing:
                self._hold=Clock.schedule_once(self._advance,self._hold_time)
        self._animate_followed(self._moves[self._index],done)
        self._refresh()

    def prev(self):
        self.stop()
        self._cancel_step()
        if self._seek_job is not None:
            self.seek(self._index-1)
            return
        if self._index<=0:
            self._refresh()
            return
        move=self._moves[self._index-1].inverse(self._work.geometry.spec.turn_order)
        def done():
            self._index-=1
            self._refresh()
        self._animate_followed(move,done)
        self._refresh()

    def _animate_followed(self,move,done):
        self._pending_move=move
        self._refresh()
        def begin():
            if self._pending_move is not move:
                return
            self._pending_move=None
            self.view.animate_move(move,done,duration=.32/self.speed.value)
            self._refresh()
        follow_turn(self.view,polyhedral_target(self._work,move),begin)

    def _cancel_step(self):
        self._pending_move=None
        cancel_follow(self.view)
        self.view.cancel_animation()

    def reset_view(self):
        if self._pending_move is None:
            reset_camera_view(self.view)

    def play(self):
        if self._seek_job is not None:
            return
        if self._playing:
            self.stop()
        else:
            self._playing=True
            self._refresh()
            self._advance()

    def stop(self):
        self._playing=False
        if self._hold:
            self._hold.cancel()
        self._hold=None
        if self._work is not None:
            self._refresh()

    def seek(self,index):
        self.stop()
        self._cancel_step()
        index=max(0,min(len(self._moves),int(index)))
        nearest=max(k for k in self._checkpoints if k<=index)
        job=object()
        self._seek_job=job
        work=self._initial.clone()
        cuboid=work.puzzle_kind.startswith(('cuboid_','camouflage_3'))
        if cuboid:
            work.restore(self._checkpoints[nearest])
        else:
            work.colors=list(self._checkpoints[nearest])
        checkpoints={}
        def finish():
            if self._seek_job is not job:
                return
            self._seek_job=None
            if cuboid:
                self._work.restore(work)
            else:
                self._work.colors=work.colors
            self._checkpoints.update(checkpoints)
            self._index=index
            self._refresh()
        def worker():
            for k in range(nearest,index):
                if self._seek_job is not job:
                    return
                work.apply_move(self._moves[k])
                if (k+1)%128==0:
                    checkpoints[k+1]=work.clone() if cuboid else tuple(work.colors)
            Clock.schedule_once(lambda dt:finish(),0)
        if index-nearest>128:
            self.status.text=tr('poly.seeking')
            threading.Thread(target=worker,daemon=True).start()
        else:
            worker()

    def to_start(self):
        self._confirm_playback(tr('playback.confirm.start'),lambda:self.seek(0))

    def to_end(self):
        self._confirm_playback(tr('playback.confirm.end'),lambda:self.seek(len(self._moves)))

    def confirm_back(self):
        self._confirm_playback(tr('playback.confirm.back'),self.back)

    def _confirm_playback(self,message,on_confirm):
        self.stop()
        content=BoxLayout(orientation='vertical',spacing=12,padding=16)
        label=Label(text=message,halign='center',font_size='18sp',size_hint_y=1)
        buttons=BoxLayout(orientation='horizontal',spacing=8,size_hint_y=None,height=m.h(52))
        popup=Popup(title=tr('confirm.title'),content=content,size_hint=(.86,.42))
        cancel=UIButton(text='',icon_name='cancel')
        cancel.bind(on_release=lambda *_:popup.dismiss())
        confirm=PrimaryButton(text='',icon_name='done')
        confirm.bind(on_release=lambda *_:(on_confirm(),popup.dismiss()))
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        content.add_widget(label)
        content.add_widget(buttons)
        theme_popup(popup,_app().theme)
        popup.open()

    def _seek_touch(self,widget,touch):
        if widget.collide_point(*touch.pos):
            self.seek(round(widget.value))

    def back(self):
        self.stop()
        self._cancel_step()
        self.manager.current=_entry_for(self._work)

    def on_leave(self,*args):
        self._seek_job=None
        self.stop()
        self._cancel_step()


class PolyhedralTwistScreen(Screen):
    """专门的异形魔方拧动界面：选择转轴/层，顺逆拧动，左右切换观察面。

    与普通魔方的 TwistScreen 一样，录入页本身不再内嵌拧动控件；本页直接
    操作录入中的 PolyhedralPuzzle（同一对象），返回后录入页即时反映改动。
    """

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self._cube=None
        self._face=0
        self._axis=0
        self._layer=0
        self._history=[]
        self._future=[]
        self._build()

    def _build(self):
        root=AdaptiveSceneLayout(padding_px=[12,8,12,8],gap_px=8)
        top=ResponsiveBoxLayout(height_px=44,gap_px=8)
        back=UIButton(icon_name='back',size_hint_x=.16)
        back.bind(on_release=lambda *_:self.back())
        self.title=Label(font_size='20sp')
        done=PrimaryButton(icon_name='done',size_hint_x=.16)
        done.bind(on_release=lambda *_:self.back())
        for item in (back,self.title,done):
            top.add_widget(item)
        root.add_widget(top)
        self.view=_view_for(getattr(_app(),'cube',None),True)()
        self.view.on_twist=self.twist
        panel=ResponsiveBoxLayout(orientation='vertical',gap_px=7,size_hint_y=None)
        history=ResponsiveBoxLayout(height_px=48,gap_px=8)
        self.btn_undo=UIButton(icon_name='undo')
        self.btn_undo.bind(on_release=lambda *_:self.undo())
        self.btn_redo=UIButton(icon_name='redo')
        self.btn_redo.bind(on_release=lambda *_:self.redo())
        history.add_widget(self.btn_undo)
        history.add_widget(self.btn_redo)
        panel.add_widget(history)
        observation=ResponsiveBoxLayout(height_px=48,gap_px=8)
        prev=UIButton(icon_name='prev')
        prev.bind(on_release=lambda *_:self.change_view(-1))
        self.btn_lock=UIButton(icon_name='lock')
        self.btn_lock.bind(on_release=lambda *_:self.toggle_lock())
        reset=UIButton(icon_name='reset')
        reset.bind(on_release=lambda *_:reset_camera_view(self.view))
        nxt=UIButton(icon_name='next')
        nxt.bind(on_release=lambda *_:self.change_view(1))
        for widget in (prev,self.btn_lock,reset,nxt):
            observation.add_widget(widget)
        panel.add_widget(observation)
        layer_row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.axis=Spinner(text='',values=())
        self.axis.bind(text=self._axis_selected)
        self.layer=Spinner(text='',values=())
        self.layer.bind(text=self._layer_selected)
        backward=UIButton(icon_name='undo',size_hint_x=.28)
        backward.bind(on_release=lambda *_:self.turn(-1))
        forward=UIButton(icon_name='redo',size_hint_x=.28)
        forward.bind(on_release=lambda *_:self.turn(1))
        for item in (self.axis,self.layer,backward,forward):
            layer_row.add_widget(item)
        panel.add_widget(layer_row)
        self.alignment_button=UIButton(size_hint_y=None,height=0)
        self.alignment_button.bind(on_release=lambda *_:self.toggle_alignment())
        panel.add_widget(self.alignment_button)
        self.hint=Label(text=tr('twist.hint_lock_on'),size_hint_y=None,height=m.h(54),
                        font_size='13sp',halign='center',valign='middle')
        self.hint.bind(size=lambda w,*_:setattr(w,'text_size',w.size))
        panel.add_widget(self.hint)
        self.panel=panel
        panel,self.follow_control=follow_panel(panel,self.view,self._camera_lock_changed,show_lock=False)
        root.set_content(self.view,panel)
        self.add_widget(root)

    def on_pre_enter(self,*args):
        self._source = _entry_for(_app().cube)
        self._cube=_app().cube
        if self._cube is None or not hasattr(self._cube,'geometry'):
            return
        if type(self.view) is not _view_for(self._cube,True):
            self.view.cancel_animation()
            self.clear_widgets()
            self._build()
        self.view.cancel_touch()
        self.view.set_cube(self._cube)
        self.follow_control.bind_view(self.view,self._camera_lock_changed)
        self._cuboid_entry_snapshot=self._cube.clone() if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')) else None
        self._entry_snapshot=(tuple(self._cube.colors)
                              if self._cube.puzzle_kind not in ('mirror_tower','mirror_pyraminx','mirror_skewb','fisher_skewb','ghost_pyramid') else None)
        self._history=[]
        self._future=[]
        self._face=0
        ghost=self._cube.puzzle_kind=='ghost_pyramid'
        self.alignment_button.height=m.h(44) if ghost else 0
        self.alignment_button.opacity=1 if ghost else 0
        self.alignment_button.disabled=not ghost
        self._update_controls()
        from app.prefs import get as pref_get
        saved=pref_get('poly_palette_'+self._cube.puzzle_kind,None)
        count=getattr(self._cube,'color_count',len(self._cube.geometry.spec.normals))
        if isinstance(saved,list) and len(saved)==count and all(
            isinstance(c,list) and len(c)==4 for c in saved):
            self.view.palette=tuple(tuple(c) for c in saved)
        self.view.selected=None
        self.view.reset_camera() if hasattr(self.view,'reset_camera') else None
        self.axis.values=self._axis_labels()
        self._axis=self._initial_axis()
        self.axis.text=self.axis.values[self._axis]
        self._set_layers()
        self.retranslate()
        self.refresh_theme()
        self.view.refresh()

    def retranslate(self):
        self.follow_control.retranslate()
        if self._cube is not None:
            self.title.text=f'{_puzzle_title(self._cube)} · {tr("input.twist")}'
            self.axis.values=self._axis_labels()
            self.axis.text=self.axis.values[self._axis]
        kind=self._cube.puzzle_kind if self._cube else ''
        if kind.startswith(('cuboid_','camouflage_3')):
            self.hint.text=tr('poly.cuboid_twist')
        elif kind.startswith('crazy_'):
            self.hint.text=tr('poly.circle_twist')
        elif kind in ('helicopter','clover','eight_petals','football','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb','fisher_skewb','ghost_pyramid','dino','war_drum','pentahedron'):
            self.hint.text=tr('poly.'+kind+'_twist')
        else:
            self.hint.text=tr('poly.twist_hint_on') if self.view.lock_view else tr('poly.twist_hint_off')

    def _initial_axis(self):
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            from cube.polyhedral import dot
            yaw,pitch=math.radians(self.view.yaw),math.radians(self.view.pitch)
            eye=(math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch))
            legal={move.axis for move in self._cube.moves()}
            return max(legal,key=lambda i:dot(self._cube.geometry.spec.axes[i],eye)) if legal else 0
        if self._cube.puzzle_kind not in ('dino','pyraminx_duo','super_ivy','mosaic','tins','dino_skewb','dayan_dino_skewb','helicopter','war_drum','pentahedron'):
            return 0
        # Dino axis zero points behind the default camera. Choose the visible
        # corner so the first button turn is visible, even before a drag.
        from cube.polyhedral import dot
        yaw,pitch=math.radians(self.view.yaw),math.radians(self.view.pitch)
        eye=(math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch))
        world=self.view.observation_world()
        return max(range(len(self._cube.geometry.spec.axes)),key=lambda i:
                   dot(world.transform(*self._cube.geometry.spec.axes[i]),eye))

    def _axis_labels(self):
        spec=self._cube.geometry.spec
        if spec.kind.startswith(('cuboid_','camouflage_3')):
            from cube.cuboid import FACES
            return tuple(f'{face} · {90*spec.step(i)}°' for i,face in enumerate(FACES))
        if spec.kind.startswith('crazy_'):
            from cube.circle_cube import PLANETS,FACES
            one=PLANETS[spec.kind[6:]]
            return tuple(f'{i+1} · {face} · {int(face in one)}' for i,face in enumerate(FACES))
        if spec.kind=='coin_tetrahedron':
            return tuple(tr('coin.disc',face=i+1) if i<4 else tr('coin.corner',axis=i-3) for i in range(8))
        if spec.kind in ('football','war_drum','pentahedron'):
            return tuple(f'{tr("poly.face",i=i+1)} · {360//spec.order(i)}°' for i in range(len(spec.axes)))
        if spec.kind not in ('helicopter','clover','eight_petals','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb','dino'):
            return tuple(tr('poly.axis',i=i+1) for i in range(len(spec.axes)))
        from cube.polyhedral import dot
        role='poly.edge' if spec.kind in ('helicopter','clover','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre') else 'poly.corner'
        if spec.kind=='dayan_dino_skewb':
            return tuple(tr('poly.axis',i=j+1)+' · '+tr(role,faces='/'.join(
                str(i+1) for i,normal in enumerate(spec.normals)
                if abs(dot(normal,axis)-max(dot(n,axis) for n in spec.normals))<1e-7))+
                (' · Dino / Skewb' if len(self._cube.geometry.layers[j])==2 else ' · Skewb')
                for j,axis in enumerate(spec.axes))
        if spec.kind in ('ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb','dino'):
            return tuple(tr('poly.axis',i=j+1)+' · '+tr(role,faces='/'.join(
                str(i+1) for i,normal in enumerate(spec.normals)
                if abs(dot(normal,axis)-max(dot(n,axis) for n in spec.normals))<1e-7))
                for j,axis in enumerate(spec.axes))
        # Face numbers match the palette and the model's face labels.
        return tuple(tr(role,faces='/'.join(str(i+1) for i,normal in enumerate(spec.normals)
                                            if abs(dot(normal,axis)-max(dot(n,axis) for n in spec.normals))<1e-7)) for axis in spec.axes)

    def refresh_theme(self):
        self.title.color=_app().theme.text
        self.hint.color=_app().theme.text

    def change_view(self,direction):
        if self._cube is None or self.view._move is not None:
            return
        self.view.cancel_touch()
        normals=self._cube.geometry.spec.normals
        if self._cube.puzzle_kind=='ghost_pyramid':
            from cube.ghost_pyramid import shell_normals
            normals=shell_normals()
        self._face=(self._face+direction)%len(normals)
        x,y,z=normals[self._face]
        yaw=math.degrees(math.atan2(x,z))
        while yaw-self.view.yaw>180:
            yaw-=360
        while yaw-self.view.yaw<-180:
            yaw+=360
        pitch=math.degrees(math.atan2(y,math.hypot(x,z)))
        Animation.cancel_all(self.view,'yaw','pitch')
        self.view.camera_busy=True
        animation=Animation(yaw=yaw,pitch=pitch,duration=.45,t='in_out_sine')
        animation.bind(on_complete=lambda *_:setattr(self.view,'camera_busy',False))
        animation.start(self.view)

    def _axis_selected(self,widget,text):
        if text in widget.values:
            self._axis=widget.values.index(text)
            self._layer=0
            self._set_layers()

    def _set_layers(self):
        if self._cube is None:
            return
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            from cube.polyhedral import Move
            legal=[i for i in range(self._cube.core_n-1) if self._cube.can_apply(Move(self._axis,i,self._cube.geometry.spec.step(self._axis)))]
            self.layer.values=self._cube.layer_labels(self._axis)
            self.layer.disabled=not legal
            self._layer=self._layer if self._layer in legal else legal[0] if legal else 0
            self.layer.text=self.layer.values[self._layer]
            self.view.selected_turn_layer=self._layer
            return
        if self._cube.puzzle_kind in ('helicopter','clover','eight_petals','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron'):
            self.layer.values=(f'{360//self._cube.geometry.spec.turn_order}°',)
            self.layer.disabled=True
        elif self._cube.puzzle_kind=='dino_skewb':
            self.layer.disabled=False
            self.layer.values=(tr('poly.dino_shallow'),tr('poly.skewb_deep'))
        elif self._cube.puzzle_kind=='dayan_dino_skewb':
            count=len(self._cube.geometry.layers[self._axis])
            self.layer.disabled=count==1
            self.layer.values=((tr('poly.dino_shallow'),tr('poly.skewb_deep'))
                               if count==2 else (tr('poly.skewb_deep'),))
        elif self._cube.puzzle_kind in ('mosaic','tins'):
            self.layer.disabled=False
            self.layer.values=(tr('poly.corner_outer'),tr('poly.corner_inner'))
        elif self._cube.puzzle_kind=='skewb':
            self.layer.disabled=False
            count=len(self._cube.geometry.layers[self._axis])
            self.layer.values=(tr('poly.skewb_outer_near'),)+tuple(
                tr('poly.skewb_slice',i=i) for i in range(1,count-1))+(tr('poly.skewb_outer_far'),)
        else:
            self.layer.disabled=False
            self.layer.values=tuple(tr('poly.layer',i=i+1)
                                    for i in range(len(self._cube.geometry.layers[self._axis])))
        self.layer.text=self.layer.values[0]
        self._layer=0
        self.view.selected_turn_layer=0
        self.view.dino_skewb_mode=('dino' if len(self.layer.values)==2 else 'skewb')

    def _layer_selected(self,widget,text):
        if text in widget.values:
            self._layer=widget.values.index(text)
            self.view.selected_turn_layer=self._layer
            self.view.dino_skewb_mode=('dino' if len(widget.values)==2 and self._layer==0 else 'skewb')

    def _update_controls(self):
        if self._cube is not None and self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            self._set_layers()
        if self._cube is not None and self._cube.puzzle_kind=='ghost_pyramid':
            self.alignment_button.text=tr('ghost_pyramid.close' if abs(self._cube.phase)<1e-8 else 'ghost_pyramid.open')
        self.btn_undo.disabled=not self._history
        self.btn_redo.disabled=not self._future
        self.btn_lock.icon_name='lock' if self.view.lock_view else 'unlock'
        self.btn_lock.active=self.view.lock_view

    def _camera_lock_changed(self,locked):
        self.btn_lock.icon_name='lock' if locked else 'unlock'
        self.btn_lock.active=locked
        kind=self._cube.puzzle_kind if self._cube else ''
        if kind.startswith(('cuboid_','camouflage_3')):
            self.hint.text=tr('poly.cuboid_twist')
        elif kind.startswith('crazy_'):
            self.hint.text=tr('poly.circle_twist')
        elif kind in ('helicopter','clover','eight_petals','football','blossom','petal_icosahedron','petal_icosahedron_nocentre','petal_tetrahedron','petal_tetrahedron_nocentre','ivy','super_ivy','pyraminx_duo','coin_tetrahedron','mosaic','tins','dino_skewb','dayan_dino_skewb','fisher_skewb','ghost_pyramid','dino','war_drum','pentahedron'):
            self.hint.text=tr('poly.'+kind+'_twist')
        else:
            self.hint.text=tr('poly.twist_hint_on') if locked else tr('poly.twist_hint_off')

    def toggle_alignment(self):
        if self._cube is not None and self._cube.puzzle_kind=='ghost_pyramid':
            self.twist(self._cube.alignment_move(close=abs(self._cube.phase)<1e-8))

    def toggle_lock(self):
        FOLLOW_SETTINGS.locked=not FOLLOW_SETTINGS.locked

    def twist(self,move):
        if self._cube is None or self.view._move is not None or self.view.camera_busy:
            return
        if self._cube.puzzle_kind=='ghost_pyramid' and not self._cube.can_apply(move):
            self.hint.text=tr('ghost_pyramid.align_first')
            return
        if self._cube.puzzle_kind.startswith(('cuboid_','camouflage_3')) and not self._cube.can_apply(move):
            self.hint.text=tr('cuboid.blocked')
            return
        # Keep button turns on the axis/layer most recently used by a drag.
        # Setting the axis label rebuilds layer values before selecting a layer.
        self._axis=move.axis
        self.axis.text=self.axis.values[move.axis]
        self._layer=move.layer
        self.layer.text=self.layer.values[move.layer]
        self._history.append(move)
        self._future.clear()
        self._animate(move)

    def undo(self):
        if self.view._move is not None or self.view.camera_busy or not self._history:
            return
        move=self._history.pop()
        self._future.append(move)
        self._animate(move.inverse(self._cube.geometry.spec.turn_order))

    def redo(self):
        if self.view._move is not None or self.view.camera_busy or not self._future:
            return
        move=self._future.pop()
        self._history.append(move)
        self._animate(move)

    def _animate(self,move):
        self.view.cancel_touch()
        self.panel.disabled=True
        self._update_controls()
        if self._cube.puzzle_kind in ('mirror_tower','mirror_pyraminx','mirror_skewb','fisher_skewb','ghost_pyramid'):
            entry=self.manager.get_screen(_entry_for(self._cube))
            from cube.ghost_pyramid import PyramidAlignment
            permutation=(tuple(range(len(self._cube.geometry.stickers)))
                         if isinstance(move,PyramidAlignment) else self._cube.geometry.permutation(move))
            entry._remember()
            recorded={self._cube.geometry.stickers[permutation[self._cube.geometry.pieces[p][0]]].piece
                      for p in entry._recorded}
        else:
            recorded=None
        def done():
            _app().polyhedral_solution=None
            if recorded is not None:
                entry._recorded=recorded
            self.panel.disabled=False
            self._update_controls()
            self.view.refresh()
        def begin():
            if not self.view.animate_move(move,done):
                self.panel.disabled=False
        follow_turn(self.view,polyhedral_target(self._cube,move),begin)

    def turn(self,direction):
        if self._cube is not None:
            spec=self._cube.geometry.spec
            self.twist(Move(self._axis,self._layer,direction*spec.step(self._axis)%spec.turn_order))

    def back(self):
        if self.view._move is not None or self.view.camera_busy:
            return
        initial=getattr(self,'_entry_snapshot',None)
        shape_snapshot=getattr(self,'_cuboid_entry_snapshot',None)
        if shape_snapshot is not None:
            if (tuple(self._cube.colors),self._cube.frames)!=(tuple(shape_snapshot.colors),shape_snapshot.frames):
                entry=self.manager.get_screen('PolyhedralScreen')
                entry._history.append(shape_snapshot)
                entry._history=entry._history[-40:]
            initial=None
        if initial is not None and tuple(self._cube.colors)!=initial:
            entry=self.manager.get_screen('PolyhedralScreen')
            entry._history.append(initial)
            entry._history=entry._history[-40:]
            self._entry_snapshot=None
        self.view.cancel_touch()
        self.view.cancel_animation()
        self.panel.disabled=False
        self.manager.current=_entry_for(self._cube)

    def reset_interaction(self):
        self.view.cancel_touch()

    def on_leave(self,*args):
        self.view.cancel_touch()
        cancel_follow(self.view)
        self.view.camera_busy=False
        self.view.cancel_animation()
        self.panel.disabled=False
