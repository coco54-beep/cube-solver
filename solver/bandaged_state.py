"""Compact rigid-group search for manually entered 3/4-order bandages."""
from collections import deque
from functools import lru_cache
from pathlib import Path
from time import monotonic
import hashlib
import heapq
import json
import struct
import zlib

from cube.appearance import ROTATIONS,transform_frame
from cube.bandaged_cube import BandagedCube
from cube.coordinates import FACE_AXIS_SIGN,FACE_NORMALS,TURNS,layer_values
from cube.colors import DEFAULT_COLORS


@lru_cache(maxsize=3)
def model(kind):
    return BandageGeometry(kind)


class BandageGeometry:
    def __init__(self,kind):
        self.kind=kind
        base=BandagedCube.solved(kind)
        bonded=set().union(*base.groups) if base.groups else set()
        self.units=tuple(tuple(sorted(g)) for g in base.groups)+tuple((h,) for h in sorted(base.cubies) if h not in bonded)
        self.base=base
        faces=('L','D','B') if kind=='fused_cube' else ('R','L','U','D','F','B')
        self.moves=tuple((str(width) if width>1 else '')+face+suffix
                         for width in ((1,2) if base.n==4 else (1,))
                         for face in faces for suffix in ('',"'",'2'))
        from cube.notation import parse_move_full
        self.bands=[];turns=[]
        index={f:i for i,f in enumerate(ROTATIONS)}
        for move in self.moves:
            face,width,count=parse_move_full(move)
            axis,_=FACE_AXIS_SIGN[face]
            self.bands.append((axis,tuple(layer_values(base.n,face,layers=width))))
            row=[]
            for frame in ROTATIONS:
                for _ in range(count):frame=tuple(TURNS[face](*v) for v in frame)
                row.append(index[frame])
            turns.append(row)
        self.transitions=[];self.legal=[];self.goals=[];self.aliases=[];self.signatures=[];self.errors=[]
        target={color:FACE_NORMALS[face] for face,color in DEFAULT_COLORS.items()}
        for unit in self.units:
            signatures=[];canonical=[];equivalence={};errors=[]
            for pose,frame in enumerate(ROTATIONS):
                signature=tuple((home,transform_frame(frame,home),
                    tuple(sorted((transform_frame(frame,normal),color) for normal,color in base.cubies[home].stickers.items()))) for home in unit)
                signatures.append(signature)
                canonical.append(equivalence.setdefault(signature,pose))
                errors.append(sum(normal!=target[color] for _,_,stickers in signature for normal,color in stickers))
            rows=[];legal=[]
            for pose,frame in enumerate(ROTATIONS):
                positions=[transform_frame(frame,h) for h in unit]
                row=[];mask=0
                for i,(axis,layers) in enumerate(self.bands):
                    selected={p[axis] in layers for p in positions}
                    dest=255 if len(selected)!=1 else canonical[turns[i][pose]] if True in selected else canonical[pose]
                    row.append(dest)
                    if dest!=255:mask|=1<<i
                rows.append(bytes(row));legal.append(mask)
            self.transitions.append(tuple(rows));self.legal.append(tuple(legal))
            self.aliases.append(tuple(canonical));self.signatures.append({s:canonical[p] for p,s in enumerate(signatures)})
            self.goals.append(tuple(sorted({canonical[p] for p,e in enumerate(errors) if e==0})))
            self.errors.append(tuple(errors))
        anchor=max(range(len(self.units)),key=lambda p:len(self.units[p]))
        others=sorted((p for p in range(len(self.units)) if p!=anchor),key=lambda p:(-len(self.units[p]),-len(base.cubies[self.units[p][0]].stickers),p))
        self.patterns=tuple((anchor,)+tuple(others[i:i+3]) for i in range(0,len(others),3))
        if kind in ('ai_cube','burr_cube'):
            heavy=sorted(range(len(self.units)),key=lambda p:(-len(self.units[p]),-len(base.cubies[self.units[p][0]].stickers),p))
            extras=(tuple(heavy[:5]),tuple(heavy[:3]+heavy[5:7]))
            if kind=='burr_cube':
                extras+=tuple(tuple(heavy[i] for i in indices) for indices in ((0,4,8,12,16),(0,5,10,15,20)))
            self.patterns+=extras
        self.data=(self.moves,tuple(self.transitions),tuple(self.legal),tuple(self.goals),self.patterns,tuple(self.aliases))
        raw=json.dumps((kind,self.units,ROTATIONS,self.moves,self.transitions_as_lists()),separators=(',',':')).encode()
        self.fingerprint=hashlib.sha256(raw).hexdigest()
        masks=[]
        for p,rows in enumerate(self.legal):
            values=[0]*256;offset=(p%8)*24;values[offset:offset+24]=rows;masks.append(tuple(values))
        self.masks=tuple(masks)
        self.actions=[]
        for i in range(len(self.moves)):
            blocks=[]
            for start in range(0,len(self.units),8):
                table=bytearray(range(256))
                for p in range(start,min(start+8,len(self.units))):
                    offset=(p%8)*24
                    for pose in range(24):
                        dest=self.transitions[p][pose][i]
                        table[offset+pose]=offset+dest if dest!=255 else 255
                blocks.append(bytes(table))
            self.actions.append(tuple(blocks))

    def transitions_as_lists(self):
        return [[list(row) for row in rows] for rows in self.transitions]

    def encode(self,cube):
        current={c.home:c for c in cube.cubies.values()}
        state=[]
        for p,unit in enumerate(self.units):
            signature=tuple((h,current[h].pos,tuple(sorted(current[h].stickers.items()))) for h in unit)
            pose=self.signatures[p].get(signature)
            if pose is None:raise ValueError('bandage.entry_layout')
            state.append((p%8)*24+pose)
        return bytes(state)

    def children(self,state):
        from solver.cuboid_search import packed_turn
        mask=(1<<len(self.moves))-1
        for p,f in enumerate(state):mask&=self.masks[p][f]
        while mask:
            bit=mask&-mask;mask^=bit;i=bit.bit_length()-1
            child=packed_turn(state,self.actions[i])
            if child!=state:yield child,i

    def solved(self,state):
        return all((f-(p%8)*24) in self.goals[p] for p,f in enumerate(state))


@lru_cache(maxsize=3)
def tables(kind):
    from solver.cuboid_search import pattern_tables
    path=Path(__file__).parent/'data'/(kind+'_patterns.bin')
    try:payload=path.read_bytes()
    except OSError:raise ValueError('rigid.search_limit') from None
    if payload[:4]!=b'CP02':raise ValueError('bandage.search_table')
    size=struct.unpack_from('<I',payload,4)[0]
    header=json.loads(payload[8:8+size])
    if header.get('bandage_geometry')!=model(kind).fingerprint:raise ValueError('bandage.search_table')
    return pattern_tables(kind)


def _search_bandaged_state(cube,cancelled=None,seconds=30.,maximum=100000,weights=(1,1,0,0)):
    if cube.is_solved():return []
    geometry=model(cube.puzzle_kind)
    patterns=tables(cube.puzzle_kind)
    wg,wt,ww,wh=weights
    prepared=[]
    for pieces,distances,packed in patterns:
        offset=0
        for p in pieces:offset=offset*24+(p%8)*24
        prepared.append((pieces,offset,distances,packed))
    def estimate(state):
        best=total=0
        for pieces,offset,distances,packed in prepared:
            index=0
            for p in pieces:index=index*24+state[p]
            index-=offset
            h=((distances[index//2]>>(4*(index%2)))&15) if packed else distances[index]
            if packed and h==15:h=255
            best=max(best,h);total+=h
        wrong=sum(geometry.errors[p][f-(p%8)*24] for p,f in enumerate(state)) if ww else 0
        return best,total,wrong
    start=geometry.encode(cube)
    h,total,wrong=estimate(start)
    if h==255:raise ValueError('rigid.search_limit')
    begun=monotonic();records=[(start,-1,-1,0,-1)];best={start:0}
    pending=[(wt*total+ww*wrong+wh*h,h,0)]
    processed={};expanded=0
    while pending:
        if cancelled and cancelled():raise InterruptedError()
        if monotonic()-begun>seconds:break
        if len(records)>=maximum:
            # Generated fringe entries are far more numerous than expanded
            # states. Retain a bounded promising fringe and its parent DAG
            # instead of exhausting the memory budget after a fraction of
            # the available calculation time.
            keep=heapq.nsmallest(2500,(item for item in pending
                if best.get(records[item[2]][0])==records[item[2]][3]))
            needed=set()
            for _,_,index in keep:
                while index>=0 and index not in needed:
                    needed.add(index);index=records[index][1]
            remap={old:new for new,old in enumerate(sorted(needed))}
            records=[(s,remap.get(parent,-1),i,depth,last)
                     for s,parent,i,depth,last in (records[old] for old in sorted(needed))]
            pending=[(score,h,remap[index]) for score,h,index in keep];heapq.heapify(pending)
            best={s:depth for s,parent,i,depth,last in records}
            if len(processed)>50000:processed=dict(list(processed.items())[-25000:])
            if not pending:break
        _,h,record=heapq.heappop(pending)
        state,parent,move,depth,last=records[record]
        if best.get(state)!=depth:continue
        if processed.get(state,1000000)<=depth:continue
        processed[state]=depth;expanded+=1
        if geometry.solved(state):
            word=[]
            while parent>=0:
                word.append(geometry.moves[move]);record=parent
                state,parent,move,depth,last=records[record]
            word.reverse()
            replay=cube.clone();replay.history=[]
            for token in word:
                if cancelled and cancelled():raise InterruptedError()
                replay.apply_move(token)
            if not replay.is_solved():raise ValueError('bandage.search_replay')
            return word
        for child,i in geometry.children(state):
            key=child
            if best.get(key,1000000)<=depth+1 or processed.get(key,1000000)<=depth+1:continue
            nh,score,wrong=estimate(child)
            if nh==255:continue
            best[key]=depth+1;position=len(records)
            records.append((child,record,i,depth+1,i))
            heapq.heappush(pending,(wg*(depth+1)+wt*score+ww*wrong+wh*nh,nh,position))
            if len(records)>=maximum:break
    error=ValueError('rigid.search_limit')
    error.search_stats={'records':len(records),'pending':len(pending),'expanded':expanded,'seconds':monotonic()-begun}
    raise error


def solve_bandaged_state(cube,cancelled=None,seconds=30.,maximum=100000,weights=None):
    """Try complementary state heuristics and legal whole-cube orientations.

    A uniform face solution may use any global orientation. The input is
    untouched; each chosen orientation is included in the returned word.
    This remains a time-bounded solver, not a complete reachability test.
    """
    if cancelled and cancelled():raise InterruptedError()
    if cube.is_solved():return []
    if cube.puzzle_kind=='fused_cube':return solve_fused(cube,cancelled)
    if weights is not None:return _search_bandaged_state(cube,cancelled,seconds,maximum,weights)
    deadline=monotonic()+seconds
    geometry=model(cube.puzzle_kind);patterns=tables(cube.puzzle_kind)
    def attempt(work,prefix,budget,weights):
        if cancelled and cancelled():raise InterruptedError()
        remaining=deadline-monotonic()
        if remaining<=0:return None
        try:word=_search_bandaged_state(work,cancelled,min(budget,remaining),maximum,weights)
        except ValueError as error:
            if str(error)!='rigid.search_limit':raise
            return None
        word=list(prefix)+word;replay=cube.clone()
        for token in word:
            if cancelled and cancelled():raise InterruptedError()
            replay.apply_move(token)
        if not replay.is_solved():raise ValueError('bandage.search_replay')
        return word
    for weights in ((1,1,0,0),(1,1,1,0)):
        result=attempt(cube,(),4.,weights)
        if result is not None:return result
    from cube.coordinates import WHOLE_CUBE
    pending=deque([(cube,(),ROTATIONS[0])]);seen={ROTATIONS[0]};candidates=[]
    while pending:
        if cancelled and cancelled():raise InterruptedError()
        work,prefix,frame=pending.popleft()
        if prefix:
            state=geometry.encode(work);score=0
            for pieces,distances,packed in patterns:
                index=0
                for p in pieces:index=index*24+state[p]-(p%8)*24
                score+=((distances[index//2]>>(4*(index%2)))&15) if packed else distances[index]
            candidates.append((score,len(prefix),prefix,work))
        for token in ('x','y','z'):
            following=tuple(WHOLE_CUBE[token](*v) for v in frame)
            if following in seen:continue
            seen.add(following);child=work.clone();child.apply_move(token)
            pending.append((child,prefix+(token,),following))
    for score,_,prefix,work in sorted(candidates)[:3]:
        result=attempt(work,prefix,5.,(1,1,0,0))
        if result is not None:return result
    result=attempt(cube,(),max(0,deadline-monotonic()),(0,1,0,0))
    if result is not None:return result
    raise ValueError('rigid.search_limit')


@lru_cache(maxsize=1)
def fused_table():
    path=Path(__file__).parent/'data/fused_group.bin'
    try:data=json.loads(zlib.decompress(path.read_bytes()))
    except OSError:raise ValueError('rigid.search_limit') from None
    if data.get('version')!=1 or data.get('kind')!='fused_cube' or data.get('geometry')!=model('fused_cube').fingerprint:
        raise ValueError('bandage.search_table')
    return data


def canonical_three(cube,cancelled=None):
    """Orient fixed centre colours, without using a remembered scramble."""
    from cube.coordinates import WHOLE_CUBE
    target={color:FACE_NORMALS[face] for face,color in DEFAULT_COLORS.items()}
    centres=[(normal,target[color]) for c in cube.cubies.values() if len(c.stickers)==1 for normal,color in c.stickers.items()]
    pending=deque([(ROTATIONS[0],())]);seen={ROTATIONS[0]}
    while pending:
        if cancelled and cancelled():raise InterruptedError()
        frame,word=pending.popleft()
        if all(transform_frame(frame,normal)==goal for normal,goal in centres):
            work=cube.clone();work.apply_moves(word);return work,word
        for token in ('x','y','z'):
            following=tuple(WHOLE_CUBE[token](*v) for v in frame)
            if following not in seen:
                seen.add(following);pending.append((following,word+(token,)))
    raise ValueError('bandage.entry_layout')


def solve_fused(cube,cancelled=None):
    if cancelled and cancelled():raise InterruptedError()
    work,prefix=canonical_three(cube,cancelled)
    table=fused_table()
    atoms=[(tuple(h),tuple(n),c) for h,n,c in table['atoms']]
    slots={(h,n):i for i,(h,n,c) in enumerate(atoms)}
    identities={(h,c):i for i,(h,n,c) in enumerate(atoms)}
    state=[-1]*len(atoms)
    try:
        for cubie in work.cubies.values():
            for normal,color in cubie.stickers.items():
                state[identities[cubie.home,color]]=slots[cubie.pos,normal]
    except KeyError:raise ValueError('bandage.entry_layout') from None
    if sorted(state)!=list(range(len(atoms))):raise ValueError('bandage.entry_layout')
    word=list(prefix)
    for base,orbit in zip(table['base'],table['transversals']):
        if cancelled and cancelled():raise InterruptedError()
        entry=orbit.get(str(state[base]))
        if entry is None:raise ValueError('bandage.state_unreachable')
        inverse=[0]*len(atoms)
        for a,b in enumerate(entry['permutation']):inverse[b]=a
        state=[inverse[x] for x in state]
        for token in reversed(entry['word']):
            word.append(token if token.endswith('2') else token[:-1] if token.endswith("'") else token+"'")
    if state!=list(range(len(atoms))):raise ValueError('bandage.state_unreachable')
    replay=cube.clone()
    for token in word:
        if cancelled and cancelled():raise InterruptedError()
        replay.apply_move(token)
    if not replay.is_solved():raise ValueError('bandage.search_replay')
    return word
