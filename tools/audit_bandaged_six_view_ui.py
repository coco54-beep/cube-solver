"""Manually fill 12 real app cases, match, turn legally, return and undo."""
import sys
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_cad_copter_shapes as base
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from cube.bandaged_cube import BandagedCube,KINDS
from cube.bandaged_entry import plates
from cube.bandaged_observation import COLOR_CODES,state_key
from cube.conversion import cubies_to_facelets
from cube.cuboid import FACES
base.OUT=Path('reports/optimization/2026-11-03/bandaged-six-view/native')
base.OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(base.OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=False
        self.jobs=iter((size,kind) for size in ((800,600),(390,844)) for kind in KINDS)
        Clock.schedule_once(self.next,.05)

    def next(self,*_):
        try:self.size,self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            self.root.get_screen('HomeScreen').launch_order('bandaged_family',self.kind)
            self.settle(self.fill)
        except Exception:self.fail()

    def fill(self):
        try:
            self.entry=self.root.current_screen
            assert self.entry.name=='BandagedSixViewScreen'
            self.truth=BandagedCube.random_scramble(self.kind,100,23)
            values=cubies_to_facelets(self.truth.cubies,self.truth.n)
            self.seams={(p.face,p.cells) for p in plates(self.truth)}
            for p in plates(self.truth):
                f=FACES.index(p.face);r,c=p.cells[0]
                self.entry.change_face(f);self.entry.select_color(COLOR_CODES.index(values[p.face][r][c]))
                indices=tuple(rr*self.truth.n+cc for rr,cc in p.cells)
                self.entry.select_region(self.entry._draft.rectangle(f,indices[0],indices[-1]))
            self.entry.change_face(2);self.entry.apply();self.deadline=monotonic()+12
            Clock.schedule_once(self.matched,.02)
        except Exception:self.fail()

    def matched(self,*_):
        try:
            if self.entry._job is not None:
                if monotonic()>self.deadline:raise TimeoutError('Matching native input')
                Clock.schedule_once(self.matched,.02);return
            assert self.entry._ready(),self.entry.status.text
            assert self.cube.history==[]
            assert self.entry.collect_facelets()==cubies_to_facelets(self.truth.cubies,self.truth.n)
            assert {(p.face,p.cells) for p in plates(self.cube)}==self.seams
            self.settle(self.open_twist)
        except Exception:self.fail()

    def open_twist(self):
        try:
            self.entry.export_to_png(str(base.OUT/f'{self.kind}-{self.size[0]}.png'))
            self.before=state_key(self.cube)
            self.entry.open_twist();self.twist=self.root.current_screen
            self.settle(self.turn)
        except Exception:self.fail()

    def turn(self):
        try:
            assert self.twist.name=='TwistScreen' and isinstance(self.twist._work,BandagedCube)
            limit=max(p[0] for p in self.cube.cubies)
            axis,layers=next((a,ls) for a in range(3)
                            for ls in ((limit,),(-limit,),tuple(range(1,limit+1,2)))
                            if self.twist._work.can_turn(a,ls))
            self.twist._twist(SimpleNamespace(axis=axis,layer_positions=layers,sign=1))
            self.deadline=monotonic()+12;Clock.schedule_once(self.turned,.02)
        except Exception:self.fail()

    def turned(self,*_):
        try:
            if self.twist._busy:
                if monotonic()>self.deadline:raise TimeoutError('Native turn')
                Clock.schedule_once(self.turned,.02);return
            self.changed=state_key(self.twist._work)
            assert self.changed!=self.before
            self.twist.go_back();self.settle(self.check)
        except Exception:self.fail()

    def check(self):
        try:
            assert self.root.current=='BandagedSixViewScreen'
            assert state_key(self.cube)==self.changed and self.entry._ready()
            self.entry.undo()
            assert state_key(self.cube)==self.before and self.entry._ready()
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,manual_scramble_steps=100,
                no_scramble_history=True,matching=True,legal_turn=True,return_and_undo=True))
            self.save();Clock.schedule_once(self.next,.05)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=12 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
