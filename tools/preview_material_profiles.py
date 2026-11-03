"""Render material profiles through their actual Kivy production views."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from cube.twins_state import TwinsState
from cube.suncube import SunCube
from renderer.twins_view import TwinsView,SunCubeView

OUT=Path('reports/expansion/2026-10-28/material-previews');OUT.mkdir(parents=True,exist_ok=True)


class Preview(App):
    def build(self):
        Window.size=(500,500);self.panel=FloatLayout()
        self.jobs=[(factory,view,painted) for factory,view in ((TwinsState,TwinsView),(SunCube,SunCubeView)) for painted in (False,True)]
        Clock.schedule_once(self.next,.3);return self.panel

    def next(self,*_):
        if not self.jobs:self.stop();return
        factory,view,self.painted=self.jobs.pop(0);self.cube=factory()
        if not self.painted:self.cube.paints=(-1,)*len(self.cube.panels)
        self.panel.clear_widgets();self.view=view();self.panel.add_widget(self.view);self.view.set_cube(self.cube)
        for label in self.view._face_labels:label.text=''
        Clock.schedule_once(self.capture,.3)

    def capture(self,*_):
        self.view._draw();self.view.export_to_png(str(OUT/(self.cube.puzzle_kind+('-painted' if self.painted else '-grey')+'.png')))
        Clock.schedule_once(self.next,.1)


if __name__=='__main__':Preview().run()
