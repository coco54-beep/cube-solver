"""Render private reference geometry without adding an unfinished catalogue item."""
import os,sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from cube.curvy_copter import CopterState,JUMBLE
from cube.polyhedral import Move
from renderer.copter_view import CopterView

OUT=Path('reports/expansion/2026-10-27/pending-completion/copter-reference')


class Preview(App):
    def build(self):
        self.passed=False;OUT.mkdir(parents=True,exist_ok=True);Window.size=(520,520)
        root=FloatLayout();self.view=CopterView();root.add_widget(self.view)
        source=CopterState();self.gray=CopterState(source.frames,[-1]*72)
        self.view.set_cube(self.gray);Clock.schedule_once(self.gray_ready,.3)
        return root

    def gray_ready(self,*_):
        self.view._draw();self.view.export_to_png(str(OUT/'gray.png'))
        before=self.gray.paints
        def paint(slot):
            colors=list(self.gray.paints);colors[slot]=2;self.gray.paints=tuple(colors)
        self.view.on_pick=paint;clicked=set()
        for triangle,slot in list(self.view._polygons):
            if slot is None or slot in clicked:continue
            x=sum(p[0] for p in triangle)/len(triangle)+self.view.x
            y=sum(p[1] for p in triangle)/len(triangle)+self.view.y
            if self.view.pick(x,y)!=slot:continue
            touch=SimpleNamespace(pos=(x,y),grab=lambda _:None,ungrab=lambda _:None)
            assert self.view.on_touch_down(touch) and self.view.on_touch_up(touch)
            clicked.add(slot)
            if len(clicked)==2:break
        assert len(clicked)==2 and {i for i,(a,b) in enumerate(zip(before,self.gray.paints)) if a!=b}==clicked
        self.view.on_pick=None
        self.view.set_cube(CopterState());Clock.schedule_once(self.solved_ready,.15)

    def solved_ready(self,*_):
        self.view._draw();self.view.export_to_png(str(OUT/'solved.png'))
        self.view.cube.apply_move(Move(0,0,-JUMBLE));self.view.cube.apply_move(Move(8,0,-JUMBLE))
        self.view.cube.apply_move(Move(1,0,180.));self.view.refresh()
        Clock.schedule_once(self.jumbled_ready,.15)

    def jumbled_ready(self,*_):
        self.view._draw();self.view.export_to_png(str(OUT/'jumbled.png'))
        assert self.view._meshes and max(self.view._meshes[0].indices)<65536
        before=self.view.cube.signature();assert not self.view.animate_move(Move(3,1,180.))
        assert self.view.cube.signature()==before
        move=Move(0,0,JUMBLE)
        self.expected=CopterState(self.view.cube.proposed(move),self.view.cube.paints).signature()
        assert self.view.animate_move(move,self.first_restored,duration=.12)

    def first_restored(self,*_):
        assert self.view.cube.signature()==self.expected
        assert self.view.animate_move(Move(8,0,JUMBLE),self.restored,duration=.12)

    def restored(self,*_):
        self.view.cube.aligned_permutation();self.view._draw()
        self.view.export_to_png(str(OUT/'shape-restored.png'))
        result=dict(passed=True,regions=len(self.view.cube.regions),panels=len(self.view.cube.panels),
                    vertices=len(self.view._meshes[0].vertices)//7,continuous_colour_pick=True,guarded_animation=True)
        (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.passed=True
        self.stop()


if __name__=='__main__':
    app=Preview();app.run()
    if not app.passed:raise SystemExit(1)
