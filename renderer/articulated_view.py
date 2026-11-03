"""Render attached coloured panels on moving rigid solids."""
import math
from cube.polyhedral import add,scale,cross,dot,unit,mean,rotate,Move
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralView,PolyhedralTwistView
from renderer.entry_style import surface_panel


class ArticulatedView(Square1View):
    piece_filter=None

    def _inset(self,points):
        # Full panels and closed housings share the renderer's screen strokes.
        return points

    def _surfaces(self,cube):
        return tuple(surface for home in range(len(cube.solids))
                     if self.piece_filter is None or home == self.piece_filter
                     for surface in self.piece_surfaces(cube,home))

    @staticmethod
    def piece_surfaces(cube,home):
        """Shared housing and sticker geometry for playback and rigid entry."""
        result=[]
        slots=iter(cube.geometry.pieces[home]);fallback=cube.geometry.pieces[home][0]
        if getattr(cube,'family',None)=='mixup':
            from renderer.mixup_housing import placed_housing
            for polygon in placed_housing(cube.puzzle_kind,home,cube.frames[home]):
                normal=(0.,0.,0.)
                for a,b in zip(polygon,polygon[1:]+polygon[:1]):normal=add(normal,cross(a,b))
                if dot(normal,normal)>1e-14:
                    result.append((polygon,unit(normal),-1,fallback,0,home,1))
        for points,color in cube.placed_faces(home):
            slot=next(slots) if color>=0 else fallback
            if getattr(cube,'family',None)=='mixup' and color<0:continue
            normal=(0.,0.,0.)
            for a,b in zip(points,points[1:]+points[:1]):normal=add(normal,cross(a,b))
            if dot(normal,normal)<1e-14:continue
            normal=unit(normal)
            result.append((points,normal,-1,slot,0,home,1))
            if color>=0:
                panel=surface_panel(points,normal)
                result.append((panel,normal,color,slot,0,home,1))
        return tuple(result)

    def _is_recorded(self,slot):
        return self.recorded is None or self.cube.geometry.stickers[slot].piece in self.recorded

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None:return points,normal
        layers=getattr(self._move,'layers',()) or (self._move.layer,)
        if not any(start in self.cube.geometry.layers[self._move.axis][i] for i in layers):return points,normal
        period=self.cube.geometry.spec.turn_order;amount=self._move.amount%period
        if amount>period/2:amount-=period
        axis=self.cube.geometry.spec.axes[self._move.axis];angle=math.tau*amount/period*self._fraction
        return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or not self.cube.can_apply(move):return False
        return PolyhedralView.animate_move(self,move,on_done,duration)


class ArticulatedTwistView(ArticulatedView,PolyhedralTwistView):
    def resolve_twist(self,sticker_index,drag,press=None):
        if self.cube is None or sticker_index is None or not getattr(self,'_proj',None):return None
        eye,right,up,*_=self._proj
        home=self.cube.geometry.stickers[sticker_index].piece
        point=self.observation_world().transform(*self.cube.geometry.centres[home])
        candidates=[];length=math.hypot(*drag)
        if length<1e-7:return None
        for move in self.cube.moves():
            if home not in self.cube.geometry.layers[move.axis][move.layer]:continue
            velocity=cross(self.observation_world().transform(*self.cube.geometry.spec.axes[move.axis]),point)
            vx,vy=dot(velocity,right),dot(velocity,up);speed=math.hypot(vx,vy)
            if speed<1e-7:continue
            score=(drag[0]*vx+drag[1]*vy)/(length*speed)
            if abs(score)<.65:continue
            turn=move if score>0 else move.inverse(self.cube.geometry.spec.turn_order)
            if self.cube.can_apply(turn):candidates.append((abs(score),turn))
        candidates.sort(key=lambda x:x[0],reverse=True)
        if not candidates or len(candidates)>1 and candidates[0][0]-candidates[1][0]<.05:return None
        return candidates[0][1]
