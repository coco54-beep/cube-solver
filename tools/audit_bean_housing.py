"""Render the actual bean shell, both faces, and intermediate moving parts."""
import json
import os
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from app.theme import Theme
from cube.polyhedral import PolyhedralPuzzle,Move
from cube.dial_beans import petals
from renderer.dial_bean_view import DialBeanView
from renderer.mat4 import Mat4
from renderer.bean_housing import housing

OUT=Path('reports/expansion/2026-10-26/bean-housing')


class Audit(App):
    def build(self):
        self.theme=Theme();Window.size=(700,700);Window.clearcolor=(.93,.96,.98,1)
        self.cases=[(kind,pose) for kind in ('bean_6','bean_10') for pose in
                    ('front','oblique','back','blank','wing-mid','rotor-mid','back-rotor-mid')]
        self.rows=[];OUT.mkdir(parents=True,exist_ok=True)
        Clock.schedule_once(self.next,.1)
        return FloatLayout()

    def next(self,*_):
        if not self.cases:self.stop();return
        kind,pose=self.cases.pop(0);cube=PolyhedralPuzzle(kind,6 if kind=='bean_6' else 10)
        view=DialBeanView();self.root.clear_widgets();self.root.add_widget(view);view.set_cube(cube)
        view.yaw=18 if pose in ('oblique','wing-mid','rotor-mid','back-rotor-mid') else 0
        view.pitch=18 if pose in ('oblique','wing-mid','rotor-mid','back-rotor-mid') else 8
        if pose in ('back','back-rotor-mid'):view.set_whole_world(Mat4.rotation_axis(180,(0,1,0)))
        if pose=='blank':cube.colors=[-1]*len(cube.colors)
        if pose in ('wing-mid','rotor-mid','back-rotor-mid'):
            axis=(2 if pose=='wing-mid' else 3)*petals(kind)+int(pose=='back-rotor-mid')
            view._move=Move(axis,0,cube.geometry.spec.step(axis));view._fraction=.5
        self.kind,self.pose,self.view=kind,pose,view
        Clock.schedule_once(self.capture,.1)

    def capture(self,*_):
        view=self.view;times=[]
        for _ in range(3):
            start=perf_counter();view._draw();times.append(perf_counter()-start)
        view.export_to_png(str(OUT/(self.kind+'-'+self.pose+'.png')))
        self.rows.append(dict(kind=self.kind,pose=self.pose,housing_facets=len(housing(self.kind)),
                              selectable_facets=sum(i is not None for _,i in view._polygons),
                              median_draw_seconds=round(sorted(times)[1],4)))
        (OUT/'render.json').write_text(json.dumps(self.rows,indent=2),encoding='utf8')
        view.cancel_animation();Clock.schedule_once(self.next,.05)


if __name__=='__main__':Audit().run()
