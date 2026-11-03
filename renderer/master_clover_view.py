"""Regular double-layer shell on the shared paint and playback renderer."""
from functools import lru_cache
from kivy.clock import Clock
from cube.master_clover import structure,centre,shell_data
from cube.polyhedral import CUBE,EDGE_AXES,triangulate,cross,dot,unit,Move
from cube.appearance import transform_frame
from renderer.copter_view import CopterView,CopterTwistView


@lru_cache(maxsize=1)
def surfaces():
    panels=structure()[2];result=[[] for _ in range(68)]
    for i,(h,f,p) in enumerate(panels):
        result[h].extend((t,CUBE[f],i) for t in triangulate(p,CUBE[f]))
        # Display backing only, not a clearance or hidden-material certificate.
        hub=tuple(v*.7 for v in centre(p,CUBE[f]))
        for a,b in zip(p,p[1:]+p[:1]):
            x=tuple(v-w for v,w in zip(b,a));y=tuple(v-w for v,w in zip(hub,a));normal=cross(x,y)
            if dot(normal,normal)>1e-16:result[h].append(((a,hub,b),unit(tuple(-v for v in normal)),-1))
    return tuple(map(tuple,result))


class MasterCloverView(CopterView):
    def _surfaces(self,cube):
        cache=getattr(self,'_master_placed',None);full=self._move is not None or self.piece_filter is not None
        stamp=cube.frames,full
        if cache is None or cache[0]!=stamp:
            rows=[]
            for h,parts in enumerate(surfaces()):
                for p,n,s in parts:
                    if s<0 and not full:continue
                    rows.append((tuple(transform_frame(cube.frames[h],v) for v in p),transform_frame(cube.frames[h],n),s,h))
            self._master_placed=stamp,tuple(rows)
        return tuple((p,n,cube.paints[s] if s>=0 and cube.paints[s]>=0 else -2 if s>=0 else -1,
                      s if s>=0 else None,0,h,1) for p,n,s,h in self._master_placed[1]
                     if self.piece_filter is None or h==self.piece_filter)

    def animate_move(self,move,on_done=None,duration=.3):
        if self._move is not None or self.cube is None:return False
        try:
            self.cube.proposed(move);self._moving_parts=frozenset(self.cube.selection(move.axis,move.layer))
        except ValueError:return False
        self._move=move;self._fraction=0.;elapsed=0.
        def tick(dt):
            nonlocal elapsed
            elapsed+=dt;self._fraction=min(1.,elapsed/max(.01,duration));self._draw()
            if self._fraction>=1:
                self.cube.apply_move(move);self._move=self._event=None;self.refresh()
                if on_done:on_done()
                return False
        self._event=Clock.schedule_interval(tick,1/24);return True


class MasterCloverTwistView(MasterCloverView,CopterTwistView):
    turn_layer=0
    def resolve_twist(self,sticker_index,drag,press=None):
        import math
        if self.cube is None or sticker_index is None or not getattr(self,'_proj',None):return None
        home=self.cube.panels[sticker_index][0];world=self.observation_world()
        point=world.transform(*self.cube.geometry.centres[home]);eye,right,up,*_=self._proj
        length=math.hypot(*drag);choices=[]
        if length<1e-7:return None
        for axis,normal in enumerate(EDGE_AXES):
            if home not in self.cube.selection(axis,self.turn_layer):continue
            velocity=cross(world.transform(*normal),point);vx,vy=dot(velocity,right),dot(velocity,up);speed=math.hypot(vx,vy)
            if speed<1e-7:continue
            score=(vx*drag[0]+vy*drag[1])/(length*speed)
            if abs(score)>.65:choices.append((abs(score),Move(axis,self.turn_layer,180. if score>0 else -180.)))
        choices.sort(key=lambda row:row[0],reverse=True)
        if not choices or len(choices)>1 and choices[0][0]-choices[1][0]<.05:return None
        return choices[0][1]
