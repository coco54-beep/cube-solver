"""Shape-card Ghost Pyramid entry with a visible opening/closing control."""
import math
from kivy.animation import Animation
from app.i18n import tr
from cube.ghost_pyramid import GhostPyramidCube, CLOSED_PHASE, shell_normals
from renderer.ghost_pyramid_view import GhostPyramidView
from ui.screens.mirror_skewb_screen import MirrorSkewbScreen
from ui.screens.polyhedral_screen import _app
from ui.widgets.buttons import UIButton
from ui.widgets import metrics as m


class GhostPyramidScreen(MirrorSkewbScreen):
    cube_class=GhostPyramidCube
    view_class=GhostPyramidView
    hint_key='ghost_pyramid.input'

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.alignment_button=UIButton(size_hint_y=None,height=m.h(40))
        self.alignment_button.bind(on_release=lambda *_:self.toggle_alignment())
        self.panel.add_widget(self.alignment_button,index=2)

    def _new_cube(self,pieces=None):
        return GhostPyramidCube(pieces,phase=getattr(self._cube,'phase',CLOSED_PHASE))

    def on_pre_enter(self,*args):
        super().on_pre_enter(*args)
        self._poly_orientation=self._view_orientation=None
        self._face%=4
        self._set_face_camera(self._face)
        self._refresh()

    def _face_camera(self,index):
        x,y,z=shell_normals()[index]
        return math.degrees(math.atan2(x,z)),math.degrees(math.atan2(y,math.hypot(x,z)))

    def change_view(self,direction):
        if not self.entry_can_edit(): return
        self._face=(self._face+direction)%4
        yaw,pitch=self._face_camera(self._face)
        while yaw-self.view.yaw>180: yaw-=360
        while yaw-self.view.yaw<-180: yaw+=360
        self._view_busy=True
        self.panel.disabled=True
        animation=Animation(yaw=yaw,pitch=pitch,roll=0,duration=.45,t='in_out_sine')
        animation.bind(on_complete=lambda *_:self._finish_face_view())
        animation.start(self.view)

    def _remember(self):
        self._history.append((dict(self._cube.pieces),set(self._recorded),self._cube.phase))
        self._history=self._history[-40:]
        _app().polyhedral_solution=None

    def undo(self):
        if self.entry_can_edit() and self._history:
            self._cube.pieces,self._recorded,self._cube.phase=self._history.pop()
            _app().polyhedral_solution=None
            self._refresh()

    def toggle_alignment(self):
        if not self.entry_can_edit(): return
        self._remember()
        self._view_busy=True
        self.panel.disabled=True
        move=self._cube.alignment_move(close=abs(self._cube.phase)<1e-8)
        self.view.animate_move(move,lambda:(self._finish_face_view(),self._refresh()))

    def randomize(self):
        if not self.entry_can_edit(): return
        from cube.polyhedral_scramble import scramble
        work=GhostPyramidCube(phase=0.)
        scramble(work,24)
        self._remember()
        self._cube.pieces,self._cube.phase=work.pieces,work.phase
        self._recorded=set(work.pieces)
        self._refresh()

    def _clear_now(self):
        if not self.entry_can_edit(): return
        super()._clear_now()
        self._cube.phase=CLOSED_PHASE
        self._refresh()

    def entry_reset_solved(self):
        super().entry_reset_solved()
        self._cube.phase=CLOSED_PHASE

    def _refresh(self):
        super()._refresh()
        if self._cube is not None:
            self.title.text=tr('directory.ghost_pyramid')
            if hasattr(self,'alignment_button'):
                self.alignment_button.text=tr('ghost_pyramid.close' if abs(self._cube.phase)<1e-8 else 'ghost_pyramid.open')
