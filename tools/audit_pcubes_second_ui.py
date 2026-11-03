"""Render the real entry screens, face animation, paint and undo controls."""
import os,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from kivy.config import Config
Config.set('graphics','window','hidden')
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition

OUT=Path('reports/optimization/2026-11-01/pcubes-second/ui')
KINDS=('masterball','master_brilic','master_pentultimate','rediminx','starminx_i',
       'pyraminx_crystal','container','square1','square0','square2','super_square1')


class Audit(CubeApp):
    def on_start(self):
        OUT.mkdir(parents=True,exist_ok=True);self.rows=[]
        self.root.transition=NoTransition()
        self.jobs=iter((size,kind) for size in ((800,600),(390,844)) for kind in KINDS)
        Clock.schedule_once(self.next,.1)
    def on_stop(self):pass
    def save(self):(OUT/'results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
    def next(self,*_):
        try:self.size,self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            if self.kind=='container':self.new_container();screen='ContainerScreen'
            elif self.kind=='square1':self.new_square1();screen='Square1Screen'
            elif self.kind.startswith('square') or self.kind=='super_square1':
                self.new_square_family(self.kind);screen='SquareFamilyScreen'
            else:self.new_polyhedral(self.kind,4 if self.kind=='masterball' else 3);screen='PolyhedralScreen'
            self.root.current=screen;Clock.schedule_once(self.check,.35)
        except Exception:self.fail()
    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.size,passed=False,error=traceback.format_exc()))
        self.save();self.stop()
    def check(self,*_):
        try:
            s=self.root.current_screen
            if self.root.current=='PolyhedralScreen':
                before=list(s._cube.colors);s.choose_color(2);s.paint(0);s.paint(1)
                assert s._cube.colors[:2]==[2,2]
                s.undo();s.undo();assert s._cube.colors==before
                self.face=s._face;s.change_view(1)
            Clock.schedule_once(self.capture,.7)
        except Exception:self.fail()
    def capture(self,*_):
        try:
            s=self.root.current_screen
            if self.root.current=='PolyhedralScreen':
                assert s._face!=self.face and not s._view_busy
                assert s.view._polygons
            s.export_to_png(str(OUT/f'{self.kind}-{self.size[0]}.png'))
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,
                                  screen=self.root.current))
            self.save();Clock.schedule_once(self.next,.05)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=22 or not all(r['passed'] for r in app.rows):raise SystemExit(1)
