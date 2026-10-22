"""Solid cuboid bricks, including black cut faces exposed by shape changes."""
import math
from cube.cuboid import layout,transform
from cube.polyhedral import CUBE,add,scale,cross,dot,mean,rotate
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralView,PolyhedralTwistView

# Counter-clockwise, looking from outside each face.
QUADS=(
 ((0,1,0),((-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1))),
 ((1,0,0),((1,-1,-1),(1,1,-1),(1,1,1),(1,-1,1))),
 ((0,0,1),((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))),
 ((0,-1,0),((-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1))),
 ((-1,0,0),((-1,-1,1),(-1,1,1),(-1,1,-1),(-1,-1,-1))),
 ((0,0,-1),((1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1))),
)


def surfaces(cube):
 cache_key=(cube.frames,tuple(cube.colors),getattr(cube,'entry_pieces',None),
            tuple(sorted(getattr(cube,'entry_panel_colors',{}).items())),getattr(cube,'entry_preview',None))
 cached=getattr(cube,'_cuboid_surface_cache',None)
 if cached is not None and cached[0]==cache_key:return cached[1]
 cells,boxes,entries,lookup,_base=layout(cube.puzzle_kind)
 result=[];factor=2.4/(5 if cube.puzzle_kind=='camouflage_3' else max(cube.dimensions))
 for piece,(frame,box) in enumerate(zip(cube.frames,boxes)):
  if hasattr(cube,'entry_pieces') and piece not in cube.entry_pieces:continue
  for face,(normal,corners) in enumerate(QUADS):
   points=tuple(tuple(box[a][1 if p[a]>0 else 0] for a in range(3)) for p in corners)
   normalworld=transform(frame,normal)
   world=tuple(scale(transform(frame,p),factor) for p in points)
   # A sticker exists only on an original exterior face. The rigid cut wall
   # is still rendered and can be exposed after a quarter turn.
   axis,sign=next((a,v) for a,v in enumerate(normal) if v)
   anchored=getattr(cube,'panel_anchored',False)
   original=(piece,face) in lookup if anchored else any(p[axis]==sign*(cube.core_n-1) for p in cells[piece])
   index=-1;color=-1
   if original:
    if anchored:index=lookup[piece,face]
    else:
     home=next(p for p in cells[piece] if p[axis]==sign*(cube.core_n-1))
     index=lookup[piece,face] if cube.puzzle_kind=='cuboid_133' else lookup[transform(frame,home),normalworld]
    color=(cube.entry_panel_colors[piece,face] if hasattr(cube,'entry_panel_colors') else cube.colors[index])
    if piece==getattr(cube,'entry_preview',None):index=-3
    if color<0:color=-2
   # Black body and an inset panel give physical borders without drawing
   # the artificial subdivisions of the internal mechanism.
   result.append((world,normalworld,-1,-1,0,piece,1))
   if original:
    centre=mean(world)
    inset=tuple(add(centre,scale(add(p,scale(centre,-1)),.955)) for p in world)
    panel=tuple(add(p,scale(normalworld,.001)) for p in inset)
    result.append((panel,normalworld,color,index,0,piece,1))
 result=tuple(result)
 cube._cuboid_surface_cache=(cache_key,result)
 return result


class CuboidView(Square1View):
 _surfaces=staticmethod(surfaces)
 fit_piece=False
 def set_cube(self,cube):
  self.camera_target=(.24,.24,.24) if cube.puzzle_kind=='camouflage_3' else (0.,0.,0.)
  super().set_cube(cube)
  for label in self._face_labels:self.remove_widget(label)
  self._face_labels=[]
 def _is_recorded(self,slot):return True
 def _inset(self,points):return points
 def _draw(self,*args):
  super()._draw(*args)
  if self.cube is None or not getattr(self,'_proj',None):return
  eye,right,up,factor,cx,cy=self._proj;observation=self.observation_world()
  # Exposed plastic must occlude painted panels behind it during picking,
  # exactly as it does in the depth-buffered rendered model.
  for points,normal,color,slot,layer,start,width in surfaces(self.cube):
   if slot>=0:continue
   points,normal=self._motion(points,normal,slot,layer,start,width)
   normal=observation.transform(*normal)
   if dot(normal,eye)<=1e-8:continue
   points=tuple(observation.transform(*p) for p in points)
   projected=tuple((cx+dot(p,right)*factor,cy+dot(p,up)*factor,-dot(p,eye)*.12) for p in points)
   self._polygons.append((projected,-1))
 def pick_surface(self,x,y):
  hit=super().pick_surface(x,y)
  return hit if hit is not None and hit[0]>=0 else None
 def _motion(self,points,normal,slot,layer,start,width):
  if self._move is None or start not in self.cube.geometry.layers[self._move.axis][self._move.layer]:return points,normal
  amount=self._move.amount%4
  if amount>2:amount-=4
  axis=self.cube.geometry.spec.axes[self._move.axis];angle=amount*math.pi/2*self._fraction
  return tuple(rotate(p,axis,angle) for p in points),rotate(normal,axis,angle)
 def animate_move(self,move,on_done=None,duration=.3):
  if not self.cube.can_apply(move):return False
  return PolyhedralView.animate_move(self,move,on_done,duration)


class CuboidTwistView(CuboidView,PolyhedralTwistView):
 def resolve_twist(self,index,drag,press=None):
  if index is None or self.cube is None:return None
  from renderer.gesture import choose_turn
  from cube.polyhedral import Move
  g=self.cube.geometry;piece=g.stickers[index].piece
  panel=next((s for s in surfaces(self.cube) if s[3]==index),None)
  if panel is None:return None
  observation=self.observation_world();point=observation.transform(*mean(panel[0]))
  eye,right,up,*_=self._proj;candidates=[];moves=[]
  for move in self.cube.moves():
   if piece not in g.layers[move.axis][move.layer]:continue
   axis=observation.transform(*g.spec.axes[move.axis]);v=cross(axis,point)
   candidates.append((len(moves),(dot(v,right),dot(v,up))));moves.append(move)
  selected=choose_turn(drag,candidates)
  if selected is None:return None
  move=moves[selected[0]]
  return Move(move.axis,move.layer,(selected[1]*g.spec.step(move.axis))%4)
