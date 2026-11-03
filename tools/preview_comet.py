"""Export the actual model for comparison before catalogue integration."""
import sys,os
os.environ['KIVY_NO_ARGS']='1'
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from renderer.comet_view import CometView
from cube.crazy_comet import CometCube

PHYSICAL='--physical' in sys.argv
if PHYSICAL:
    from cube.lanlan_comet import LanlanCometCube as CometCube
    from renderer.comet_view import LanlanCometView as CometView


class Preview(App):
    def build(self):
        Window.size=(640,640);root=FloatLayout();self.view=CometView()
        root.add_widget(self.view);self.view.set_cube(CometCube());return root
    def on_start(self):Clock.schedule_once(self.save,.5)
    def save(self,*args):
        target=Path('reports/expansion/2026-10-28/lanlan-comet' if PHYSICAL else 'reports/expansion/2026-10-27/crazy-comet');target.mkdir(parents=True,exist_ok=True)
        self.view._draw();self.view.export_to_png(str(target/'preview.png'));self.stop()


if __name__=='__main__':Preview().run()
