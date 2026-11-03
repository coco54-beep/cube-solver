"""Actual reference Twins directory, two animated turns, reset and undo."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tools.audit_cad_copter_shapes as base
from kivy.clock import Clock
from kivy.uix.screenmanager import NoTransition
base.OUT=Path('reports/optimization/2026-11-02/twins-scramble-coverage/native')
base.OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(base.OUT/'audit-preferences.json')


class Audit(base.Audit):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition();self.simple_input=True
        self.jobs=iter((size,'mf8_twins') for size in ((800,600),(390,844)))
        Clock.schedule_once(self.next,.05)


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
