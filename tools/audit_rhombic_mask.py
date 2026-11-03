"""Photo-corrected four-layer Mask: both native viewport sizes."""
from pathlib import Path
from tools import audit_lanlan_models as audit


class Audit(audit.Audit):
    def input(self,*args):
        # Reopening the same model intentionally retains input. Start each
        # independent viewport case with a blank draft instead of treating
        # that persistence as an entry validation failure.
        self.entry._blank(None)
        self.entry._refresh()
        super().input(*args)


if __name__=='__main__':
    audit.KINDS=('rhombic_mask_4',)
    audit.OUT=Path('reports/expansion/2026-10-28/rhombic-mask-correction/visible')
    audit.OUT.mkdir(parents=True,exist_ok=True)
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
