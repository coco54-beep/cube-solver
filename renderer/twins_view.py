"""Shared-style rendering of the whole Twins and SunCube II material."""
from functools import lru_cache
from cube.twins_material import structure
from cube.compound_solids import face_normal
from cube.polyhedral import triangulate
from cube.appearance import transform_frame
from cube.appearance import transform_frame
from renderer.comet_view import CometView
from renderer.copter_view import CopterTwistView
from renderer.polyhedral_view import CUBE_PALETTE


@lru_cache(maxsize=4)
def material_surfaces(factory):
    solids,panels=factory();slots={(h,p):i for i,(h,c,p) in enumerate(panels)};result=[]
    for h,faces in enumerate(solids):
        row=[]
        for poly,color in faces:
            normal=face_normal(poly);slot=slots[h,poly] if color>=0 else -1
            row.extend((triangle,normal,slot) for triangle in triangulate(poly,normal))
        result.append(tuple(row))
    return tuple(result)


def surfaces():return material_surfaces(structure)


class PlanarTwinsView(CometView):
    home_surfaces=staticmethod(surfaces)
    def set_cube(self,cube):
        super().set_cube(cube);self.palette=CUBE_PALETTE


def sun_surfaces():
    from cube.suncube import structure as sun_structure
    return material_surfaces(sun_structure)


class SunCubeView(PlanarTwinsView):home_surfaces=staticmethod(sun_surfaces)
class SunCubeTwistView(SunCubeView,CopterTwistView):pass


# Legacy CAD checkpoints retain their own renderer; the public reference uses
# the same Drawing3 exterior, attached to its independently moving bodies.
from renderer.twins_cad_view import TwinsCADView,TwinsCADTwistView


def reference_surfaces():
    from cube.twins_display import surfaces
    return surfaces()


def reference_material():
    from cube.twins_pcubes import structure as reference
    return reference()[1:]


class TwinsView(TwinsCADView):
    home_surfaces=staticmethod(reference_surfaces)
    def _surfaces(self,cube):
        if getattr(cube,'geometry_profile',None)=='pcubes-skewby-twins-v1':
            return CometView._surfaces(self,cube)
        return super()._surfaces(cube)

    def _physical_outlines(self):
        if getattr(self.cube,'geometry_profile',None)!='pcubes-skewby-twins-v1':
            return super()._physical_outlines()
        from cube.twins_display import panels
        cached=getattr(self,'_curved_reference_outlines',None)
        cache_key=self.cube.frames,self.piece_filter
        if cached is None or cached[0]!=cache_key:
            result={}
            for slot,(home,face,poly) in enumerate(panels()):
                if self.piece_filter is not None and home!=self.piece_filter:continue
                placed=tuple(transform_frame(self.cube.frames[home],p) for p in poly)
                result[slot]=tuple(zip(placed,placed[1:]+placed[:1]))
            self._curved_reference_outlines=cache_key,result
        return self._curved_reference_outlines[1]


class TwinsTwistView(TwinsView,TwinsCADTwistView):pass
