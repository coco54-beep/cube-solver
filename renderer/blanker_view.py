"""White decorative grids ride on eight rigid Blanker pieces."""
from cube.blanker import piece_faces
from cube.mastermorphix import transform
from cube.polyhedral import dot
from renderer.mirror_view import MirrorView
from renderer.entry_style import PLASTIC,shade_unentered


class BlankerView(MirrorView):
    def _piece_color(self,color):return (.98,.98,.98,1.)

    def _surface_shade(self,rgba,normal,eye,light,finish,recorded):
        if finish=='cut':return PLASTIC
        if not recorded:return shade_unentered(normal)
        c=(.98,.98,.98)
        brightness=.8+.2*max(0,dot(normal,light))
        return tuple(v*brightness for v in c)+(1.,)

    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        result=[];factor=4.2/2
        for vertices,normal,outside in piece_faces(home):
            axis=next(a for a,v in enumerate(normal) if v);others=[a for a in range(3) if a!=axis]
            ranges=[]
            for a in others:
                lo=min(p[a] for p in vertices);hi=max(p[a] for p in vertices)
                ranges.append([lo]+([2/3] if outside and lo<2/3<hi else [])+[hi])
            for left,right in zip(ranges[0],ranges[0][1:]):
                for bottom,top in zip(ranges[1],ranges[1][1:]):
                    points=[]
                    for u,v in ((left,bottom),(right,bottom),(right,top),(left,top)):
                        p=list(vertices[0]);p[others[0]]=u;p[others[1]]=v
                        points.append(tuple(x*factor for x in transform(frame,p)))
                    result.append((tuple(points),transform(frame,normal),0,'sticker' if outside else 'cut',
                                   ((0,1),(1,2),(2,3),(3,0))))
        return tuple(result)
