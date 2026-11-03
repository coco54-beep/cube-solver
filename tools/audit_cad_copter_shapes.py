"""Native play/shape animation audit with isolated preferences and screenshots."""
import os,sys,json,traceback
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
os.environ['KIVY_METRICS_DENSITY']='1';os.environ['KIVY_DPI']='96'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window_state','hidden')
# Headless checks use SDL mouse events; Windows pen hooks can target another
# concurrent test window at shutdown and are unrelated to this model audit.
Config.remove_option('input','wm_pen');Config.remove_option('input','wm_touch')
OUT=Path(__file__).resolve().parents[1]/'reports/optimization/2026-11-02/cad-copter-shapes'
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'audit-preferences.json')
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
from candidate_puzzles import catalogue_family


class Audit(CubeApp):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,kind) for size in ((800,600),(390,844))
                       for kind in ('lanlan_flower_copter','mf8_twins'))
        Clock.schedule_once(self.next,.05)

    def on_stop(self):pass

    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.size,passed=False,error=traceback.format_exc()))
        self.save();self.stop()

    def save(self):
        (OUT/'native-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')

    def next(self,*_):
        try:self.size,self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            self.root.get_screen('HomeScreen').launch_order(catalogue_family(self.kind),self.kind)
            self.settle(self.open)
        except Exception:self.fail()

    def settle(self,callback):
        self.frames_left=6
        def tick(_):
            self.frames_left-=1
            if self.frames_left:Clock.schedule_once(tick,0)
            else:callback()
        Clock.schedule_once(tick,0)

    def open(self):
        try:
            self.entry=self.root.current_screen;self.before=self.cube.signature()
            assert self.entry.play_only and self.cube.is_solved()
            self.entry.open_twist();self.twist=self.root.current_screen
            self.settle(self.corner)
        except Exception:self.fail()

    def corner(self):
        try:
            s=self.twist;s._axis=12;s.axis.text=s.axis.values[12];s._set_layers()
            s.layer.text=s.layer.values[s._angles.index(60.)]
            s._layer_selected(s.layer,s.layer.text)
            assert not s.layer.disabled and s.view.amount_for_axis(12)==60.
            s.turn(1);self.wait_animation(self.edge)
        except Exception:self.fail()

    def wait_animation(self,callback):
        deadline=monotonic()+30
        def tick(_):
            try:
                if self.twist.view._move is None and not self.twist.view.camera_busy:callback();return
                if monotonic()>deadline:raise TimeoutError('native shape animation')
                Clock.schedule_once(tick,.02)
            except Exception:self.fail()
        Clock.schedule_once(tick,.02)

    def edge(self):
        try:
            assert self.cube.signature()!=self.before
            assert any(abs(v)>1.01 for p in self.cube.world_panels() for q in p for v in q)
            # Exercise a second animated cut on an already non-cubic shell.
            self.twist.twist(Move(0,0,JUMBLE));self.wait_animation(self.back)
        except Exception:self.fail()

    def back(self):
        try:
            assert self.twist.view._polygons
            self.twist.export_to_png(str(OUT/f'{self.kind}-twist-{self.size[0]}.png'))
            self.shaped=self.cube.signature();self.twist.back();self.settle(self.check)
        except Exception:self.fail()

    def check(self):
        try:
            s=self.root.current_screen
            assert s is self.entry and self.cube.signature()==self.shaped
            assert s.validate() and s.view.on_pick is None
            assert all(w.parent is None for w in (s.palette,s.palette2,s.navigation,s.shape_button))
            s.export_to_png(str(OUT/f'{self.kind}-play-{self.size[0]}.png'))
            s.assign_initial();assert self.cube.is_solved()
            s.undo();assert self.cube.signature()==self.shaped
            s.undo();assert self.cube.signature()==self.before
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,
                                  shape_animation=True,second_cut_animation=True,
                                  manual_colour=False,manual_pose=False,reset_and_undo=True))
            self.save();Clock.schedule_once(self.next,.02)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=4 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
