"""Rigid silver shell; piece size and centre orientation survive turns."""
import math
from cube.mirror_tower import piece_faces,SHELL_OFFSET
from cube.mastermorphix import transform
from cube.polyhedral import add,scale,cross,dot,unit,rotate,mean,clip
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralTwistView


class MirrorTowerView(Square1View):
    camera_target=scale(SHELL_OFFSET,.64)
    def _inset(self,points):
        return points
    def set_cube(self,cube):
        super().set_cube(cube)
        self.palette=((.83,.84,.85,1),)*4

    @staticmethod
    def _surfaces(cube):
        result=[]
        for pos,piece in cube.pieces.items():
            faces=piece_faces(piece.home)
            centre=mean(tuple(p for vertices,color in faces for p in vertices))
            for vertices,color in faces:
                normal=(0.,0.,0.)
                for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                    normal=add(normal,cross(a,b))
                if dot(normal,normal)<1e-16:
                    continue
                normal=unit(normal)
                def placed(p):
                    return scale(transform(piece.frame,add(centre,scale(add(p,scale(centre,-1)),.997))),.64)
                points=tuple(placed(p) for p in vertices)
                world_normal=transform(piece.frame,normal)
                # Black housing surrounds each inset silver panel. Keep a
                # fixed border width even when neighbouring pieces differ.
                result.append((points,world_normal,-1,
                               cube.geometry.pieces[pos][0],0,pos,1))
                if color<0:
                    continue
                face_centre=mean(vertices)
                edges=[]
                for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                    delta=add(b,scale(a,-1))
                    if dot(delta,delta)<1e-14:
                        continue
                    inward=unit(cross(normal,delta))
                    edges.append((inward,dot(inward,a)))
                border=min(.045,min(dot(n,face_centre)-bound for n,bound in edges)*.18)
                panel=vertices
                for inward,bound in edges:
                    panel=clip(panel,scale(inward,-1),-bound-border)
                if panel:
                    result.append((tuple(placed(add(p,scale(normal,.002))) for p in panel),
                                   world_normal,color,cube.geometry.pieces[pos][0],0,pos,1))
        return tuple(result)

    def _is_recorded(self,slot):
        return self.recorded is None or self.cube.geometry.stickers[slot].piece in self.recorded

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None or start not in self.cube.geometry.layers[self._move.axis][self._move.layer]:
            return points,normal
        axis=self.cube.geometry.spec.axes[self._move.axis]
        amount=self._move.amount%3
        angle=(2*math.pi/3 if amount==1 else -2*math.pi/3)*self._fraction
        return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)

    def animate_move(self,move,on_done=None,duration=.3):
        # Polyhedral animations use the same clock but their legality comes
        # from the tetrahedral layer permutation, not the SQ1 slice boundary.
        from renderer.polyhedral_view import PolyhedralView
        return PolyhedralView.animate_move(self,move,on_done,duration)


class MirrorTowerTwistView(MirrorTowerView,PolyhedralTwistView):
    pass
