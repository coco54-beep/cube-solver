"""Reproduce the reported cache crash through real screen transitions, in isolation."""
import os,sys,json,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['KIVY_NO_ARGS']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from app.application import CubeApp
from app.session import SessionStore
from app.constants import FACES
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from app.i18n import tr

OUT=Path('reports/cache-crash/2026-10-25');OUT.mkdir(parents=True,exist_ok=True)
def data(n,color=''):
    result={f:[['']*n for _ in range(n)] for f in FACES};result['F'][0][0]=color;return result


class Audit(CubeApp):
    def on_start(self):
        self.root.transition=NoTransition();Window.size=(480,850);self.rows=[]
        self.source=Path.home()/'AppData/Roaming/cube/last-session.json'
        self.original=self.source.read_bytes() if self.source.exists() else None
        self.temp=tempfile.TemporaryDirectory(prefix='cube-cache-repro-')
        if self.original:
            self.store=SessionStore(self);self.store.path=Path(self.temp.name)/'last-session.json'
            self.store.path.write_bytes(self.original);self.store.restore()
        else:self.store=None
        Clock.schedule_once(self.reproduce,.2)

    def reproduce(self,_=0):
        if self.store and self.store.restoring:Clock.schedule_once(self.reproduce,.1);return
        self.root.current='HomeScreen';self.new_cube(5)
        self.facelets_input=data(2,'G');self.facelets_input_key=None
        self.root.current='InputScreen';Clock.schedule_once(self.check_five,.2)

    def check_five(self,_):
        screen=self.root.current_screen
        assert self.root.current=='InputScreen' and screen._n_for_screen==5
        assert screen._facelets_fit_n(screen.collect_facelets(),5)
        assert screen.title.text==tr('input.title',n=5)
        # Fence two rendered frames before capturing text textures and layouts.
        Clock.schedule_once(lambda _:Clock.schedule_once(self.capture_five,0),0)

    def capture_five(self,_):
        screen=self.root.current_screen
        screen.export_to_png(str(OUT/'five-order-restored.png'))
        self.rows.append(dict(case='legacy two-order global input while entering five',passed=True))
        self.root.current='HomeScreen';self.new_cube(3);self.root.current='InputScreen'
        Clock.schedule_once(self.fill_three,.15)

    def fill_three(self,_):
        screen=self.root.current_screen;screen.set_facelets(data(3,'G'))
        self.root.current='HomeScreen';self.new_cube(4)
        self.facelets_input=data(2,'Y');self.facelets_input_key=2;self.facelets_cache[4]=data(4,'R')
        self.root.current='InputScreen';Clock.schedule_once(self.check_four,.15)

    def check_four(self,_):
        screen=self.root.current_screen;assert screen.collect_facelets()==data(4,'R')
        self.rows.append(dict(case='four-order own cache wins over two-order recent input',passed=True))
        # The model can change before the old page receives on_pre_leave.
        self.n=3;self.root.current='HomeScreen';self.new_cube(3);self.root.current='InputScreen'
        Clock.schedule_once(self.check_three,.15)

    def check_three(self,_):
        screen=self.root.current_screen
        assert screen.collect_facelets()==data(3,'G') and self.facelets_cache[4]==data(4,'R')
        assert screen.set_facelets(data(2,'B'),remember=True) is False
        assert screen.collect_facelets()==data(3,'G')
        Clock.schedule_once(lambda _:Clock.schedule_once(self.capture_three,0),0)

    def capture_three(self,_):
        screen=self.root.current_screen
        screen.export_to_png(str(OUT/'three-order-input-kept.png'))
        self.rows.append(dict(case='switch-back and invalid external input preserve both drafts',passed=True))
        self.root.current='HomeScreen';self.new_cube_variant('penrose_3',3)
        self.facelets_input=data(3,'O');self.facelets_input_key=3;self.facelets_cache['penrose_3']=data(3,'G')
        self.root.current='InputScreen';Clock.schedule_once(self.finish,.15)

    def finish(self,_):
        assert self.root.current_screen.collect_facelets()==data(3,'G')
        self.rows.append(dict(case='same-size different model uses own input',passed=True))
        unchanged=self.original is None or self.source.read_bytes()==self.original
        assert unchanged
        report=dict(cases=self.rows,original_user_checkpoint_unchanged=unchanged,
                    original_sha256=hashlib.sha256(self.original).hexdigest() if self.original else None)
        (OUT/'visible-reproduction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        self.temp.cleanup();self.stop();print(json.dumps(report),flush=True)


if __name__=='__main__':Audit().run()
