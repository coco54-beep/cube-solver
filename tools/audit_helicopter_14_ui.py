"""Real fourteen-face entry, overlapping-cut animation, reset and undo."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_edge_jumbling_ui as base
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition
from cube.polyhedral import Move
from time import monotonic
base.base.OUT=Path('reports/optimization/2026-11-02/helicopter-14/native')
base.base.OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(base.base.OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,'helicopter_14') for size in ((800,600),(390,844)))
        Clock.schedule_once(self.next,.05)

    def edge(self):
        try:
            assert self.cube.signature()!=self.before
            # Axes 3 and 4 overlap the prepared cap. A disjoint free layer
            # would not demonstrate the newly implemented jumbling gate.
            self.twist.twist(Move(3,0,180.));self.wait_animation(self.back)
        except Exception:self.fail()

    def check(self):
        try:
            s=self.root.current_screen
            assert s is self.entry and self.cube.signature()==self.shaped
            assert s.validate() and s.view.on_pick is None
            assert all(w.parent is None for w in (s.palette,s.palette2,s.navigation,s.shape_button))
            s.export_to_png(str(base.base.OUT/f'{self.kind}-play-{self.size[0]}.png'))
            s.assign_initial();assert self.cube.is_solved()
            s.undo();assert self.cube.signature()==self.shaped
            s.undo();assert self.cube.signature()==self.before
            s.randomize();self.deadline=monotonic()+20
            Clock.schedule_once(self.scrambled,.02)
        except Exception:self.fail()

    def scrambled(self,*_):
        try:
            s=self.entry
            if s._job is not None:
                if monotonic()>self.deadline:raise TimeoutError('native scramble button')
                Clock.schedule_once(self.scrambled,.02);return
            assert self.cube.signature()!=self.before and s.validate()
            assert not self.cube.is_solved() and self.cube.color_count==7
            self.settle(self.finish_scramble)
        except Exception:self.fail()

    def finish_scramble(self):
        try:
            self.entry.export_to_png(str(base.base.OUT/f'{self.kind}-scramble-{self.size[0]}.png'))
            self.entry.undo();assert self.cube.signature()==self.before
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,
                                  shape_animation=True,overlapping_cut=True,scramble_button=True,
                                  gold_validation=True,reset_and_undo=True,manual_colour=False,manual_pose=False))
            self.save();Clock.schedule_once(self.next,.02)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
