"""Cuboid family: rigid physical bricks over a bandaged cubic mechanism.

The displayed dimensions are separate from the mechanical grid. Bonds forbid
cuts through a brick after shape changes; incompatible-parity axes use 180°.
"""
from functools import lru_cache
from itertools import product
import math
from cube.polyhedral import CUBE,Spec,Geometry,Sticker,Move,rotate,key,mean

FACES=('U','R','F','D','L','B')
# Layout is x/y/z (height on y), independently of the catalogue dimension order.
MODELS={
 'cuboid_332': ((3,2,3),4),
 'cuboid_223': ((2,3,2),4),
 'cuboid_334': ((3,4,3),4),
 'cuboid_224': ((2,4,2),4),
 'cuboid_442': ((4,2,4),4),
 'cuboid_234': ((2,4,3),4),
 'cuboid_133': ((3,1,3),3),
 'cuboid_335': ((3,5,3),5),
 'cuboid_446': ((4,6,4),6),
 'camouflage_3': ((3,3,3),4),
}
PARTITIONS={
 (3,1):(3,), (3,3):(1,1,1),
 (4,2):(2,2), (4,3):(1,2,1), (4,4):(1,1,1,1),
 (5,3):(2,1,2), (5,5):(1,1,1,1,1),
 (6,4):(1,2,2,1), (6,6):(1,1,1,1,1,1),
}
IDENTITY=((1,0,0),(0,1,0),(0,0,1))


def transform(frame,p):
 return tuple(sum(frame[j][i]*p[j] for j in range(3)) for i in range(3))


def multiply(a,b):return tuple(transform(a,v) for v in b)


@lru_cache(maxsize=24)
def turn_frame(axis,amount):
 return tuple(tuple(round(v) for v in rotate(e,CUBE[axis],amount*math.pi/2)) for e in IDENTITY)


@lru_cache(maxsize=10)
def layout(kind):
 dims,n=MODELS[kind];vals=tuple(2*i-(n-1) for i in range(n))
 bins=[]
 for length in dims:
  widths=(2,1,1) if kind=='camouflage_3' else PARTITIONS[n,length];start=0;out=[]
  for width in widths:out.append(vals[start:start+width]);start+=width
  bins.append(out)
 cells=[];boxes=[]
 for index in product(*(range(d) for d in dims)):
  cells.append(tuple(product(*(bins[a][index[a]] for a in range(3)))))
  # Camouflage is an asymmetric bandaged 4x4. Its final core layer is
  # enlarged: the visible widths are 2:1:2, with the core at the first cut.
  cuts=(-2.,0.,1.,3.)
  boxes.append(tuple((cuts[index[a]],cuts[index[a]+1]) if kind=='camouflage_3'
                     else (index[a]-dims[a]/2,index[a]+1-dims[a]/2) for a in range(3)))
 entries=[];lookup={};stickers=[]
 group_by_cell={p:i for i,group in enumerate(cells) for p in group}
 for f,normal in enumerate(CUBE):
  axis,sign=next((a,v) for a,v in enumerate(normal) if v)
  for p in product(vals,repeat=3):
   if p[axis]!=sign*(n-1):continue
   lookup[p,normal]=len(entries);entries.append((p,normal))
   stickers.append(Sticker(group_by_cell[p],f,()))
 perms=[]
 for axis,normal in enumerate(CUBE):
  a,sign=next((a,v) for a,v in enumerate(normal) if v)
  other=[dims[j] for j in range(3) if j!=a]
  layers=[];frame=turn_frame(axis,1 if other[0]%2==other[1]%2 else 2)
  for width in range(1,n):
   threshold=n-1-2*(width-1)
   layers.append(tuple(lookup[transform(frame,p),transform(frame,norm)]
                       if sign*p[a]>=threshold else i for i,(p,norm) in enumerate(entries)))
  perms.append(tuple(layers))
 steps=[]
 for axis,normal in enumerate(CUBE):
  a=next(a for a,v in enumerate(normal) if v)
  other=[dims[j] for j in range(3) if j!=a]
  steps.append(1 if other[0]%2==other[1]%2 else 2)
 bounds=tuple(dims[next(a for a,v in enumerate(norm) if v)]/2 for norm in CUBE)
 spec=Spec(kind,max(dims),CUBE,CUBE,(),4,axis_steps=tuple(steps),bounds=bounds)
 if kind=='cuboid_133':
  # Super Floppy has four fixed-position edges and four corners moving
  # among twelve locations. It is not a bandaged 3x3 mechanism: a corner
  # above an edge must not prevent the adjacent edge from turning.
  panels=[];entries=[];lookup={}
  for piece,group in enumerate(cells):
   for face,normal in enumerate(CUBE):
    a,sign=next((a,v) for a,v in enumerate(normal) if v)
    home=next((p for p in group if p[a]==sign*(n-1)),None)
    if home is not None:
     lookup[piece,face]=len(panels);entries.append((home,normal))
     panels.append(Sticker(piece,face,()))
  identity=tuple(range(len(panels)))
  stickers=panels;perms=[(identity,)*(n-1) for _ in range(6)]
 base=Geometry(spec,tuple(stickers),tuple(() for _ in cells),(),tuple(perms),())
 return tuple(cells),tuple(boxes),tuple(entries),lookup,base


class CuboidCube:
 def __init__(self,kind,colors=None,frames=None,history=None):
  self.puzzle_kind=kind;self.dimensions,self.core_n=MODELS[kind];self.n=max(self.dimensions)
  cells,boxes,entries,lookup,base=layout(kind)
  self.frames=tuple(tuple(tuple(v for v in axis) for axis in f) for f in frames) if frames is not None else (IDENTITY,)*len(cells)
  if len(self.frames)!=len(cells):raise ValueError('Wrong cuboid brick count')
  from cube.appearance import ROTATIONS
  if any(frame not in ROTATIONS for frame in self.frames):raise ValueError('Invalid cuboid rotation')
  self.colors=list(colors) if colors is not None else [s.face for s in base.stickers]
  if len(self.colors)!=len(entries):raise ValueError('Wrong cuboid sticker count')
  self.history=list(history) if history is not None else ([] if colors is None else None)
  self._snapshot=(tuple(self.colors),self.frames);self._geometry_cache=None

 @classmethod
 def solved(cls,kind):return cls(kind)

 @property
 def color_count(self):return 6

 @property
 def geometry(self):
  if self._geometry_cache is not None:return self._geometry_cache
  cells,boxes,entries,lookup,base=layout(self.puzzle_kind)
  if self.puzzle_kind=='cuboid_133':
   centres=tuple(transform(f,tuple((lo+hi)/2 for lo,hi in box)) for f,box in zip(self.frames,boxes))
   pieces=tuple(tuple(i for i,s in enumerate(base.stickers) if s.piece==p) for p in range(len(cells)))
   corners={p for p,box in enumerate(boxes) if sum(abs((lo+hi)/2)>.5 for lo,hi in box)==2}
   layers=[]
   for axis,normal in enumerate(CUBE):
    a,sign=next((a,v) for a,v in enumerate(normal) if v)
    selected=tuple(p for p,c in enumerate(centres) if abs(sign*c[a]-1)<1e-8) if a!=1 else ()
    # The original Super Floppy blocks an isolated edge with no corners.
    if not corners.intersection(selected):selected=()
    layers.append((selected,()))
   self._geometry_cache=Geometry(base.spec,base.stickers,pieces,centres,base.permutations,tuple(layers))
   return self._geometry_cache
  current=[tuple(transform(frame,p) for p in group) for frame,group in zip(self.frames,cells)]
  owners={p:i for i,group in enumerate(current) for p in group}
  if len(owners)!=self.core_n**3:raise ValueError('Cuboid bricks overlap')
  stickers=tuple(Sticker(owners[p],base.stickers[i].face,()) for i,(p,norm) in enumerate(entries))
  pieces=tuple(tuple(i for i,s in enumerate(stickers) if s.piece==piece) for piece in range(len(cells)))
  layers=[]
  for axis,normal in enumerate(CUBE):
   a,sign=next((a,v) for a,v in enumerate(normal) if v);bands=[]
   for width in range(1,self.core_n):
    threshold=self.core_n-1-2*(width-1);selected=[];split=False
    for piece,group in enumerate(current):
     flags={sign*p[a]>=threshold for p in group}
     if len(flags)>1:split=True;break
     if True in flags:selected.append(piece)
    bands.append(tuple(selected) if not split and len(selected)<len(cells) else ())
   layers.append(tuple(bands))
  centres=tuple(transform(f,tuple((lo+hi)/2 for lo,hi in box)) for f,box in zip(self.frames,boxes))
  self._geometry_cache=Geometry(base.spec,stickers,pieces,centres,base.permutations,tuple(layers))
  return self._geometry_cache

 def can_apply(self,move):
  g=self.geometry
  return (0<=move.axis<6 and 0<=move.layer<self.core_n-1 and
          move.amount%g.spec.step(move.axis)==0 and bool(g.layers[move.axis][move.layer]))

 def moves(self):
  return tuple(Move(a,l,self.geometry.spec.step(a)) for a in range(6) for l in range(self.core_n-1)
               if self.can_apply(Move(a,l,self.geometry.spec.step(a))))

 def layer_labels(self,axis):
  from app.i18n import tr
  a=next(a for a,v in enumerate(CUBE[axis]) if v);g=self.geometry
  labels=[]
  for i,band in enumerate(g.layers[axis]):
   depth=len({round(g.centres[p][a],6) for p in band})
   labels.append(tr('cuboid.outer_layers',i=depth) if band else tr('cuboid.layer_blocked',i=i+1))
  return tuple(labels)

 def apply_move(self,move):
  if move.amount%4==0:return self
  if not self.can_apply(move):raise ValueError('This turn crosses a rigid cuboid brick')
  if (tuple(self.colors),self.frames)!=self._snapshot:self.history=None
  g=self.geometry;moving=set(g.layers[move.axis][move.layer]);rotation=turn_frame(move.axis,move.amount%4)
  inverse=g.inverse_permutation(move)
  colors=list(self.colors) if self.puzzle_kind=='cuboid_133' else list(map(self.colors.__getitem__,inverse))
  frames=tuple(multiply(rotation,f) if i in moving else f for i,f in enumerate(self.frames))
  # All mutation occurs after legality and permutations have been obtained.
  self.colors,self.frames=colors,frames;self._geometry_cache=None
  if self.history is not None:
   self.history.append(move)
   if len(self.history)>4096:self.history=None
  self._snapshot=(tuple(self.colors),self.frames)
  return self

 def apply_moves(self,moves):
  for move in moves:self.apply_move(move)
  return self

 def clone(self):
  result=type(self)(self.puzzle_kind,self.colors,self.frames)
  if (tuple(self.colors),self.frames)==self._snapshot:
   result.history=None if self.history is None else list(self.history)
  return result

 def entered(self):return self.clone()

 def restore(self,other):
  if self.puzzle_kind!=other.puzzle_kind:raise ValueError('Cuboid model mismatch')
  self.colors=list(other.colors);self.frames=other.frames
  self.history=None if other.history is None else list(other.history)
  self._snapshot=(tuple(self.colors),self.frames);self._geometry_cache=None

 def is_solved(self):
  if self.puzzle_kind=='cuboid_133':
   if any(not 0<=c<6 or CUBE[c]!=transform(self.frames[s.piece],CUBE[s.face])
          for c,s in zip(self.colors,self.geometry.stickers)):return False
  elif any(c!=s.face for c,s in zip(self.colors,self.geometry.stickers)):return False
  cells,boxes,*_=layout(self.puzzle_kind)
  bounds=((-2.,3.),)*3 if self.puzzle_kind=='camouflage_3' else tuple((-d/2,d/2) for d in self.dimensions)
  for frame,box in zip(self.frames,boxes):
   for corner in product(*box):
    p=transform(frame,corner)
    if any(p[a]<bounds[a][0]-1e-8 or p[a]>bounds[a][1]+1e-8 for a in range(3)):return False
  return True

 def paint(self,index,color):
  g=self.geometry;s=g.stickers[index]
  for i in g.pieces[s.piece]:
   if g.stickers[i].face==s.face:self.colors[i]=color
  self.history=None;self._snapshot=(tuple(self.colors),self.frames)

 def panels(self):
  # One representative index for each physical coloured panel, regardless
  # of how many mechanical cells support it.
  g=self.geometry
  return tuple(next(iter(slots)) for slots in self._panel_groups(g).values())

 def _panel_groups(self,g):
  groups={}
  for i,s in enumerate(g.stickers):groups.setdefault((s.piece,s.face),[]).append(i)
  return groups

 def entry_progress(self):
  groups=self._panel_groups(self.geometry).values()
  return sum(all(self.colors[i]>=0 for i in slots) for slots in groups),len(self._panel_groups(self.geometry))
