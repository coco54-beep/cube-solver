"""Resume a legacy Twins state, press Scramble, and undo the geometry update."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_cad_copter_shapes as base
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition
from time import monotonic
from cube.twins_pcubes import TwinsPCubesState
from cube.twins_state import TwinsState
base.OUT=Path('reports/optimization/2026-11-02/twins-petal-scramble/native')
base.OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(base.OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,'mf8_twins') for size in ((800,600),(390,844)))
        Clock.schedule_once(self.next,.05)

    def open(self):
        try:
            from cube.twins_aligned import scrambled
            from app.session import encode,decode
            import json
            self.entry=self.root.current_screen
            legacy=decode(json.loads(json.dumps(encode(scrambled(11,30,jumble=True)))))
            self.cube=self.entry._cube=legacy;self.before=legacy.signature()
            self.entry.view.set_cube(legacy);self.entry._history=[];self.entry._refresh()
            self.entry.randomize();self.deadline=monotonic()+20
            Clock.schedule_once(self.await_scramble,.02)
        except Exception:self.fail()

    def await_scramble(self,*_):
        try:
            if self.entry._job is not None:
                if monotonic()>self.deadline:raise TimeoutError('Twins scramble button')
                Clock.schedule_once(self.await_scramble,.02);return
            assert isinstance(self.cube,TwinsPCubesState) and self.entry._cube is self.cube
            assert self.entry.validate() and not self.cube.is_solved()
            self.settle(self.check)
        except Exception:self.fail()

    def check(self):
        try:
            assert self.entry.view._polygons and self.entry.view.on_pick is None
            self.entry.export_to_png(str(base.OUT/f'twins-new-petals-{self.size[0]}.png'))
            self.entry.undo()
            assert type(self.cube) is TwinsState and self.cube.signature()==self.before
            assert self.entry._cube is self.cube
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,
                                  legacy_scramble_uses_new_geometry=True,undo_preserves_legacy_state=True,
                                  view_fields=192,manual_colour=False,manual_pose=False))
            self.save();Clock.schedule_once(self.next,.05)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
