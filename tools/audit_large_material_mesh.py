"""Native GPU regression for material scenes above the 16-bit vertex limit."""
import os,sys,json,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from renderer.square1_view import Square1View

OUT=Path('reports/expansion/2026-10-29/large-mesh');OUT.mkdir(parents=True,exist_ok=True)
TRIANGLE=(((-.5,-.5,0.),(.5,-.5,0.),(0.,.5,0.)),(0.,0.,1.),0,0,0,0,1)


class View(Square1View):
    fit_piece=True
    test_faces=(TRIANGLE,)*22000
    def _display_surfaces(self,cube):return self.test_faces


class Audit(App):
    def build(self):
        self.view=View();self.view.set_cube(SimpleNamespace());self.rows=[];self.sizes=[(800,600),(390,844)]
        root=FloatLayout();root.add_widget(self.view);Clock.schedule_once(self.next,.1);return root

    def next(self,*_):
        if not self.sizes:self.stop();return
        self.size=self.sizes.pop(0);Window.size=self.size;self.view.test_faces=(TRIANGLE,)*22000
        Clock.schedule_once(self.large,.2)

    def large(self,*_):
        try:
            v=self.view;v._draw();assert not v._gpu_failed
            active=[m for m in v._meshes if m.indices];assert len(active)>=2
            assert all(len(m.vertices)//7<=60000 and max(m.indices)<60000 for m in active)
            assert sum(len(m.indices) for m in active)==22000*3+18
            points,slot=v._polygons[0];x=sum(p[0] for p in points)/3+v.x;y=sum(p[1] for p in points)/3+v.y
            assert v.pick(x,y)==0
            self.batch_count=len(active);Clock.schedule_once(self.shrink,.2)
        except Exception:self.fail()

    def shrink(self,*_):
        try:
            v=self.view;assert any(v._fbo.texture.pixels[3::4])
            v.test_faces=(TRIANGLE,);v._draw()
            assert sum(bool(m.indices) for m in v._meshes)==1
            assert all(not m.indices and not m.vertices for m in v._meshes[1:])
            v.test_faces=();v._draw();assert not any(m.indices for m in v._meshes)
            assert v._polygons==[];Clock.schedule_once(self.empty,.2)
        except Exception:self.fail()

    def empty(self,*_):
        try:
            assert not any(self.view._fbo.texture.pixels[3::4])
            self.rows.append(dict(size=self.size,passed=True,batches=self.batch_count,
                                  triangles=22000,picking=True,shrink_clears_old_batches=True,empty_clears_pixels=True))
            self.save();Clock.schedule_once(self.next,.1)
        except Exception:self.fail()

    def fail(self):
        self.rows.append(dict(size=self.size,passed=False,error=traceback.format_exc()));self.save();self.stop()

    def save(self):(OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=2 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
