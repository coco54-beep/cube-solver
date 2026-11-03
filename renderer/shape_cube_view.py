"""Render an Axis shell in each piece's mechanical frame, including deformation."""
from functools import lru_cache

from cube.shape_cube import faces_for
from cube.mastermorphix import transform
from cube.polyhedral import cross,dot,unit,add,scale,mean,CUBE
from renderer.mastermorphix_view import MastermorphixView


@lru_cache(maxsize=1024)
def _geometry(kind,home,frame,n=3):
    result=[]
    for vertices,color in faces_for(kind,home,n):
        normal=(0.,0.,0.)
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            normal=add(normal,cross(a,b))
        if dot(normal,normal)<1e-16:
            continue
        normal=unit(normal)
        points=tuple(scale(transform(frame,p),2.1) for p in vertices)
        finish='sticker' if color>=0 else 'cut'
        if kind=='pandora' and color<0 and any(all(abs(dot(axis,p)-1)<1e-8 for p in vertices) for axis in CUBE):
            finish='shell'
        result.append((points,transform(frame,normal),color,finish,
                       tuple((i,(i+1)%len(vertices)) for i in range(len(vertices)))))
    return tuple(result)


class AxisView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('axis',home,frame,n)

class FootballView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('football',home,frame,n)

    def _piece_color(self,color):
        return ((.98,.98,.98,1),(.035,.04,.045,1))[color]

class PandoraView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('pandora',home,frame,n)


class WindmillView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('windmill',home,frame,n)


class FisherView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('fisher',home,frame,n)


class TrajberView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('trajber',home,frame,n)

MasterTrajberView=TrajberView

class Dodecahedron2View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('dodecahedron_2',home,frame,n)

class Dodecahedron3View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('dodecahedron_3',home,frame,n)

class Rhombic3View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('rhombic_3',home,frame,n)

class Rhombic4View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('rhombic_4',home,frame,n)

class RhombicMask4View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('rhombic_mask_4',home,frame,n)

class Caneball4View(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):return _geometry('caneball_4',home,frame,n)

SOLID_VIEWS={'trajber':TrajberView,'trajber_4':MasterTrajberView,
             'dodecahedron_2':Dodecahedron2View,'dodecahedron_3':Dodecahedron3View,
             'rhombic_3':Rhombic3View,'rhombic_4':Rhombic4View,'rhombic_mask_4':RhombicMask4View,
             'caneball_4':Caneball4View}
