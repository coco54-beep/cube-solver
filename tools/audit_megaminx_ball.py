"""Native catalogue / pixel entry / turn / solve / playback for VP #59."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.audit_pending_models import Audit as BaseAudit
from tools import audit_lanlan_models as audit


class Audit(BaseAudit):
    def _ready(self,*args):
        self._navigation_checked=False
        self.entry.view._draw()
        super()._ready(*args)
        try:
            e=self.entry
            assert len(e._swatches)==20 and len(e.view.palette)==20
            assert len(e._cube.colors)==140 and len(e._cube.geometry.spec.axes)==12
        except Exception:self.fail()

    def open_turn(self,*args):
        if not self._navigation_checked:
            self._navigation_checked=True
            self._original_face=self.entry._face
            self.entry.change_view(1)
            audit.Clock.schedule_once(self._changed_face,.8)
            return
        super().open_turn(*args)

    def _changed_face(self,*args):
        try:
            assert self.entry._face!=self._original_face
            assert audit.signature(self.entry._cube)==self.input_signature
            self.entry.change_view(-1)
            audit.Clock.schedule_once(self._returned_face,.8)
        except Exception:self.fail()

    def _returned_face(self,*args):
        try:assert self.entry._face==self._original_face
        except Exception:self.fail();return
        self.open_turn()

    def back_to_input(self,*args):
        try:
            assert self.twist.layer.disabled and self.twist.layer.values==['72°']
        except Exception:
            self.fail();return
        super().back_to_input(*args)


if __name__=='__main__':
    audit.KINDS=('megaminx_ball',)
    audit.OUT=Path('reports/expansion/2026-10-27/megaminx-ball/visible')
    audit.OUT.mkdir(parents=True,exist_ok=True)
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
