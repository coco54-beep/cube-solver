"""Closed planar Comet solids, shared colours, selection and turn animation."""
from functools import lru_cache
from cube.polyhedral import cross,add,dot,unit,scale,triangulate
from cube.appearance import transform_frame
from cube.crazy_comet import structure
from renderer.copter_view import CopterView,CopterTwistView
from renderer.polyhedral_view import PALETTE


@lru_cache(maxsize=1)
def surfaces():
    masks,solids,panels=structure();slots={(h,f):i for i,(h,f,p) in enumerate(panels)};result=[]
    for home,faces in enumerate(solids):
        parts=[]
        for poly,color in faces:
            normal=(0.,0.,0.)
            for a,b in zip(poly,poly[1:]+poly[:1]):normal=add(normal,cross(a,b))
            if dot(normal,normal)<1e-18:continue
            normal=unit(normal);slot=slots[home,color] if color>=0 else -1
            parts.extend((triangle,normal,slot) for triangle in triangulate(poly,normal))
        result.append(tuple(parts))
    return tuple(result)


class CometView(CopterView):
    home_surfaces=staticmethod(surfaces)
    def set_cube(self,cube):
        super().set_cube(cube);self.palette=PALETTE

    def _surfaces(self,cube):
        cached=getattr(self,'_placed_comet',None)
        if cached is None or cached[0]!=cube.frames:
            placed=[]
            for home,parts in enumerate(self.home_surfaces()):
                frame=cube.frames[home]
                for triangle,normal,slot in parts:
                    placed.append((tuple(transform_frame(frame,p) for p in triangle),transform_frame(frame,normal),slot,home))
            self._placed_comet=(cube.frames,tuple(placed))
        return tuple((poly,normal,cube.paints[slot] if slot>=0 and cube.paints[slot]>=0 else -2 if slot>=0 else -1,
                      slot if slot>=0 else None,0,home,1) for poly,normal,slot,home in self._placed_comet[1]
                     if self.piece_filter is None or home==self.piece_filter)


class CometTwistView(CometView,CopterTwistView):pass


@lru_cache(maxsize=1)
def physical_surfaces():
    from cube.lanlan_comet import structure
    solids,panels=structure();slots={(h,p):i for i,(h,f,p) in enumerate(panels)};result=[]
    for home,faces in enumerate(solids):
        parts=[]
        for poly,color in faces:
            normal=(0.,0.,0.)
            for a,b in zip(poly,poly[1:]+poly[:1]):normal=add(normal,cross(a,b))
            if dot(normal,normal)<1e-18:continue
            normal=unit(normal);slot=slots[home,poly] if color>=0 else -1
            parts.extend((triangle,normal,slot) for triangle in triangulate(poly,normal))
        result.append(tuple(parts))
    return tuple(result)


class LanlanCometView(CometView):
    home_surfaces=staticmethod(physical_surfaces)

    def set_cube(self,cube):
        super().set_cube(cube)
        self.palette=PALETTE[:12]+((.72,.57,.29,1.),)


class LanlanCometTwistView(LanlanCometView,CopterTwistView):pass
