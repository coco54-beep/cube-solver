"""One selectable colour field per Pisces patch, across housing facets."""
from functools import lru_cache
from collections import Counter
from cube.pisces import structure
from cube.compound_solids import face_normal
from cube.polyhedral import triangulate,key,dot,add,scale
from cube.appearance import transform_frame
from renderer.twins_view import PlanarTwinsView
from renderer.copter_view import CopterTwistView


@lru_cache(maxsize=4)
def field_surfaces(factory):
    solids,panels=factory();slots={(h,c):i for i,(h,c,p) in enumerate(panels)};result=[]
    for h,faces in enumerate(solids):
        row=[]
        for poly,color in faces:
            normal=face_normal(poly);slot=slots[h,color] if color>=0 else -1
            row.extend((triangle,normal,slot) for triangle in triangulate(poly,normal))
        result.append(tuple(row))
    return tuple(result)


@lru_cache(maxsize=4)
def field_outlines(factory):
    solids,panels=factory();result={}
    for slot,(home,color,cloud) in enumerate(panels):
        faces=[p for p,c in solids[home] if c==color];points={key(p):p for face in faces for p in face};edges=Counter()
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                delta=add(b,scale(a,-1));length=dot(delta,delta)
                if length<1e-16:continue
                along=[]
                for k,p in points.items():
                    t=dot(add(p,scale(a,-1)),delta)/length
                    if -1e-7<=t<=1+1e-7:
                        error=add(add(a,scale(delta,t)),scale(p,-1))
                        if dot(error,error)<1e-14:along.append((t,k))
                along.sort()
                for (_,u),(_,v) in zip(along,along[1:]):
                    if u!=v:edges[tuple(sorted((u,v)))]+=1
        if any(count>2 for count in edges.values()):raise ValueError('Overlapping Pisces surface facets')
        result[slot]=tuple((points[a],points[b]) for (a,b),count in edges.items() if count==1)
    return result


def surfaces():return field_surfaces(structure)
def outlines():return field_outlines(structure)


class PiscesView(PlanarTwinsView):
    home_surfaces=staticmethod(surfaces)
    home_outlines=staticmethod(outlines)

    def _physical_outlines(self):
        return {slot:tuple((transform_frame(self.cube.frames[self.cube.panels[slot][0]],a),
                           transform_frame(self.cube.frames[self.cube.panels[slot][0]],b)) for a,b in edges)
                for slot,edges in self.home_outlines().items()
                if self.piece_filter is None or self.cube.panels[slot][0]==self.piece_filter}


class PiscesTwistView(PiscesView,CopterTwistView):pass


def hexagram_surfaces():
    from cube.hexagram import structure
    return field_surfaces(structure)


def hexagram_outlines():
    from cube.hexagram import structure
    return field_outlines(structure)


class HexagramView(PiscesView):
    home_surfaces=staticmethod(hexagram_surfaces)
    home_outlines=staticmethod(hexagram_outlines)
    def set_cube(self,cube):
        super().set_cube(cube)
        from renderer.polyhedral_view import TETRA_PALETTE
        self.palette=TETRA_PALETTE


class HexagramTwistView(HexagramView,CopterTwistView):pass


def clover_pyraminx_surfaces():
    from cube.clover_pyraminx import structure
    return field_surfaces(structure)


def clover_pyraminx_outlines():
    from cube.clover_pyraminx import structure
    return field_outlines(structure)


class CloverPyraminxView(HexagramView):
    home_surfaces=staticmethod(clover_pyraminx_surfaces)
    home_outlines=staticmethod(clover_pyraminx_outlines)


class CloverPyraminxTwistView(CloverPyraminxView,CopterTwistView):pass
