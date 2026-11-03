"""Solid cuboid bricks, including black cut faces exposed by shape changes."""
import math
from cube.cuboid import layout,transform
from cube.polyhedral import CUBE,add,scale,cross,dot,mean,rotate
from renderer.square1_view import Square1View
from renderer.polyhedral_view import PolyhedralView,PolyhedralTwistView
from renderer.entry_style import surface_panel

from renderer.cuboid_surfaces import QUADS,surfaces


from renderer.tutorial_markers import TutorialMarkersMixin

class CuboidView(TutorialMarkersMixin,Square1View):
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
