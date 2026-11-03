"""Actual delayed startup restore for old bandage input and current drafts."""
import sys,json,tempfile
from pathlib import Path
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_cad_copter_shapes as base
from kivy.clock import Clock
from app.session import SessionStore,encode
from cube.bandaged_cube import BandagedCube
from cube.bandaged_entry import plates
from cube.bandaged_observation import BandagedSixViewDraft
from cube.conversion import cubies_to_facelets
OUT=Path('reports/optimization/2026-11-03/bandaged-six-view/restores')
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.jobs=iter(('legacy','partial','twist'))
        self.store_dir=tempfile.TemporaryDirectory(prefix='bandaged-session-')
        self._user_data_dir=self.store_dir.name
        Clock.schedule_once(self.next,.1)

    def save(self):
        (OUT/'native-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')

    def next(self,*_):
        try:self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';self.new_cube_variant('bicube',3)
            source=BandagedCube.random_scramble('bicube',30,7)
            self.expected=cubies_to_facelets(source.cubies,3)
            if self.kind=='legacy':
                page='InputScreen';fields=dict(_data=self.expected,_bandage_connections={(p.face,p.cells) for p in plates(source)})
            elif self.kind=='partial':
                page='BandagedSixViewScreen';draft=BandagedSixViewDraft('bicube');draft.paint(2,(0,1),3)
                self.expected_draft=draft.state()
                fields=dict(_cube=self.cube,_six_state=draft.state(),_six_face=2,_six_cube_key=None,_six_applied=None)
            else:page='TwistScreen';fields=dict(_work=source,_history=[],_future=[])
            state=dict(version=1,page=page,app=dict(n=3,puzzle_kind='bicube',cube=self.cube),screens={page:fields},color_info={})
            self._session_store=SessionStore(self)
            self._session_store.path.write_text(json.dumps(encode(state)),encoding='utf-8')
            self._session_store.restore();self.deadline=monotonic()+15
            Clock.schedule_once(self.check,.2)
        except Exception:self.fail()

    def check(self,*_):
        try:
            if self._session_store.restoring:
                if monotonic()>self.deadline:raise TimeoutError('Delayed bandage restore')
                Clock.schedule_once(self.check,.2);return
            assert self._session_store.recovery_reason is None
            entry=self.root.get_screen('BandagedSixViewScreen')
            if self.kind=='twist':
                twist=self.root.current_screen
                assert twist.name=='TwistScreen' and isinstance(twist._work,BandagedCube)
                assert cubies_to_facelets(twist._work.cubies,3)==self.expected
                twist.go_back();assert self.root.current==entry.name
            else:assert self.root.current==entry.name
            if self.kind=='partial':assert entry._draft.state()==self.expected_draft
            else:assert entry.collect_facelets()==self.expected
            self.rows.append(dict(case=self.kind,passed=True));self.save()
            self._session_store.close();Clock.schedule_once(self.next,.3)
        except Exception:self.fail()

    def on_stop(self):
        if hasattr(self,'_session_store'):self._session_store.close()
        if hasattr(self,'store_dir'):self.store_dir.cleanup()


if __name__=='__main__':
    base.OUT=OUT
    app=Audit();app.run()
    if len(app.rows)!=3 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
