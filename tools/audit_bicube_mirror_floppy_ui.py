"""Real directory routes, paint/undo, face animation and mobile previews."""
import os,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.config import Config
Config.set('graphics','window','hidden')
OUT=Path('reports/optimization/2026-11-02/bicube-mirror-floppy')
OUT.mkdir(parents=True,exist_ok=True)
import app.prefs
app.prefs._PREFS_FILE=str(OUT/'audit-preferences.json')
from app.application import CubeApp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from cube.cuboid import CuboidCube
from cube.polyhedral_scramble import scramble


class Audit(CubeApp):
    def on_start(self):
        self.rows=[];self.root.transition=NoTransition()
        self.jobs=iter((size,kind) for size in ((800,600),(390,844))
                       for kind in ('bicube','floppy_133','mirror_camouflage_3'))
        Clock.schedule_once(self.next,.1)
    def on_stop(self):pass
    def save(self):
        (OUT/'ui-results.json').write_text(json.dumps(self.rows,indent=2),encoding='utf-8')
    def fail(self):
        self.rows.append(dict(kind=self.kind,size=self.size,passed=False,error=traceback.format_exc()))
        self.save();self.stop()
    def next(self,*_):
        try:self.size,self.kind=next(self.jobs)
        except StopIteration:self.stop();return
        try:
            self.root.current='HomeScreen';Window.size=self.size
            family='bandaged_family' if self.kind=='bicube' else 'cuboid_family' if self.kind=='floppy_133' else 'mirror'
            self.root.get_screen('HomeScreen').launch_order(family,self.kind)
            expected='InputScreen' if self.kind=='bicube' else 'PolyhedralScreen' if self.kind=='floppy_133' else 'CuboidSixViewScreen'
            assert self.root.current==expected
            assert self.cube.puzzle_kind==self.kind
            Clock.schedule_once(self.check,.4)
        except Exception:self.fail()
    def check(self,*_):
        try:
            s=self.root.current_screen
            if self.kind=='floppy_133':
                source=CuboidCube.solved(self.kind);scramble(source,100,37)
                for index in source.panels():s.choose_color(source.colors[index]);s.paint(index)
                assert s._cube.colors==source.colors
                before=list(s._cube.colors);s.choose_color(2);s.paint(0);s.undo()
                assert s._cube.colors==before
                self.face=s._face;s.change_view(1)
            elif self.kind=='mirror_camouflage_3':
                assert len(s._swatches)==1
                before=s._draft.state();s.select_color(0);s.select_region((0,1));s.undo()
                assert s._draft.state()==before
                s.change_face(1);assert s._six_face==1
            Clock.schedule_once(self.capture,.7)
        except Exception:self.fail()
    def capture(self,*_):
        try:
            s=self.root.current_screen
            if self.kind=='floppy_133':assert s._face!=self.face and not s._view_busy
            s.export_to_png(str(OUT/f'entry-{self.kind}-{self.size[0]}.png'))
            self.rows.append(dict(kind=self.kind,size=self.size,passed=True,screen=self.root.current,
                                  controls=('paint, undo, face animation' if self.kind=='floppy_133' else
                                            'silver region, undo, face switch' if self.kind=='mirror_camouflage_3' else 'directory route')))
            self.save()
            if self.kind=='mirror_camouflage_3':
                cube=CuboidCube.solved(self.kind);scramble(cube,30,37)
                s._load_cube(cube);s.open_twist();Clock.schedule_once(self.capture_model,.4)
            else:Clock.schedule_once(self.next,.05)
        except Exception:self.fail()
    def capture_model(self,*_):
        try:
            assert self.root.current=='PolyhedralTwistScreen'
            self.root.current_screen.export_to_png(str(OUT/f'mirror-model-{self.size[0]}.png'))
            Clock.schedule_once(self.next,.05)
        except Exception:self.fail()


if __name__=='__main__':
    app=Audit();app.run()
    if len(app.rows)!=6 or not all(row['passed'] for row in app.rows):raise SystemExit(1)
