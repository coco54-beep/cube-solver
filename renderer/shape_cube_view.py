"""Render an Axis shell in each piece's mechanical frame, including deformation."""
from functools import lru_cache

from cube.shape_cube import faces_for
from cube.mastermorphix import transform
from cube.polyhedral import cross,dot,unit,add,scale,mean,CUBE
from renderer.mastermorphix_view import MastermorphixView


@lru_cache(maxsize=1024)
def _geometry(kind,home,frame):
    result=[]
    for vertices,color in faces_for(kind,home):
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
        return _geometry('axis',home,frame)

class FootballView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('football',home,frame)

    def _piece_color(self,color):
        return ((.98,.98,.98,1),(.035,.04,.045,1))[color]

class PandoraView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('pandora',home,frame)


class WindmillView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('windmill',home,frame)


class FisherView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        return _geometry('fisher',home,frame)
