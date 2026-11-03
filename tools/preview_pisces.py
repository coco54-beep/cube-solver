"""Export the production Pisces renderer for photo comparison."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from cube.pisces import PiscesCube,ANGLE1
from cube.polyhedral import Move
from renderer.pisces_view import PiscesView

if '--hexagram' in sys.argv:
    from cube.hexagram import HexagramCube as PiscesCube
    from renderer.pisces_view import HexagramView as PiscesView
elif '--clover-pyraminx' in sys.argv:
    from cube.clover_pyraminx import CloverPyraminxCube as PiscesCube
    from renderer.pisces_view import CloverPyraminxView as PiscesView
elif '--flower' in sys.argv:
    from cube.flower_copter import FlowerCopterCube as PiscesCube
    from renderer.flower_copter_view import FlowerCopterView as PiscesView

OUT=Path('reports/expansion/2026-10-28/pisces');OUT.mkdir(parents=True,exist_ok=True)
if '--hexagram' in sys.argv:
    OUT=Path('reports/expansion/2026-10-28/hexagram');OUT.mkdir(parents=True,exist_ok=True)
elif '--clover-pyraminx' in sys.argv:
    OUT=Path('reports/expansion/2026-10-29/clover-pyraminx');OUT.mkdir(parents=True,exist_ok=True)
elif '--flower' in sys.argv:
    OUT=Path('reports/expansion/2026-10-29/flower-copter');OUT.mkdir(parents=True,exist_ok=True)


class Preview(App):
    def build(self):
        Window.size=(600,600);self.view=PiscesView();self.jobs=['solved','grey','turned']
        if '--angles' in sys.argv:self.jobs=[f'angle-{yaw}-{pitch}' for yaw,pitch in ((0,0),(45,0),(90,0),(0,35),(45,35),(135,35))]
        root=FloatLayout();root.add_widget(self.view);Clock.schedule_once(self.next,.2);return root

    def next(self,*_):
        if not self.jobs:self.stop();return
        self.case=self.jobs.pop(0);cube=PiscesCube()
        if self.case=='grey':cube.paints=(-1,)*len(cube.panels)
        if self.case=='turned':cube.apply_move(Move(0,0,180. if '--flower' in sys.argv else ANGLE1))
        self.view.set_cube(cube)
        if self.case.startswith('angle-'):
            _,yaw,pitch=self.case.split('-');self.view.yaw=float(yaw);self.view.pitch=float(pitch)
        for label in self.view._face_labels:label.text=''
        Clock.schedule_once(self.save,.2)

    def save(self,*_):
        self.view._draw();self.view.export_to_png(str(OUT/(self.case+'.png')))
        Clock.schedule_once(self.next,.1)


if __name__=='__main__':Preview().run()
