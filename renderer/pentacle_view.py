"""Independent circular face panels and ordinary core housings."""
import math
from cube.polyhedral import add,scale,mean,rotate,dot,cross,CUBE,Move
from renderer.articulated_view import ArticulatedView,ArticulatedTwistView

class PentacleView(ArticulatedView):
    def _inset(self,points):return points
    def _surface_depth_bias(self,color):return -.0006 if color>=0 or color==-2 else 0.
    def _surfaces(self,cube):
        result=[]
        for slot,sticker in enumerate(cube.geometry.stickers):
            from cube.polyhedral import CUBE
            normal=CUBE[sticker.face];patches=sticker.patches or (sticker.polygon,)
            centre=mean(tuple(v for poly in patches for v in poly))
            for polygon in patches:
                result.append((polygon,normal,-1,slot,0,sticker.piece,1))
                panel=tuple(add(add(centre,scale(add(v,scale(centre,-1)),.984)),scale(normal,.0015)) for v in polygon)
                result.append((panel,normal,cube._paints[slot] if cube._paints[slot]>=0 else -2,slot,0,sticker.piece,1))
        return tuple(result)
    def _is_recorded(self,slot):return True

class PentacleTwistView(PentacleView,ArticulatedTwistView):
    def resolve_twist(self,sticker_index,drag,press=None):
        if self.cube is None or sticker_index is None or press is None:return None
        hit=self.pick_surface(*press)
        if hit is None:return None
        eye,right,up,factor,*_=self._proj;point=hit[1]
        world=self.observation_world();slot=self.cube.geometry.stickers[sticker_index]
        if getattr(self,'selected_turn_layer',0)==0:
            if slot.piece not in self.cube.discs:return None
            face=slot.face;normal=world.transform(*CUBE[face]);centre=normal
            facing=dot(normal,eye)
            if abs(facing)<.05:return None
            start=add(point,scale(centre,-1))
            start=add(start,scale(normal,-dot(start,normal)))
            delta=add(scale(right,drag[0]/factor),scale(up,drag[1]/factor))
            delta=add(delta,scale(eye,-dot(normal,delta)/facing))
            end=add(start,delta)
            if dot(start,start)<.005 or dot(end,end)<.005:return None
            angle=round(math.degrees(math.atan2(dot(cross(start,end),normal),dot(start,end))),1)
            return Move(face,0,angle) if abs(angle)>.1 else None
        length=math.hypot(*drag);candidates=[]
        if length<1e-7:return None
        for axis,normal in enumerate(CUBE):
            if slot.piece not in self.cube.geometry.layers[axis][1]:continue
            velocity=cross(world.transform(*normal),point)
            vx,vy=dot(velocity,right),dot(velocity,up);speed=math.hypot(vx,vy)
            if speed<1e-7:continue
            score=(drag[0]*vx+drag[1]*vy)/(length*speed)
            move=Move(axis,1,90 if score>0 else 270)
            if abs(score)>.65 and self.cube.can_apply(move):candidates.append((abs(score),move))
        candidates.sort(key=lambda item:item[0],reverse=True)
        if not candidates or len(candidates)>1 and candidates[0][0]-candidates[1][0]<.05:return None
        return candidates[0][1]
