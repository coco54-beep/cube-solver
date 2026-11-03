"""Native entry/turn/solve/playback checks for newly connected pending models."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import audit_lanlan_models as audit


class Audit(audit.Audit):
    def input(self,*args):
        audit.Clock.schedule_once(self._ready,.12)

    def _ready(self,*args):
        self._aj_shallow_checked=False
        super().input(*args)
        try:
            e=self.entry;v=e.view;original=list(e._cube.colors)
            a,b=next(p for p in e._cube.geometry.pieces if len(p)==2)
            e._cube.colors[a],e._cube.colors[b]=e._cube.colors[b],e._cube.colors[a]
            bad=list(e._cube.colors)
            assert not e.validate() and self.root.current==e.name
            assert e._entry_notice['category']=='illegal' and e._cube.colors==bad
            e._cube.colors=list(original);assert e.validate()
            v._draw();candidates={}
            for triangle,index in v._polygons:
                if index is None:continue
                a,b,c=triangle;area=abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))
                if area>candidates.get(index,(0,None))[0]:
                    candidates[index]=(area,(v.x+(a[0]+b[0]+c[0])/3,v.y+(a[1]+b[1]+c[1])/3))
            for index,(_,xy) in sorted(candidates.items(),key=lambda row:row[1][0],reverse=True):
                if v.pick(*xy)!=index:continue
                e.choose_color((original[index]+1)%12)
                touch=SimpleNamespace(pos=xy,grab=lambda _:None,ungrab=lambda _:None)
                assert v.on_touch_down(touch) and v.on_touch_up(touch)
                assert [i for i,(a,b) in enumerate(zip(original,e._cube.colors)) if a!=b]==[index]
                e.undo();assert e._cube.colors==original
                break
            else:raise ValueError('No visible panel could be selected from screen pixels')
        except Exception:self.fail()

    def back_to_input(self,*args):
        if self.kind=='aj_curvy_dinominx_4' and not self._aj_shallow_checked:
            try:
                from demo.expanded_support import signature
                assert signature(self.twist._cube)==self.input_signature
                assert len(self.twist.layer.values)==2 and not self.twist.layer.disabled
                self.twist.layer.text=self.twist.layer.values[1]
                assert self.twist._layer==1
                self._aj_shallow_checked=True
                self.twist.turn(1)
                audit.Clock.schedule_once(self.undo_turn,.8)
            except Exception:self.fail()
            return
        super().back_to_input(*args)


if __name__=='__main__':
    audit.KINDS=('mf8_bauhinia_minx','aj_curvy_dinominx_4')
    audit.OUT=Path('reports/expansion/2026-10-27/pending-completion/visible')
    audit.OUT.mkdir(parents=True,exist_ok=True)
    app=Audit();app.run()
    if len(app.rows)!=2*len(audit.KINDS) or not all(r['passed'] for r in app.rows):raise SystemExit(1)
