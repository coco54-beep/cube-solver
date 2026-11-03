"""Normal startup and pause/resume with an isolated session and preferences."""
import os,sys,json,time
from pathlib import Path
START=time.monotonic()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
OUT=ROOT/'reports/reliability-audit/2026-11-02/startup'
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'preferences.json')
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window


class Audit(CubeApp):
    @property
    def user_data_dir(self):return str(OUT/'session')
    def on_start(self):
        super().on_start()
        self.results={'normal_startup':True,'startup_seconds':round(time.monotonic()-START,3)}
        self.frames=0;self.gaps=[];self.last=time.monotonic()
        Clock.schedule_interval(self.tick,0)
    def tick(self,dt):
        now=time.monotonic();self.gaps.append(now-self.last);self.last=now;self.frames+=1
        if self.frames==12:
            assert self.root.current=='HomeScreen'
            self.root.export_to_png(str(OUT/'home.png'))
            self.results['pause_accepted']=self.on_pause()
            self.on_resume()
        if self.frames==32:
            assert self.root.current=='HomeScreen'
            self.results.update(resume_preserved_page=True,frames=self.frames,
                                maximum_observed_frame_gap=round(max(self.gaps),3),window_size=list(Window.size))
            (OUT/'result.json').write_text(json.dumps(self.results,indent=2),encoding='utf-8')
            self.stop();return False


if __name__=='__main__':Audit().run()
