"""Bounded fast search modulo the always-legal half-cube rotation group.

Every physical brick stays in one mechanical octant. Half-cube turns move
octants rigidly and act faithfully on the eight corner owners. Fixing those
corners gives a unique representative of each half-turn orbit. The shortcut
uses a subset of quotient edges; failure always returns to complete search.
"""
from functools import lru_cache
import heapq
from time import monotonic

from cube.appearance import ROTATIONS
from cube.cuboid import layout,transform,multiply,IDENTITY


def octant(point):
    return (point[0]>0)*4+(point[1]>0)*2+(point[2]>0)


@lru_cache(maxsize=1)
def model(kind='camouflage_3'):
    return OctantModel(kind)


class OctantModel:
    def __init__(self,kind='camouflage_3'):
        self.kind=kind
        from solver.cuboid_search import search_model,packed_actions,pattern_tables
        self.atoms,self.transitions,_,goals,_,self.aliases=search_model(kind)
        self.masks,self.actions=packed_actions(kind)
        self.goals=tuple(frozenset((p%8)*24+f for f in row) for p,row in enumerate(goals))
        cells=layout(kind)[0]
        self.corners=tuple((p,next(c for c in group if all(abs(v)==3 for v in c)))
                           for p,group in enumerate(cells) if any(all(abs(v)==3 for v in c) for c in group))
        assert len(self.corners)==8
        anchor=max(range(len(cells)),key=lambda p:len(cells[p]))
        corner=next(c for p,c in self.corners if p==anchor)
        from cube.polyhedral import CUBE
        self.inner_faces=tuple(a if sum(v*w for v,w in zip(CUBE[a],corner))<0 else a+3
                               for a in range(3))
        self.octants=tuple(tuple(octant(transform(frame,group[0])) for frame in ROTATIONS) for group in cells)
        indices={frame:i for i,frame in enumerate(ROTATIONS)}
        self.inverse=tuple(indices[tuple(zip(*f))] for f in ROTATIONS)
        self.product=tuple(tuple(indices[multiply(a,b)] for b in ROTATIONS) for a in ROTATIONS)
        self.at={m:i for i,m in enumerate(self.atoms)}
        self.patterns=pattern_tables(kind)
        occupied={cell for p,corner in self.corners for cell in cells[p]}
        corner_owners={p for p,corner in self.corners}
        self.feasible=tuple(tuple([self.aliases[p][indices[IDENTITY]]] if p in corner_owners else
                                  [pose for pose,frame in enumerate(ROTATIONS)
                                   if not occupied.intersection(transform(frame,c) for c in group)])
                            for p,group in enumerate(cells))

    def signature(self,tables):
        return bytes(tables[p//8][(p%8)*24+pose] for p,row in enumerate(self.feasible) for pose in row)

    def canonical(self,state):
        frames=[value-(p%8)*24 for p,value in enumerate(state)]
        inverse_at=[None]*8
        for p,corner in self.corners:
            inverse_at[self.octants[p][frames[p]]]=self.inverse[frames[p]]
        if any(v is None for v in inverse_at):raise ValueError('cuboid.identity_unreachable')
        return bytes((p%8)*24+self.aliases[p][self.product[inverse_at[self.octants[p][f]]][f]]
                     for p,f in enumerate(frames))

    def turn(self,state,index):
        from solver.cuboid_search import packed_turn
        if any(not self.masks[p][f]&(1<<index) for p,f in enumerate(state)):return None
        return packed_turn(state,self.actions[index])

    @lru_cache(maxsize=32768)
    def score(self,state):
        from solver.camouflage_octants import quotient_patterns
        try:patterns=quotient_patterns(self.kind)
        except FileNotFoundError:patterns=None
        if patterns is not None:
            total=0
            for positions,distances in patterns:
                index=0
                for p,radix,lookup in positions:
                    value=lookup[state[p]]
                    if value==255:return 1000000
                    index=index*radix+value
                value=distances[index]
                if value==255:return 1000000
                total+=value
            return total
        total=0
        for pieces,distances,packed in self.patterns:
            index=0
            for p in pieces:index=index*24+state[p]-(p%8)*24
            value=(distances[index//2]>>(4*(index%2)))&15 if packed else distances[index]
            if value==(15 if packed else 255):return 1000000
            total+=value
        return total+2*sum(f not in self.goals[p] for p,f in enumerate(state))

    @lru_cache(maxsize=256)
    def corner_word(self,corner_poses):
        from solver.cuboid_search import camouflage_anchor
        from solver.camouflage_octants import corner_table,corner_permutation
        identity=ROTATIONS.index(IDENTITY)
        proxy=bytearray((p%8)*24+a[identity] for p,a in enumerate(self.aliases))
        for (p,corner),pose in zip(self.corners,corner_poses):proxy[p]=(p%8)*24+pose
        aligned,prefix,_=camouflage_anchor(bytes(proxy),kind=self.kind)
        state=corner_permutation(self,tuple(aligned[p]-(p%8)*24 for p,c in self.corners))
        table=corner_table(self.kind);word=[self.at[m] for m in prefix]
        for base,orbit in zip(table['base'],table['transversals']):
            entry=orbit.get(str(state[base]))
            if entry is None:raise ValueError('cuboid.identity_unreachable')
            inverse=[0]*24
            for a,b in enumerate(entry['permutation']):inverse[b]=a
            state=tuple(inverse[i] for i in state)
            word.extend(self.at[self.atoms[i].inverse(4)] for i in reversed(entry['word']))
        if state!=tuple(range(24)):raise ValueError('cuboid.identity_unreachable')
        return tuple(word)

    def correction(self,state):
        poses=tuple(state[p]-(p%8)*24 for p,corner in self.corners)
        return self.corner_word(poses)


def solve_octants(original,cancel=None,seconds=2.,maximum=12000,stats=None):
    """Return a verified physical word, or None when this shortcut runs out."""
    from solver.cuboid_search import packed_turn
    from solver.cuboid_static import normalize
    from solver.camouflage_octants import catalogue
    if cancel and cancel():raise InterruptedError()
    begun=monotonic();deadline=begun+seconds;g=model(original.puzzle_kind);cube=normalize(original,cancel)
    at={f:i for i,f in enumerate(ROTATIONS)}
    raw=bytes((p%8)*24+g.aliases[p][at[f]] for p,f in enumerate(cube.frames))
    root=g.canonical(raw);records=[(root,-1,(),0)];best={root:0};queue=[(g.score(root),0,0)]
    macro_words,macro_actions,macro_masks,header=catalogue(original.puzzle_kind)
    nodes=0;found=None
    while queue and monotonic()<deadline:
        if cancel and cancel():raise InterruptedError()
        _,depth,index=heapq.heappop(queue);state,parent,edge,depth=records[index]
        if best.get(state)!=depth:continue
        nodes+=1
        if all(f in g.goals[p] for p,f in enumerate(state)):found=index;break
        candidates={};mask=(1<<len(macro_words))-1
        for p,f in enumerate(state):mask&=macro_masks[p][f]
        while mask:
            bit=mask&-mask;mask^=bit;move=bit.bit_length()-1
            child=packed_turn(state,macro_actions[move])
            if child!=state and best.get(child,maximum)>depth+1:
                candidates.setdefault(child,macro_words[move])
        ranked=heapq.nsmallest(32,((g.score(child),len(edge),child,edge) for child,edge in candidates.items()))
        for value,_,child,edge in ranked:
            best[child]=depth+1;records.append((child,index,edge,depth+1))
            heapq.heappush(queue,(value+depth+1,depth+1,len(records)-1))
            if value==0 and all(f in g.goals[p] for p,f in enumerate(child)):
                found=len(records)-1;break
            if len(records)>=maximum:break
        if found is not None:break
        if len(records)>=maximum:break
    if stats is not None:stats.update(nodes=nodes,records=len(records),search_seconds=monotonic()-begun)
    if found is None:return None
    chunks=[];index=found
    while records[index][1]>=0:
        state,parent,edge,depth=records[index];chunks.append((edge,state));index=parent
    word=[];current=raw
    def append(indices):
        nonlocal current
        for index in indices:
            if cancel and cancel():raise InterruptedError()
            current=g.turn(current,index)
            if current is None:raise ValueError('cuboid.replay_failed')
            word.append(g.atoms[index])
    append(g.correction(current))
    if current!=root:raise ValueError('cuboid.replay_failed')
    for edge,target in reversed(chunks):
        append(edge)
        if current!=target:raise ValueError('cuboid.replay_failed')
    replay=original.clone()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('cuboid.replay_failed')
    if stats is not None:stats.update(seconds=monotonic()-begun,moves=len(word))
    return tuple(word)
