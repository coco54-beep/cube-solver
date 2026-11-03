"""Current public catalogue routes and reversible controls, isolated preferences."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
OUT=Path('reports/reliability-audit/2026-11-02/catalogue')
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'preferences.json')
import tools.audit_entry_buttons as buttons
from tools.audit_catalogue_inputs import CatalogueAudit
from candidate_puzzles import PENDING_KINDS


class Audit(CatalogueAudit):
    def on_start(self):
        super().on_start()
        self.routes=[r for r in self.routes if r[1] not in PENDING_KINDS]
        self.cases=self.routes
        (OUT/'routes.json').write_text(json.dumps(self.routes,ensure_ascii=False,indent=2),encoding='utf-8')
    def on_stop(self):pass


if __name__=='__main__':
    buttons.OUT=OUT
    app=Audit();app.run()
    rows=app.rows
    summary={'checked':len(rows),'expected':len(app.routes),'passed':sum(bool(r.get('ok')) for r in rows),
             'failures':[r for r in rows if not r.get('ok')], 'pending_entries_tested':False,
             'scope':'actual directory navigation, reset/undo, clear/cancel/undo; play-only pages exclude manual input'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(bool(summary['failures']) or summary['checked']!=summary['expected'])
