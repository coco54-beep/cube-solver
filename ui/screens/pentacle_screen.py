"""Paint entry with an unrestricted circular-disc angle preview."""
from ui.entry_feedback import validation_action
import random
import threading
from time import monotonic
from kivy.clock import Clock
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from app.i18n import tr
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from renderer.pentacle_view import PentacleView
from ui.screens.polyhedral_screen import PolyhedralScreen,_app
from ui.widgets.layouts import ResponsiveBoxLayout
from ui.widgets.buttons import UIButton,PrimaryButton

class PentacleScreen(PolyhedralScreen):
    view_class=PentacleView
    def __init__(self,**kwargs):
        self._angle_updating=False;self._recorded=set()
        super().__init__(**kwargs)
    def _build(self):
        super()._build()
        controls=ResponsiveBoxLayout(orientation='vertical',height_px=92,gap_px=5)
        row=ResponsiveBoxLayout(height_px=40,gap_px=6)
        self.disc_angle=Slider(min=-180,max=180,value=0,step=.1)
        self.angle_label=Label(text='0°',size_hint_x=.2)
        row.add_widget(self.disc_angle);row.add_widget(self.angle_label);controls.add_widget(row)
        row=ResponsiveBoxLayout(height_px=44,gap_px=6)
        self.apply_disc=PrimaryButton(text=tr('pentacle.apply_disc'))
        self.align_layer=UIButton(text=tr('pentacle.align_layer'))
        self.apply_disc.bind(on_release=lambda *_:self.commit_disc())
        self.align_layer.bind(on_release=lambda *_:self.align_current())
        row.add_widget(self.apply_disc);row.add_widget(self.align_layer);controls.add_widget(row)
        self.panel.add_widget(controls,index=1)
        self._angle_trigger=Clock.create_trigger(self.preview_disc,.08)
        self.disc_angle.bind(value=lambda *_:self._angle_trigger() if not self._angle_updating else None)
    def _refresh(self):
        if self._cube is None:return
        self._angle_trigger.cancel();self._angle_updating=True;self.disc_angle.value=0;self._angle_updating=False
        self.angle_label.text='0°';self.demo_button.disabled=False;self.demo_button.opacity=1
        self.view.cube=self._cube;self.view.refresh()
        self.status.text=tr('poly.progress',done=sum(self._cube._paints[i]>=0 for i in self._cube.paint_slots),total=len(self._cube.paint_slots))
    def retranslate(self):
        super().retranslate()
        if self._cube:
            self.title.text=tr('directory.pentacle');self.hint.text=tr('pentacle.entry_hint')
        self.apply_disc.text=tr('pentacle.apply_disc');self.align_layer.text=tr('pentacle.align_layer')
    def paint(self,index):
        if not self.entry_can_edit() or abs(self.disc_angle.value)>1e-6:return
        if index in self._cube.hidden_panels or self._cube._paints[index]==self._color:return
        self._remember();self._cube.paint(index,self._color);self.view.selected=index;self._refresh()
    def _remember(self):
        # Retain the verified move path as well as colours and geometry. Undo
        # after an edit must not turn a generated scramble into a fresh search.
        self._history.append(self._cube.clone());self._history=self._history[-40:]
        _app().polyhedral_solution=None
    def preview_disc(self,*_):
        if self._cube is None or not self.entry_can_edit():return
        value=self.disc_angle.value;self.angle_label.text=f'{value:+g}°'
        preview=self._cube.clone();preview.apply_move(Move(self._face,0,value))
        self.view.cube=preview;self.view.refresh()
    def commit_disc(self):
        if not self.entry_can_edit():return
        value=self.disc_angle.value
        if abs(value)>1e-6:self._remember();self._cube.apply_move(Move(self._face,0,value))
        self._refresh()
    def align_current(self):
        if not self.entry_can_edit():return
        self.commit_disc()
        try:moves=self._cube.alignment_moves(self._face)
        except ValueError as exc:self.status.text=tr(str(exc));return
        self._remember();self._cube.apply_moves(moves);self._refresh()
    def change_view(self,direction):
        self.commit_disc();super().change_view(direction)
    @validation_action
    def validate(self):
        self.status.text=''
        return True
    def entry_reset_solved(self):
        self._remember();self._cube.colors=PentacleCube().colors
    def clear(self):
        if not self.entry_can_edit():return
        self._remember();self._cube.colors=PentacleCube(paints=[-1]*len(self._cube.panels)).colors;self._refresh()
    def undo(self):
        if not self.entry_can_edit() or not self._history:return
        state=self._history.pop()
        if isinstance(state,tuple) and len(state)==2 and isinstance(state[0],PentacleCube):state=state[0]
        self._cube.colors=state.colors if isinstance(state,PentacleCube) else state
        if isinstance(state,PentacleCube):
            self._cube.history=list(state.clone().history);self._cube._history_snapshot=self._cube.frames
        self._refresh()
    def randomize(self):
        if not self.entry_can_edit():return
        self._remember();job=self.entry_state.begin('scrambling');target=self._cube
        cancel=self._cancel=threading.Event();self.status.text=tr('rigid.shuffling')
        def run():
            work=PentacleCube();error=None;deadline=monotonic()+5
            try:
                # Twelve independent core turns already exercise all six axes and
                # both cut directions; more turns mainly make the inverse longer.
                # non-trivial disc offsets to mix both housing and discs.
                for _ in range(12):
                    if cancel.is_set():return
                    if monotonic()>deadline:break
                    axis=random.randrange(6)
                    try:work.apply_moves(work.alignment_moves(axis))
                    except ValueError:continue
                    work.apply_move(Move(axis,1,random.choice((90,180,270))))
                for axis in range(6):
                    if cancel.is_set():return
                    if monotonic()>deadline:break
                    work.apply_move(Move(axis,0,random.randrange(1,20)*18))
                if work.is_solved():
                    work.apply_moves(work.alignment_moves(0))
                    work.apply_move(Move(0,1,90))
            except Exception as exc:error=str(exc) if isinstance(exc,ValueError) else 'rigid.invalid'
            def done(_):
                if self._job is not job:return
                self._job=None
                if cancel.is_set() or self._cube is not target:return
                if error:self.status.text=tr(error);return
                self._cube.frames=work.frames;self._cube._paints=list(work._paints)
                self._cube.history=list(work.history);self._cube._history_snapshot=work.frames;self._cube._geometry_cache=None
                self._refresh()
            Clock.schedule_once(done,0)
        threading.Thread(target=run,daemon=True).start()
    def solve(self):
        self.commit_disc()
        if any(self._cube._paints[i]<0 for i in self._cube.paint_slots):self.entry_show_error('poly.error.incomplete');return
        super().solve()
    def entry_prepare_twist(self):self.commit_disc()
    def on_leave(self,*_):
        self.commit_disc()
        self._angle_trigger.cancel();super().on_leave()
