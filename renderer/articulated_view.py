"""Render attached coloured panels on moving rigid solids."""
import math
from cube.polyhedral import add,scale,cross,dot,unit,mean,rotate,Move
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralView,PolyhedralTwistView


class ArticulatedView(Square1View):
    piece_filter=None

    def _inset(self,points):
        # Sticker borders are already built below. Shrinking every housing
        # face independently opens seams between its sides and back cap.
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
        for points,color in cube.placed_faces(home):
            slot=next(slots) if color>=0 else fallback
            if getattr(cube,'family',None)=='mixup' and color<0:continue
            normal=(0.,0.,0.)
            for a,b in zip(points,points[1:]+points[:1]):normal=add(normal,cross(a,b))
            if dot(normal,normal)<1e-14:continue
            normal=unit(normal)
            result.append((points,normal,-1,slot,0,home,1))
            if getattr(cube,'family',None)=='mixup':
                # Close the body towards the turning core. A constant,
                # shallow back plate leaves pieces looking hollow/missing
                # after centre/edge exchange. Radial tapered housings keep
                # their original panels and avoid the false rectangular
                # internal caps of the construction boxes. These are
                # display surfaces, never collision/solver geometry.
                back=tuple(scale(p,.35) for p in points)
                result.append((tuple(reversed(back)),scale(normal,-1),-1,slot,0,home,1))
                for i,(p,q) in enumerate(zip(points,points[1:]+points[:1])):
                    side=(p,back[i],back[(i+1)%len(back)],q)
                    n=cross(add(side[1],scale(p,-1)),add(side[2],scale(p,-1)))
                    if dot(n,n)>1e-14:result.append((side,unit(n),-1,slot,0,home,1))
            if color>=0:
                centre=mean(points)
                panel=tuple(add(add(centre,scale(add(p,scale(centre,-1)),.95)),scale(normal,.0015)) for p in points)
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
