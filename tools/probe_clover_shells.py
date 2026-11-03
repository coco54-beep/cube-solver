"""Compare body orientations before assigning a physical product identity."""
import os,sys
from pathlib import Path
from functools import lru_cache
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS']='1';os.environ['KIVY_NO_FILELOG']='1'
from app.desktop_runtime import configure_graphics
configure_graphics()
from cube.hexagram import shell,HexagramCube
from cube.clover_pyraminx import CloverPyraminxCube,structure as clover_structure
from cube.clover_pyraminx import CUT
from cube.pisces import AXES,fields_for
from cube.polyhedral import TETRA,scale,dot,add,cross,unit
from cube.twins_material import partition
from renderer.pisces_view import HexagramView,field_surfaces,field_outlines
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout


@lru_cache(maxsize=1)
def structure():
    cells=(tuple((tuple(tuple(-x for x in p) for p in reversed(poly)),c) for poly,c in shell()),)
    for n in AXES:cells=partition(cells,n,CUT)
    return cells,fields_for(cells)


@lru_cache(maxsize=1)
def layout():
    cells,panels=structure();return tuple(range(len(cells))),cells,panels


class Candidate(HexagramCube):
    puzzle_kind='_clover_dual_research'
    observation_model='_clover-dual-research-v1'
    layout=staticmethod(layout)
    face_normals=TETRA
    cut_bounds=(CUT,)*12


class View(HexagramView):
    home_surfaces=staticmethod(lambda:field_surfaces(structure))
    home_outlines=staticmethod(lambda:field_outlines(structure))


def radial(p):
    if '--power3' in sys.argv:return scale(p,dot(p,p)/.75)
    if '--power5' in sys.argv:return scale(p,(dot(p,p)/.75)**2)
    return scale(p,.5/(1.25-dot(p,p)))


def radial_triangle(triangle,depth=0):
    a,b,c=triangle
    if depth<3 and max(dot(add(p,scale(q,-1)),add(p,scale(q,-1))) for p,q in ((a,b),(b,c),(c,a)))>.012:
        ab=scale(add(a,b),.5);bc=scale(add(b,c),.5);ca=scale(add(c,a),.5)
        return tuple(t for sub in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)) for t in radial_triangle(sub,depth+1))
    return (tuple(radial(p) for p in triangle),)


@lru_cache(maxsize=1)
def radial_surfaces():
    return tuple(tuple((tri,unit(cross(add(tri[1],scale(tri[0],-1)),add(tri[2],scale(tri[0],-1)))),slot)
                       for triangle,n,slot in row for tri in radial_triangle(triangle)) for row in field_surfaces(clover_structure))


@lru_cache(maxsize=1)
def radial_outlines():
    result={}
    for slot,edges in field_outlines(clover_structure).items():
        row=[]
        for a,b in edges:
            points=[radial(add(scale(a,1-k/8),scale(b,k/8))) for k in range(9)]
            row.extend(zip(points,points[1:]))
        result[slot]=tuple(row)
    return result


if any(flag in sys.argv for flag in ('--radial','--power3','--power5')):
    Candidate=CloverPyraminxCube
    class View(HexagramView):
        home_surfaces=staticmethod(radial_surfaces)
        home_outlines=staticmethod(radial_outlines)


class Preview(App):
    def build(self):
        Window.size=(600,600);self.view=View();self.jobs=[(0,0),(45,0),(0,35),(45,35)]
        if '--single' in sys.argv:self.jobs=[(0,35)]
        profile='power3' if '--power3' in sys.argv else 'power5' if '--power5' in sys.argv else 'radial' if '--radial' in sys.argv else 'dual'
        self.out=Path('artifacts/research/clover-pyraminx')/profile;self.out.mkdir(parents=True,exist_ok=True)
        root=FloatLayout();root.add_widget(self.view);Clock.schedule_once(self.next,.2);return root

    def next(self,*_):
        if not self.jobs:self.stop();return
        self.angle=self.jobs.pop(0);self.view.set_cube(Candidate());self.view.yaw,self.view.pitch=self.angle
        for label in self.view._face_labels:label.text=''
        Clock.schedule_once(self.save,.2)

    def save(self,*_):
        self.view._draw();self.view.export_to_png(str(self.out/('%s-%s.png'%self.angle)))
        Clock.schedule_once(self.next,.1)


if __name__=='__main__':Preview().run()
