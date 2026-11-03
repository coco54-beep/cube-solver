"""Exercise visible source pages in both orientations; skip physical camera use."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from app.ui_self_check import UISelfCheck
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from kivy.clock import Clock


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();self.results=[];self.index=0;self.next_orientation()

    def next_orientation(self):
        if self.index==2:
            out=Path('reports/reliability-audit/2026-10-25/visible-pages')
            (out/'summary.json').write_text(json.dumps(self.results,ensure_ascii=False,indent=2),encoding='utf-8')
            self.stop();return
        name,size=(('portrait',(390,844)),('landscape',(800,600)))[self.index];self.index+=1
        Window.size=size
        out=Path('reports/reliability-audit/2026-10-25/visible-pages')/name
        def done(report):
            self.results.append(dict(orientation=name,**report));Clock.schedule_once(lambda _:self.next_orientation(),.1)
        self.audit=UISelfCheck(self,str(out),on_done=done,step_delay=.2)
        self.audit._steps=[s for s in self.audit._steps if s[0]!='CameraScreen']
        self.audit.start()


if __name__=='__main__':
    app=Audit();app.run()
    assert len(app.results)==2 and all(r['status']=='pass' for r in app.results),app.results
    print(json.dumps([(r['orientation'],r['checked'],r['errors']) for r in app.results]),flush=True)
