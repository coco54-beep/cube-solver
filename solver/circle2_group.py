"""Colour-state group solver for Circle 2 and the eight fixed planet masks.

A turn containing the anchor carries the hidden core. Once the labelled
anchor corner is oriented, the three opposite turns act like ordinary
corner/edge turns. No scramble witness or runtime symbolic package is used.
"""
from collections import Counter, deque
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import zlib
from time import monotonic

from cube.circle_cube import Circle2Cube
from cube.polyhedral import Move, PolyhedralPuzzle


def fingerprint(kind='circle_2'):
    cube=Circle2Cube() if kind=='circle_2' else PolyhedralPuzzle(kind,3);g=cube.geometry
    data=(g.pieces,tuple(s.face for s in g.stickers),
          tuple(g.permutation(Move(a,0,1)) for a in range(6)))
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=2)
def table(kind='circle_2'):
    filename='circle2_group.bin' if kind=='circle_2' else kind+'_group.bin'
    try:data=json.loads(zlib.decompress((Path(__file__).parent/'data'/filename).read_bytes()))
    except (OSError,ValueError,zlib.error):raise ValueError('circle2.table_missing') from None
    if data.get('version')!=1 or data.get('kind')!=kind or data.get('geometry')!=fingerprint(kind):
        raise ValueError('circle2.table_version')
    return data


def normalize(cube,cancel=None):
    def corner(state):
        for slots in state.geometry.pieces:
            if len(slots)==3 and {state.colors[i] for i in slots}=={3,4,5}:
                return tuple(sorted((state.geometry.stickers[i].face,state.colors[i]) for i in slots))
        raise ValueError('circle.count_error')
    root=cube.entered();pending=deque([(root,())]);seen={corner(root)}
    target=((3,3),(4,4),(5,5))
    while pending:
        if cancel and cancel():raise InterruptedError()
        state,word=pending.popleft()
        if corner(state)==target:return state,word
        for axis,normal in enumerate(state.geometry.spec.axes):
            a,sign=next((a,v) for a,v in enumerate(normal) if v)
            if state.anchor[a]!=sign:continue
            for amount in (1,2,3):
                move=Move(axis,0,amount);child=state.clone();child.apply_move(move)
                key=corner(child)
                if key not in seen:seen.add(key);pending.append((child,word+(move,)))
    raise ValueError('circle.count_error')


def solve_circle_group(cube,cancel=None,progress=None):
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    work,prefix=normalize(cube,cancel) if cube.puzzle_kind=='circle_2' else (cube.entered(),())
    data=table(cube.puzzle_kind);wanted=tuple(s.face for s in work.geometry.stickers)
    if Counter(work.colors)!=Counter(wanted):raise ValueError('circle.count_error')
    # The hidden edges have opposite-colour caps: four pieces share each
    # pair. Their labels cannot be recovered from paint. Sift the coloured
    # state through the complete subgroup instead of inventing identities.
    begun=monotonic();seen=set();nodes=0
    def visit(level,state):
        nonlocal nodes
        if cancel and cancel():raise InterruptedError()
        nodes+=1
        if monotonic()-begun>20 or nodes>20000:raise ValueError('circle.search_limit')
        if state==wanted:return ()
        if level==len(data['base']) or (level,state) in seen:return None
        if len(seen)<12000:seen.add((level,state))
        base=data['base'][level];following=[]
        for beta,entry in data['transversals'][level].items():
            if state[int(beta)]!=wanted[base]:continue
            child=tuple(state[i] for i in entry['permutation'])
            following.append((sum(a!=b for a,b in zip(child,wanted)),len(entry['word']),int(beta),child,entry))
        for _,_,beta,child,entry in sorted(following):
            tail=visit(level+1,child)
            if tail is not None:return (entry,)+tail
        return None
    factors=visit(0,tuple(work.colors))
    if factors is None:raise ValueError('circle.state_unreachable')
    word=list(prefix)
    for entry in factors:word.extend(Move(a,l,-n%4) for a,l,n in reversed(entry['word']))
    if progress:progress(1,1)
    from solver.polyhedral import simplify
    replay=cube.entered();short=[]
    def key(state):return bytes(state.colors),getattr(state,'anchor',None)
    visited={key(replay):0};checkpoints=[key(replay)]
    for move in simplify(word,4):
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
        state=key(replay);previous=visited.get(state)
        if previous is not None:
            for old in checkpoints[previous+1:]:visited.pop(old,None)
            del checkpoints[previous+1:];del short[previous:]
        else:
            short.append(move);visited[state]=len(short);checkpoints.append(state)
    if not replay.is_solved():raise ValueError('circle.replay_failed')
    # Erased loops have identical paint and mechanism state, including the
    # travelling Circle 2 anchor. Verify the final shortened word as well.
    replay=cube.entered();word=simplify(short,4)
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('circle.replay_failed')
    return tuple(word)


solve_circle2=solve_circle_group
