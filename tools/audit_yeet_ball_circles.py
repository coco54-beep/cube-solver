"""Native input, spherical picking, turn, undo and solve for the revised cuts."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.audit_yeet_ball import BallAudit,audit
import app.prefs

audit.KINDS=('yeet_ball',)
audit.OUT=Path('reports/optimization/2026-11-04/yeet-ball-circles/native')
audit.OUT.mkdir(parents=True,exist_ok=True)
app.prefs._PREFS_FILE=str(audit.OUT/'audit-preferences.json')


class Audit(BallAudit):
    def on_stop(self):pass


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(row['passed'] for row in app.rows):raise SystemExit(1)
