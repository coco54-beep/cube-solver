"""Rigid SQ profiles, four-ring slashes and split Super SQ-1 cap centres."""
import math

from kivy.clock import Clock
from cube.polyhedral import add,scale,dot,cross,unit,rotate,mean
from renderer.square1_view import Square1View,surfaces as square1_surfaces
from renderer.mirror_material import inset_panel


def family_surfaces(cube):
    result = []
    count = cube.layer_count
    for layer,start,width,piece in cube.groups():
        outline = cube.outline(layer,start,width,piece)
        if count == 2:
            low,high = (.27,1.1) if layer == 0 else (-1.1,-.27)
        else:
            high = 1.1-layer*.55-.012
            low = high-.526
        bottom = tuple((x,low,z) for x,z in outline)
        top = tuple((x,high,z) for x,z in outline)
        cap,sides = cube.piece_colors(piece)
        polygons = [(top,cap if layer == 0 else -1,0),
                    (bottom,cap if layer == count-1 else -1,0)]
        for i,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
            color = sides[i-1] if 1 <= i < len(outline)-1 else -1
            polygons.append((((a[0],low,a[1]),(b[0],low,b[1]),
                              (b[0],high,b[1]),(a[0],high,a[1])),color,i))
        centre = mean(top+bottom)
        for points,color,field in polygons:
            normal = unit(cross(add(points[1],scale(points[0],-1)),add(points[2],scale(points[0],-1))))
            if dot(normal,add(mean(points),scale(centre,-1))) < 0:
                normal = scale(normal,-1)
            slot = layer*12+start
            selected = (slot,0) if getattr(cube,'color_entry',False) else slot
            result.append((points,normal,color,selected,layer,start,width))
    if count == 2:
        # Exactly the ordinary SQ-1 middle bar, not an independently rotatable layer.
        result.extend(s for s in square1_surfaces(_Middle(cube.middle)) if s[4] == 2)
    else:
        # The two semicircular centre posts are fixed against U/u/d/D turns.
        # The right post exchanges its white/yellow ends during every slash.
        spindle = (math.sin(math.radians(75)),0.,math.cos(math.radians(75)))
        perpendicular = (math.cos(math.radians(75)),0.,-math.sin(math.radians(75)))
        for half in (0,1):
            arc = tuple((.19*(spindle[0]*math.cos(t)+perpendicular[0]*math.sin(t)),
                         .19*(spindle[2]*math.cos(t)+perpendicular[2]*math.sin(t)))
                        for t in ((math.pi/2+math.pi*i/12+math.pi*half) for i in range(13)))
            for y,color,normal in ((1.105,0,(0.,1.,0.)),(-1.105,3,(0.,-1.,0.))):
                points = tuple((x,y,z) for x,z in arc)
                if half == 0 and cube.middle:
                    points = tuple(rotate(p,spindle,math.pi) for p in points)
                    normal = rotate(normal,spindle,math.pi)
                result.append((points,normal,color,48+half,4,half,1))
    panels = []
    for points,normal,color,slot,layer,start,width in result:
        panels.append((points,normal,-1,slot,layer,start,width))
        if color >= 0 or color == -2:
            panel = inset_panel(tuple(points),tuple(normal),.012)
            if panel:
                panels.append((panel,normal,color,slot,layer,start,width))
    return tuple(panels)


class _Middle:
    color_entry = False
    def __init__(self,middle):
        self.middle = middle
    def groups(self):
        return ()


class SquareFamilyView(Square1View):
    _surfaces = staticmethod(family_surfaces)

    def __init__(self,**kwargs):
        self.on_twist = None
        self._sq_hit = None
        super().__init__(**kwargs)

    def on_touch_down(self,touch):
        handled = super().on_touch_down(touch)
        if touch is self._touch:
            self._sq_hit = self.pick_surface(*touch.pos)
        return handled

    def on_touch_up(self,touch):
        from ui.widgets import metrics as m
        if (touch is self._touch and self.lock_rotation and self.on_twist is not None
                and self._sq_hit is not None and self._touch_start is not None):
            drag = tuple(a-b for a,b in zip(touch.pos,self._touch_start))
            if sum(v*v for v in drag) >= m.h(18)**2:
                hit,self._sq_hit = self._sq_hit,None
                self.cancel_touch()
                move = self._drag_move(hit,drag)
                if move is not None:
                    self.on_twist(move)
                return True
        self._sq_hit = None
        return super().on_touch_up(touch)

    def _drag_move(self,hit,drag):
        from renderer.gesture import choose_turn
        selected,point = hit
        slot = selected[0] if isinstance(selected,tuple) else selected
        if slot >= self.cube.layer_count*12:
            return None
        layer,start = divmod(slot,12)
        _,right,up,_,_,_ = self._proj
        world = self.observation_world()
        candidates = []
        axis = world.transform(0.,-self.cube.layer_direction(layer),0.)
        velocity = cross(axis,point)
        candidates.append((layer,(dot(velocity,right),dot(velocity,up))))
        moving = start >= 6 if self.cube.layer_direction(layer) == 1 else start < 6
        if moving and self.cube.can_slice():
            axis = world.transform(math.sin(math.radians(75)),0.,math.cos(math.radians(75)))
            velocity = cross(axis,point)
            candidates.append((self.cube.layer_count,(dot(velocity,right),dot(velocity,up))))
        selected = choose_turn(drag,candidates)
        if selected is None:
            return None
        axis,sign = selected
        step = 3 if self.cube.puzzle_kind == 'square0' else 1
        from cube.square_family import SquareFamilyMove
        return SquareFamilyMove(axis,1 if axis == self.cube.layer_count else sign*step,self.cube.layer_count)

    def _inset(self,points):
        return points

    def _surface_depth_bias(self,color):
        return -.0005 if color >= 0 or color == -2 else 0.

    def _is_recorded(self,slot):
        return True

    def _motion(self,points,normal,slot,layer,start,width):
        if self._move is None:
            return points,normal
        move = self._move
        if move.axis < self.cube.layer_count:
            moving = layer == move.axis
            axis = (0.,1.,0.)
            amount = move.amount % 12
            if amount > 6:
                amount -= 12
            angle = math.radians(-self.cube.layer_direction(layer)*amount*30)*self._fraction
        else:
            moving = ((layer < self.cube.layer_count and
                       ((self.cube.layer_direction(layer) == 1 and start >= 6) or
                        (self.cube.layer_direction(layer) == -1 and start < 6))) or
                      (layer == self.cube.layer_count and start == 0))
            axis = (math.sin(math.radians(75)),0.,math.cos(math.radians(75)))
            angle = math.pi*self._fraction
        if moving:
            return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)
        return points,normal

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or self.cube is None:
            return False
        if move.axis == self.cube.layer_count and not self.cube.can_slice():
            return False
        self._move = move
        self._fraction = 0.
        elapsed = 0.
        def tick(dt):
            nonlocal elapsed
            elapsed += dt
            self._fraction = min(1.,elapsed/max(.01,duration))
            self._draw()
            if self._fraction >= 1.:
                self.cube.apply_move(move)
                self._move = self._event = None
                self.refresh()
                if on_done:
                    on_done()
                return False
        self._event = Clock.schedule_interval(tick,1/24)
        return True
