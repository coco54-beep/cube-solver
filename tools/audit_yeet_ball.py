"""Run the real entry/turn/undo/solve/playback checks for the spherical Ivy."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import audit_lanlan_models as audit


class BallAudit(audit.Audit):
    def input(self,*args):
        # Building the first curved mesh can consume the first frame. Wait
        # across a frame boundary so its initial screenshot uses final layout.
        audit.Clock.schedule_once(self._input_ready,.12)

    def _input_ready(self,*args):
        try:
            e=self.entry;v=e.view;v._draw()
            candidates={}
            for triangle,index in v._polygons:
                if index is None:continue
                a,b,c=triangle
                area=abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))
                old=candidates.get(index)
                if old is None or area>old[0]:
                    candidates[index]=(area,(v.x+(a[0]+b[0]+c[0])/3,
                                             v.y+(a[1]+b[1]+c[1])/3))
            picked=[]
            e.choose_color(2)
            for index,(_,xy) in sorted(candidates.items(),key=lambda row:row[1][0],reverse=True):
                hit=v.pick_surface(*xy)
                if hit is None or hit[0]!=index:continue
                assert abs(sum(p*p for p in hit[1])-3)<.04
                touch=SimpleNamespace(pos=xy,grab=lambda _:None,ungrab=lambda _:None)
                assert v.on_touch_down(touch) and v.on_touch_up(touch)
                assert e._cube.colors[index]==2
                picked.append(index)
                if len(picked)==2:break
            assert len(picked)==2 and len(set(picked))==2
            e.undo();e.undo()
            assert all(c==-1 for c in e._cube.colors)
        except Exception:
            self.fail();return
        super().input(*args)


if __name__=='__main__':
    audit.KINDS=('yeet_ball',)
    audit.OUT=Path('reports/expansion/2026-10-26/flower-batch/visible')
    audit.OUT.mkdir(parents=True,exist_ok=True)
    app=BallAudit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
