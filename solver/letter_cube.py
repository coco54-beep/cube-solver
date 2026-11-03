"""Visible-state identities and constructive solving for cubic extensions.

Covered core facets have no input colours. Match those hidden identities by
the ordinary corner/edge orientation and parity constraints, rather than
asking the user to label invisible pieces.
"""
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.appearance import ROTATIONS
from cube.cuboid import CuboidCube, IDENTITY, layout, transform
from cube.letter_cube import extension_demands
from cube.polyhedral import CUBE, Move

CORNER_FACES=((0,1,2),(0,2,4),(0,4,5),(0,5,1),
              (3,2,1),(3,4,2),(3,5,4),(3,1,5))
EDGE_FACES=((0,1),(0,2),(0,4),(0,5),(3,1),(3,2),
            (3,4),(3,5),(2,1),(2,4),(5,4),(5,1))


def _home(faces):
    return tuple(2*sum(CUBE[f][a] for f in faces) for a in range(3))


def normalize(cube,cancel=None):
    kind=cube.puzzle_kind;cells,_,_,lookup,base=layout(kind)
    faces=defaultdict(list)
    for s in base.stickers:faces[s.piece].append(s.face)
    at={g[0]:p for p,g in enumerate(cells)}
    def signature(p,frame,colours):
        return (transform(frame,cells[p][0]),
                tuple(sorted((transform(frame,CUBE[f]),colours[lookup[p,f]]) for f in faces[p])),
                tuple(sorted(transform(frame,v) for v in extension_demands(kind,cells[p][0])))
                if p<27 else ())
    goal=tuple(s.face for s in base.stickers)
    targets={signature(p,f,cube.colors):p for p,f in enumerate(cube.frames)}
    if len(targets)!=len(cells):raise ValueError('cuboid.identity_conflict')
    candidates=defaultdict(list)
    for p in range(len(cells)):
        for f in ROTATIONS:
            sig=signature(p,f,goal)
            if sig in targets:candidates[targets[sig]].append((p,f))
    if any(not candidates[p] for p in range(len(cells))):raise ValueError('cuboid.identity_unreachable')
    result=[None]*len(cells)
    centres=[at[tuple(2*v for v in n)] for n in CUBE]
    # The six centre positions establish a single global cube orientation.
    global_frame=None
    for rotation in ROTATIONS:
        assignments=[]
        for p in centres:
            wanted=transform(rotation,cells[p][0])
            matches=[(target,frame) for target,items in candidates.items()
                     for home,frame in items if home==p and frame==rotation
                     and transform(cube.frames[target],cells[target][0])==wanted]
            if not matches:break
            assignments.append((p,matches[0][1],matches[0][0]))
        else:
            global_frame=rotation
            for p,frame,target in assignments:result[p]=frame
            break
    if global_frame is None:raise ValueError('cuboid.identity_unreachable')
    free_targets=list(range(27,len(cells)))
    def fill(index,seen):
        if cancel and cancel():raise InterruptedError()
        if index==len(free_targets):return True
        target=free_targets[index]
        for home,frame in candidates[target]:
            if home<27 or home in seen:continue
            result[home]=frame
            if fill(index+1,seen|{home}):return True
            result[home]=None
        return False
    if not fill(0,set()):raise ValueError('cuboid.identity_unreachable')
    def local(point):return tuple(sum(point[a]*global_frame[j][a] for a in range(3)) for j in range(3))
    def odd(values):return sum(a>b for i,a in enumerate(values) for b in values[i+1:])&1
    def assignments(face_rows,modulus):
        homes=[at[_home(row)] for row in face_rows];index={p:i for i,p in enumerate(homes)}
        slots={transform(global_frame,_home(row)):i for i,row in enumerate(face_rows)}
        demand_ids={};home_masks=[]
        for home in homes:
            mask=0
            for point in sorted(extension_demands(kind,cells[home][0])):
                demand_ids[point]=len(demand_ids);mask|=1<<demand_ids[point]
            home_masks.append(mask)
        target_demands=[]
        for target,frame in enumerate(cube.frames[:27]):
            pos=transform(frame,cells[target][0])
            if pos not in slots:continue
            target_demands.extend(transform(frame,v) for v in extension_demands(kind,cells[target][0]))
        def demand_key(point):
            anchor=tuple(max(-2,min(2,v)) for v in point)
            return slots[anchor],local(point)
        target_ids={p:i for i,p in enumerate(sorted(target_demands,key=demand_key))}
        free=[None]*len(demand_ids)
        for home in free_targets:
            point=cells[home][0]
            if point in demand_ids:free[demand_ids[point]]=target_ids[transform(result[home],point)]
        if any(v is None for v in free):raise ValueError('cuboid.identity_unreachable')
        free_parity=odd(free)
        options=[[] for _ in homes]
        for target,items in candidates.items():
            pos=transform(cube.frames[target],cells[target][0])
            slot=slots.get(pos)
            if slot is None:continue
            normals=[transform(global_frame,CUBE[f]) for f in face_rows[slot]]
            for home,frame in items:
                if home not in index:continue
                preferred=CUBE[face_rows[index[home]][0]]
                orientation=normals.index(transform(frame,preferred))
                sequence=[demand_ids[v] for v in sorted(extension_demands(kind,cells[home][0]),
                                                       key=lambda v:local(transform(frame,v)))]
                options[slot].append((index[home],orientation,home,frame,sequence))
        @lru_cache(maxsize=None)
        def chosen_demands(mask):return sum(home_masks[i] for i in range(len(homes)) if mask>>i&1)
        states={(0,0,0,0):()}
        for slot,items in enumerate(options):
            if cancel and cancel():raise InterruptedError()
            following={}
            for (mask,total,parity,anchor_parity),chosen in states.items():
                for i,orientation,home,frame,sequence in items:
                    if mask>>i&1:continue
                    crossings=sum((chosen_demands(mask)>>(v+1)).bit_count() for v in sequence)+odd(sequence)
                    key=(mask|1<<i,(total+orientation)%modulus,
                         parity^((mask>>(i+1)).bit_count()&1),anchor_parity^(crossings&1))
                    following.setdefault(key,chosen+((home,frame),))
            states=following
        return {(parity,anchor):states[(2**len(homes)-1,0,parity,anchor)] for parity in (0,1) for anchor in (0,1)
                if (2**len(homes)-1,0,parity,anchor) in states},free_parity
    corners,cp=assignments(CORNER_FACES,3);edges,ep=assignments(EDGE_FACES,2)
    choice=next(((c,e) for c in corners for e in edges if c[0]==e[0] and c[1]^e[1]==cp^ep),None)
    if choice is None:raise ValueError('cuboid.identity_unreachable')
    for home,frame in corners[choice[0]]+edges[choice[1]]:result[home]=frame
    result[at[(0,0,0)]]=IDENTITY
    # The position and the two/three actual coloured normals identify each
    # free extension; repeated unordered colour sets alone do not.
    if any(f is None for f in result):raise ValueError('cuboid.identity_unreachable')
    normalized=CuboidCube(kind,goal,result)
    normalized.geometry
    if {signature(p,f,normalized.colors) for p,f in enumerate(normalized.frames)}!=set(targets):
        raise ValueError('cuboid.identity_conflict')
    normalized.history=None
    return normalized


@lru_cache(maxsize=2)
def extension_chain(kind):
    from solver.cuboid_extensions import extension_mechanism
    adapter,panels,_,_=extension_mechanism(kind)
    path=Path(__file__).parent/'data'/(kind+'_extension_group.bin')
    data=json.loads(zlib.decompress(path.read_bytes()))
    if data.get('version')!=1 or data.get('fingerprint')!=adapter.fingerprint:
        raise ValueError('Extension solver data does not match its mechanism')
    return adapter,panels,data


def solve_extensions(cube,cancel=None,progress=None):
    from solver.polyhedral import compose,inverse,inverse_word
    from solver.cuboid_extensions import expand
    from solver.cuboid_extended import _extension_state
    adapter,panels,data=extension_chain(cube.puzzle_kind)
    state=_extension_state(cube);word=[]
    for level,(point,row) in enumerate(zip(data['base'],data['transversals'])):
        if cancel and cancel():raise InterruptedError()
        record=row.get(str(state[point]))
        if record is None:raise ValueError('cuboid.identity_unreachable')
        state=compose(state,inverse(tuple(record['permutation'])))
        word.extend(inverse_word(tuple(Move(*m) for m in record['word']),adapter.geometry.spec.turn_order))
        if progress:progress(level+1,len(data['base']))
    if state!=tuple(range(len(state))):raise ValueError('cuboid.identity_unreachable')
    return expand(cube.puzzle_kind,word)
