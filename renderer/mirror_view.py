"""Mirror pieces use offset planar boxes, never tetrahedron geometry."""
from app.constants import COLOR_INFO
from cube.mirror import piece_faces
from cube.mastermorphix import transform
from renderer.mastermorphix_view import MastermorphixView
from renderer.mirror_material import SILVER, panel_geometry, shade_surface

COLOR_INFO.setdefault('MIRROR',('Silver',SILVER))


class MirrorView(MastermorphixView):
    inset_silver_panels = True

    def _piece_color(self, color):
        return SILVER

    def _render_piece_geometry(self, home, frame, subdivisions, n):
        return tuple(panel_geometry(self._piece_geometry(home, frame, subdivisions, n)))

    def _surface_shade(self, rgba, normal, eye, light, finish, recorded):
        return shade_surface(normal, eye, finish == 'sticker', recorded)

    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        factor=4.2/n
        result=[]
        for vertices,normal,exterior in piece_faces(home,n):
            points=tuple(tuple(x*factor for x in transform(frame,p)) for p in vertices)
            result.append((points,transform(frame,normal),0,'sticker' if exterior else 'cut',((0,1),(1,2),(2,3),(3,0))))
        return tuple(result)
