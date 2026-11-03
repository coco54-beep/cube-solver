"""Actual directory, shape animation, reset and undo in both orientations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_cad_copter_shapes as base
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition
from cube.polyhedral import Move
from cube.curvy_copter import JUMBLE
base.OUT=Path('reports/optimization/2026-11-02/edge-jumbling')
base.OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(base.OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,kind) for size in ((800,600),(390,844))
                       for kind in ('helicopter','rua','clover','mf8_bauhinia_minx'))
        Clock.schedule_once(self.next,.05)

    def corner(self):
        try:
            s=self.twist;s._axis=0;s.axis.text=s.axis.values[0];s._set_layers()
            from cube.spherical_jumbling import BAU_JUMBLE
            s.twist(Move(0,0,BAU_JUMBLE if self.kind=='mf8_bauhinia_minx' else JUMBLE))
            self.wait_animation(self.edge)
        except Exception:self.fail()

    def edge(self):
        try:
            assert self.cube.signature()!=self.before
            axis=next(a for a in range(1,len(self.cube.turn_axes)) if self.cube.can_apply(Move(a,0,self.cube.turn_steps[a])))
            self.twist.twist(Move(axis,0,self.cube.turn_steps[axis]));self.wait_animation(self.back)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=8 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
