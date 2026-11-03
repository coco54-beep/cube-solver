"""Staged, history-independent restoration of the Bauhinia's regular state."""
from functools import lru_cache
from pathlib import Path
from collections import deque
import json
import zlib
from cube.polyhedral import Move
from solver.polyhedral import identify,piece_orbits,apply_word,simplify,_parity
from solver.lattice_data import geometry_key


@lru_cache(maxsize=2)
def prepared(kind='mf8_bauhinia_minx',n=3):
    from cube.polyhedral import PolyhedralPuzzle
    cube=PolyhedralPuzzle(kind,n);g=cube.geometry
    data=json.loads(zlib.decompress((Path(__file__).parent/'data'/(kind+'_cycles.bin')).read_bytes()))
    if data.get('version')!=1 or data.get('geometry')!=geometry_key(g):
        raise ValueError('Bauhinia formula data does not match its geometry')
    orbits=piece_orbits(cube.puzzle_kind,n)
    prior={s for o in orbits if len(o)==1 for p in o for s in g.pieces[p]}
    if sorted(data['order'])!=[i for i,o in enumerate(orbits) if len(o)>1]:raise ValueError('Incomplete curved-cap stages')
    macros={}
    for i in data['order']:
        row=data['cycles'][str(i)];word=tuple(Move(*m) for m in row['word']);base=tuple(row['base'])
        if len(set(base))!=3 or not set(base)<=set(orbits[i]):raise ValueError('Invalid Bauhinia cycle')
        action=apply_word(g,word)
        if any(action[s]!=s for s in prior):raise ValueError('Bauhinia cycle changes a completed stage')
        changed={p for p in orbits[i] if any(action[s]!=s for s in g.pieces[p])}
        if changed!=set(base):raise ValueError('Bauhinia cycle changes extra target pieces')
        for a,b in zip(base,base[1:]+base[:1]):
            if {action[s] for s in g.pieces[a]}!=set(g.pieces[b]):raise ValueError('Bauhinia cycle splits a piece')
        target=[s for p in orbits[i] for s in g.pieces[p]]
        if any(action[action[action[s]]]!=s for s in target):raise ValueError('Bauhinia cycle leaves a residual twist')
        prior.update(target);macros[i]=word,base
    flip=data['edge_flip'];word=tuple(Move(*m) for m in flip['word']);base=tuple(flip['base'])
    edges=next(o for o in orbits if len(o)==30 and len(g.pieces[o[0]])==2);action=apply_word(g,word)
    changed={p for p in edges if any(action[s]!=s for s in g.pieces[p])}
    if len(base)!=2 or changed!=set(base) or any(g.stickers[action[s]].piece!=p for p in edges for s in g.pieces[p]):
        raise ValueError('Bauhinia edge orientation formula is not a two-edge flip')
    return tuple(data['order']),macros,word,base


@lru_cache(maxsize=2)
def flip_paths(kind='mf8_bauhinia_minx',n=3):
    from cube.polyhedral import PolyhedralPuzzle
    cube=PolyhedralPuzzle(kind,n);g=cube.geometry
    _,_,_,base=prepared(kind,n);root=tuple(sorted(base));paths={root:()};queue=deque([root])
    actions=[]
    for atom in cube.moves():
        for amount in (1,2):
            move=Move(atom.axis,atom.layer,amount);p=g.permutation(move)
            actions.append((move,tuple(g.stickers[p[slots[0]]].piece for slots in g.pieces)))
    while queue:
        state=queue.popleft()
        for move,point in actions:
            child=tuple(sorted(point[p] for p in state))
            if child not in paths:paths[child]=paths[state]+(move,);queue.append(child)
    if len(paths)!=30*29//2:raise ValueError('Bauhinia edge flips do not cover every pair')
    return paths


def validate(cube):
    """Check the complete regular group invariants without doing a search."""
    g=cube.geometry;state=identify(cube)
    for orbit in piece_orbits(cube.puzzle_kind,3):
        local={p:i for i,p in enumerate(orbit)}
        points=[local[g.stickers[state[g.pieces[h][0]]].piece] for h in orbit]
        if _parity(points):raise ValueError('rex.error.orbit_parity')
        if len(g.pieces[orbit[0]])==2:
            flips=sum(state[g.pieces[h][0]]!=g.pieces[g.stickers[state[g.pieces[h][0]]].piece][0] for h in orbit)
            if flips%2:raise ValueError('rex.error.edge_flip')
    return state


def solve(cube,cancel=None,progress=None):
    from solver.polyhedral_reduction import Transports,orbit_word,color_orbit_word
    from solver.polyhedral import inverse_word
    if cancel and cancel():raise InterruptedError()
    work=cube.entered();g=work.geometry;orbits=piece_orbits(cube.puzzle_kind,3)
    validate(work)
    if work.is_solved():return ()
    order,macros,flip_word,flip_base=prepared(cube.puzzle_kind,cube.n);solution=[];finished=[]
    for stage,i in enumerate(order):
        if cancel and cancel():raise InterruptedError()
        if progress:progress(stage,len(order))
        orbit=orbits[i];state=identify(work,only=(i,));local={p:j for j,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            position=g.stickers[state[g.pieces[home][0]]].piece
            destination[local[position]]=local[home]
        if _parity(destination):raise ValueError('rex.error.orbit_parity')
        if destination!=list(range(len(orbit))):
            primitive,base=macros[i];transport=Transports(work,orbit,base,cancel,both_directions=True)
            word=orbit_word(transport,orbit,destination,primitive,solution,
                            alternatives=len(g.pieces[orbit[0]])==1,search_budget=.04)
            if len(g.pieces[orbit[0]])==1:
                word=color_orbit_word(work,transport,orbit,primitive,word,solution,budget=.08)
            for move in word:
                if cancel and cancel():raise InterruptedError()
                work.apply_move(move)
            solution.extend(word)
        if len(g.pieces[orbit[0]])==2:
            flipped=[p for p in orbit if any(work.colors[s]!=g.stickers[s].face for s in g.pieces[p])]
            if len(flipped)%2:raise ValueError('rex.error.edge_flip')
            for a,b in zip(flipped[::2],flipped[1::2]):
                path=flip_paths(cube.puzzle_kind,cube.n)[tuple(sorted((a,b)))];word=inverse_word(path,3)+flip_word+path
                for move in word:
                    if cancel and cancel():raise InterruptedError()
                    work.apply_move(move)
                solution.extend(word)
        finished.extend(s for p in orbit for s in g.pieces[p])
        if any(work.colors[s]!=g.stickers[s].face for s in finished):
            raise ValueError('Bauhinia stage replay does not match the entered state')
    solution=simplify(solution,3);replay=cube.entered()
    for move in solution:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Bauhinia full replay failed')
    if progress:progress(len(order),len(order))
    return solution
