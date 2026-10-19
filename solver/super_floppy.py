"""Shortest state-based restoration for the original 3,041,280-state Super Floppy.

Reference mechanism: Jaap Scherphuis, /puzzles/floppy2.htm. Isolated edges
without a corner cannot turn. The shipped distance table is produced offline.
"""
from array import array
from collections import deque
from functools import lru_cache
from itertools import permutations,product
from pathlib import Path
import zlib

from cube.cuboid import layout,transform,multiply,turn_frame,IDENTITY
from cube.polyhedral import CUBE,Move,dot

AXES=(1,2,4,5)
ATOMS=tuple(Move(axis,0,power) for axis in AXES for power in (1,2,3))


@lru_cache(maxsize=1)
def mechanism():
 cells,boxes,entries,lookup,base=layout('cuboid_133')
 homes=tuple(tuple((lo+hi)/2 for lo,hi in box) for box in boxes)
 corners=tuple(i for i,p in enumerate(homes) if sum(abs(v)>.5 for v in p)==2)
 edges=tuple(next(i for i,p in enumerate(homes) if p==CUBE[a]) for a in AXES)
 slots=tuple(p for p in product((-1,0,1),repeat=3) if sum(v*v for v in p)==2)
 slotid={p:i for i,p in enumerate(slots)}
 actions=[]
 for move in ATOMS:
  selected=frozenset(i for i,p in enumerate(slots) if dot(p,CUBE[move.axis])>.9)
  frame=turn_frame(move.axis,move.amount)
  mapping=tuple(slotid[transform(frame,p)] if i in selected else i for i,p in enumerate(slots))
  actions.append((selected,mapping))
 # At each of the twelve locations a labelled corner has one reachable frame.
 placements={}
 for home in corners:
  frames={homes[home]:IDENTITY};pending=deque([homes[home]])
  while pending:
   pos=pending.popleft();frame=frames[pos]
   for axis in AXES:
    if dot(pos,CUBE[axis])<.9:continue
    rotation=turn_frame(axis,1);target=transform(rotation,pos);nxt=multiply(rotation,frame)
    if target in frames:
     if frames[target]!=nxt:raise ValueError('Super Floppy corner orientation is not unique')
    else:frames[target]=nxt;pending.append(target)
  if len(frames)!=12:raise ValueError('Incomplete Super Floppy corner orbit')
  placements[home]=frames
 start=rank_positions(tuple(slotid[homes[p]] for p in corners))*256
 return corners,edges,homes,slots,slotid,tuple(actions),placements,start


def rank_positions(positions):
 remaining=list(range(12));result=0
 for i,p in enumerate(positions):
  j=remaining.index(p);result=result*(12-i)+j;remaining.pop(j)
 return result


def unrank_positions(rank):
 remaining=list(range(12));positions=[]
 for factor in (990,90,9,1):
  j,rank=divmod(rank,factor);positions.append(remaining.pop(j))
 return tuple(positions)


@lru_cache(maxsize=1)
def system():
 # The offline builder expands transitions; the phone never allocates this.
 corners,edges,homes,slots,slotid,actions,placements,start=mechanism()
 ranks=tuple(permutations(range(12),4));rankid={p:i for i,p in enumerate(ranks)}
 maps=tuple(array('h',(rankid[tuple(mapping[p] for p in positions)]
             if selected.intersection(positions) else -1 for positions in ranks)) for selected,mapping in actions)
 return corners,edges,homes,slots,slotid,ranks,rankid,maps,placements,start


def next_index(index,atom_index):
 selected,mapping=mechanism()[5][atom_index]
 move=ATOMS[atom_index];rank,bits=divmod(index,256)
 positions=unrank_positions(rank)
 if not selected.intersection(positions):return None
 dest=rank_positions(tuple(mapping[p] for p in positions))
 shift=AXES.index(move.axis)*2
 current=(bits>>shift)&3
 bits=(bits&~(3<<shift))|(((current+move.amount)%4)<<shift)
 return dest*256+bits


@lru_cache(maxsize=1)
def distances():
 payload=(Path(__file__).parent/'data/super_floppy.bin').read_bytes()
 if payload[:4]!=b'SF01':raise ValueError('Wrong Super Floppy table version')
 data=zlib.decompress(payload[4:])
 if len(data)!=3041280 or max(data)>15 or data[mechanism()[-1]]!=0:
  raise ValueError('Invalid Super Floppy distance table')
 return data


def _message(part):
 from app.i18n import tr
 return tr('floppy.'+part+'_error')


def entered_index(cube):
 corners,edges,homes,slots,slotid,actions,placements,start=mechanism()
 _cells,_boxes,_entries,_lookup,base=layout('cuboid_133')
 g=cube.geometry
 def painted(piece):
  return {transform(cube.frames[piece],CUBE[g.stickers[i].face]):cube.colors[i] for i in g.pieces[piece]}
 def expected(piece,frame):
  return {transform(frame,CUBE[s.face]):s.face for s in base.stickers if s.piece==piece}
 central=next(i for i,p in enumerate(homes) if all(abs(v)<.1 for v in p))
 if painted(central)!=expected(central,IDENTITY):raise ValueError(_message('centre'))
 positions=[None]*4
 for piece in corners:
  colours=painted(piece);pos=transform(cube.frames[piece],homes[piece])
  found=[]
  for label,home in enumerate(corners):
   frame=placements[home].get(pos)
   if frame is not None and colours==expected(home,frame):found.append(label)
  if len(found)!=1 or positions[found[0]] is not None:raise ValueError(_message('corner'))
  positions[found[0]]=slotid[pos]
 bits=0
 for j,piece in enumerate(edges):
  colours=painted(piece)
  candidates=[q for q in range(4) if colours==expected(piece,turn_frame(AXES[j],q))]
  if len(candidates)!=1:raise ValueError(_message('edge'))
  bits|=candidates[0]<<(2*j)
 return rank_positions(tuple(positions))*256+bits


def solve_super_floppy(cube,cancel=None,progress=None):
 if cancel and cancel():raise InterruptedError()
 index=entered_index(cube);table=distances();word=[]
 while table[index]:
  if cancel and cancel():raise InterruptedError()
  depth=table[index]
  for j,move in enumerate(ATOMS):
   target=next_index(index,j)
   if target is not None and table[target]==depth-1:
    word.append(move);index=target;break
  else:raise ValueError('Super Floppy table cannot descend')
 replay=cube.entered();replay.apply_moves(word)
 if not replay.is_solved():raise ValueError('Super Floppy solution replay failed')
 if progress:progress(1,1)
 return tuple(word)
