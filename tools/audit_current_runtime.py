"""Visible pages in both orientations, without opening a physical camera."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
OUT=Path('reports/reliability-audit/2026-11-02/runtime')
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'preferences.json')
from app.application import CubeApp
from app.ui_self_check import UISelfCheck
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from kivy.clock import Clock


class Audit(CubeApp):
    def on_start(self):
        self.results=[];self.index=0;self.root.transition=NoTransition();self.next_orientation()
    def on_stop(self):pass
    def next_orientation(self,*_):
        if self.index==2:
            (OUT/'summary.json').write_text(json.dumps(self.results,ensure_ascii=False,indent=2),encoding='utf-8')
            self.stop();return
        name,size=(('portrait',(390,844)),('landscape',(800,600)))[self.index];self.index+=1
        Window.size=size
        def done(report):
            self.results.append(dict(orientation=name,**report));Clock.schedule_once(self.next_orientation,.1)
        self.audit=UISelfCheck(self,str(OUT/name),on_done=done,step_delay=.35)
        self.audit._steps=[s for s in self.audit._steps if s[0]!='CameraScreen']
        self.audit._steps.extend([
            ('PolyhedralScreen',lambda:self.new_polyhedral('floppy_133',3)),
            ('CuboidSixViewScreen',lambda:self.new_polyhedral('mirror_camouflage_3',3)),
            ('CopterInputScreen',self.new_copter),('LanlanCometInputScreen',self.new_lanlan_comet),
            ('TwinsInputScreen',self.new_twins),('SunCubeInputScreen',self.new_suncube),
            ('HexagramInputScreen',self.new_hexagram),('FlowerCopterInputScreen',self.new_flower_copter),
            ('ButterflowerInputScreen',self.new_butterflower)])
        self.audit.start()


if __name__=='__main__':
    app=Audit();app.run()
    raise SystemExit(len(app.results)!=2 or any(r['status']!='pass' for r in app.results))
