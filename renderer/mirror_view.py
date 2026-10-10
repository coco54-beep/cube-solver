"""Mirror pieces use offset planar boxes, never tetrahedron geometry."""
from app.constants import COLOR_INFO
from cube.mirror import piece_faces
from cube.mastermorphix import transform
from renderer.mastermorphix_view import MastermorphixView

COLOR_INFO.setdefault('MIRROR',('Silver',(.76,.79,.84,1)))


class MirrorView(MastermorphixView):
    @staticmethod
    def _piece_geometry(home,frame,subdivisions,n):
        factor=4.2/n
        result=[]
        for vertices,normal,exterior in piece_faces(home,n):
            points=tuple(tuple(x*factor for x in transform(frame,p)) for p in vertices)
            # Every face is metallic, including surfaces exposed by a turn.
            result.append((points,transform(frame,normal),0,'sticker',((0,1),(1,2),(2,3),(3,0))))
        return tuple(result)
