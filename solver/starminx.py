"""Restore oriented edges and pentagons, then the independent petal orbit."""
from functools import lru_cache
from pathlib import Path
import json,zlib
from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import identify,inverse_word,simplify,apply_word,piece_orbits


@lru_cache(maxsize=1)
def asset():
    return json.loads(zlib.decompress((Path(__file__).parent/'data/starminx_i_edges.bin').read_bytes()))


def solve_starminx(cube,cancel=None,progress=None):
    from solver.expanded_polyhedra import validate_expanded
    from solver.polyhedral_reduction import Transports,orbit_word,color_orbit_word
    from solver.nxn_orbits import three_cycles
    def check():
        if cancel and cancel():raise InterruptedError()
    check();validate_expanded(cube)
    if cube.is_solved():return ()
    g=cube.geometry;data=asset()
    if data.get('version')!=1 or data.get('geometry')!=geometry_key(g):
        raise ValueError('Starminx edge data does not match its mechanism')
    slots=tuple(data['slots']);local={s:i for i,s in enumerate(slots)}
    labels=identify(cube);state=[None]*len(slots)
    for home in slots:state[local[labels[home]]]=local[home]
    work=cube.entered();solution=[]
    for k,row in zip(data['base'],data['transversals']):
        check();beta=state.index(k);rec=row.get(str(beta))
        if rec is None:raise ValueError('Starminx edge state is unreachable')
        state=[state[i] for i in rec['permutation']]
        word=inverse_word(tuple(Move(*m) for m in rec['word']),5)
        for move in word:check();work.apply_move(move)
        solution.extend(word)
    if any(work.colors[s]!=g.stickers[s].face for s in slots):
        raise ValueError('Starminx edge replay failed')
    if progress:progress(1,2)
    index,orbit=next((i,o) for i,o in enumerate(piece_orbits(cube.puzzle_kind,cube.n))
                     if len(o)==60 and len(g.pieces[o[0]])==1)
    primitive=tuple(Move(*m) for m in data['centre_word']);base=tuple(data['centre_base'])
    action=apply_word(g,primitive)
    if {p for p,skin in enumerate(g.pieces) if any(action[s]!=s for s in skin)}!=set(base):
        raise ValueError('Starminx centre tool changes an outside piece')
    if any(action[g.pieces[a][0]]!=g.pieces[b][0] for a,b in zip(base,base[1:]+base[:1])):
        raise ValueError('Starminx centre tool direction is invalid')
    labels=identify(work,only=(index,));local={p:i for i,p in enumerate(orbit)};destination=[None]*len(orbit)
    for home in orbit:
        position=g.stickers[labels[g.pieces[home][0]]].piece
        destination[local[position]]=local[home]
    if three_cycles(destination):
        transports=Transports(work,orbit,base,cancel,both_directions=True)
        word=orbit_word(transports,orbit,destination,primitive,solution,search_budget=.15)
        word=color_orbit_word(work,transports,orbit,primitive,word,solution)
        for move in word:check();work.apply_move(move)
        solution.extend(word)
    if not work.is_solved():raise ValueError('Starminx complete replay failed')
    solution=simplify(solution,5);replay=cube.entered()
    for move in solution:check();replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Starminx simplified replay failed')
    if progress:progress(2,2)
    return solution
