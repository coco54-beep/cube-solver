"""Export both Dogic paint schemes with one camera and equal physical cuts."""
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
from renderer.polyhedral_view import PolyhedralView
from cube.polyhedral import PolyhedralPuzzle

OUT=Path(os.environ.get('DOGIC_PREVIEW_OUT','reports/expansion/2026-10-27/dogic-colourways/comparison'))
OUT.mkdir(parents=True,exist_ok=True)


class Preview(App):
    def build(self):
        Window.size=(500,500);self.root=FloatLayout()
        self.view=PolyhedralView();self.root.add_widget(self.view)
        self.jobs=[(k,painted) for k in ('dogic_i','dogic_20') for painted in (False,True)]
        Clock.schedule_once(self.next,.3);return self.root

    def next(self,*_):
        if not self.jobs:self.stop();return
        self.kind,self.painted=self.jobs.pop(0);model=PolyhedralPuzzle(self.kind,3)
        if not self.painted:model.colors=[-1]*len(model.colors)
        self.view.set_cube(model)
        for label in self.view._face_labels:label.text=''
        Clock.schedule_once(self.capture,.2)

    def capture(self,*_):
        self.view._draw()
        self.view.export_to_png(str(OUT/(self.kind+('-painted' if self.painted else '-grey')+'.png')))
        Clock.schedule_once(self.next,.1)


if __name__=='__main__':Preview().run()
