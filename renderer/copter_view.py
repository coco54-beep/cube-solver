"""Closed-solid Copter rendering with shared entry styling."""
import math
from kivy.clock import Clock
from cube.polyhedral import rotate,EDGE_AXES
from cube.appearance import transform_frame
from renderer.square1_view import Square1View
from renderer.copter_skin import surfaces


class CopterView(Square1View):
    fit_piece=True
    pick_black_surfaces=True
    piece_filter=None
    selected_piece=None

    def _is_recorded(self,slot):return slot is not None and self.cube.paints[slot]>=0
    def _is_selected(self,slot):
        return slot is not None and (slot==self.selected or self.cube.panels[slot][0]==self.selected_piece)

    def _surfaces(self,cube):
        frames=cube.frames;cache=getattr(self,'_placed_skin',None)
        if cache is None or cache[0]!=frames:
            transformed=[]
            for home,parts in enumerate(surfaces()):
                frame=frames[home]
                for triangle,normal,slot in parts:
                    transformed.append((tuple(transform_frame(frame,p) for p in triangle),
                                        transform_frame(frame,normal),slot,home))
            self._placed_skin=(frames,tuple(transformed))
        return tuple((triangle,normal,(-2 if cube.paints[slot]<0 else cube.paints[slot]) if slot>=0 else -1,
                      slot if slot>=0 else None,0,home,1)
                     for triangle,normal,slot,home in self._placed_skin[1]
                     if self.piece_filter is None or home==self.piece_filter)

    def _physical_outlines(self):
        result={}
        for slot,(home,face,polygon) in enumerate(self.cube.panels):
            if self.piece_filter is not None and home!=self.piece_filter:continue
            placed=tuple(transform_frame(self.cube.frames[home],p) for p in polygon)
            result[slot]=tuple(zip(placed,placed[1:]+placed[:1]))
        return result

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None or start not in self._moving_parts:return points,normal
        axis=self.cube.geometry.spec.axes[self._move.axis];angle=math.radians(self._move.amount)*self._fraction
        return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or self.cube is None:return False
        try:
            self.cube.proposed(move)
            self._moving_parts=frozenset(self.cube.selection(move.axis))
        except ValueError:return False
        self._move=move;self._fraction=0.;elapsed=0.
        def tick(dt):
            nonlocal elapsed
            elapsed+=dt;self._fraction=min(1.,elapsed/max(.01,duration));self._draw()
            if self._fraction>=1:
                self.cube.apply_move(move);self._move=self._event=None;self.refresh()
                if on_done:on_done()
                return False
        self._event=Clock.schedule_interval(tick,1/24)
        return True


from renderer.articulated_view import ArticulatedTwistView
from cube.polyhedral import Move,cross,dot


class CopterTwistView(CopterView,ArticulatedTwistView):
    turn_amount=180.

    def amount_for_axis(self,axis):return self.turn_amount

    def resolve_twist(self,sticker_index,drag,press=None):
        if self.cube is None or sticker_index is None or not getattr(self,'_proj',None):return None
        home=self.cube.panels[sticker_index][0];world=self.observation_world()
        point=world.transform(*self.cube.geometry.centres[home])
        eye,right,up,*_=self._proj;length=math.hypot(*drag);choices=[]
        if length<1e-7:return None
        for axis,normal in enumerate(self.cube.geometry.spec.axes):
            try:members=self.cube.selection(axis)
            except ValueError:continue
            if home not in members:continue
            velocity=cross(world.transform(*normal),point)
            vx,vy=dot(velocity,right),dot(velocity,up);speed=math.hypot(vx,vy)
            if speed<1e-7:continue
            score=(vx*drag[0]+vy*drag[1])/(length*speed)
            amount=self.amount_for_axis(axis)
            if abs(score)>.65:choices.append((abs(score),Move(axis,0,amount if score>0 else -amount)))
        choices.sort(key=lambda item:item[0],reverse=True)
        if not choices or len(choices)>1 and choices[0][0]-choices[1][0]<.05:return None
        return choices[0][1]
