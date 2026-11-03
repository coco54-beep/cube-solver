"""Restore the ordinary Minx core, then Brilic's three sixty-piece orbits.

Only shallow face turns are used for the core. Every extra-orbit primitive
is checked on all 360 facets, so its conjugates preserve the restored core.
"""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import PolyhedralPuzzle,Move
from solver.polyhedral import piece_orbits,identify,solve_minx,simplify,apply_word
from solver.lattice_data import geometry_key


@lru_cache(maxsize=1)
def _asset():
    return json.loads(zlib.decompress((Path(__file__).parent/'data/master_brilic_cycles.bin').read_bytes()))


def prepared_cycles(cube,targets):
    data=_asset()
    if data.get('version')!=1 or data.get('geometry')!=geometry_key(cube.geometry):
        raise ValueError('Master Brilic cycle data does not match its mechanism')
    result={}
    for index,orbit in targets.items():
        record=data['cycles'][str(index)];word=tuple(Move(*m) for m in record['word']);base=tuple(record['base'])
        if len(set(base))!=3 or not set(base)<=set(orbit):raise ValueError('Invalid Brilic cycle base')
        action=apply_word(cube.geometry,word);g=cube.geometry
        moved={p for p,slots in enumerate(g.pieces) if any(action[s]!=s for s in slots)}
        if moved!=set(base):raise ValueError('Brilic cycle changes an outside piece')
        for a,b in zip(base,base[1:]+base[:1]):
            if {action[s] for s in g.pieces[a]}!=set(g.pieces[b]):raise ValueError('Brilic cycle splits a piece')
        if any(action[action[action[s]]]!=s for s in range(len(g.stickers))):raise ValueError('Brilic cycle has a residual twist')
        result[index]=word,base
    return result


def solve_master_brilic(cube,cancel=None,progress=None):
    from solver.expanded_polyhedra import validate_expanded
    from solver.polyhedral_reduction import Transports,orbit_word,color_orbit_word
    from solver.nxn_orbits import three_cycles
    if cancel and cancel():raise InterruptedError()
    validate_expanded(cube)
    if cube.is_solved():return ()
    work=cube.entered();g=work.geometry;orbits=piece_orbits(cube.puzzle_kind,cube.n)
    core_indices={i for i,o in enumerate(orbits) if len(o) in (20,30)}
    targets={i:o for i,o in enumerate(orbits) if i not in core_indices}
    macros=prepared_cycles(work,targets)
    identify(work)
    core=PolyhedralPuzzle('megaminx',3)
    core_at={tuple(sorted(core.geometry.stickers[s].face for s in slots)):slots
             for slots in core.geometry.pieces if len(slots)>1}
    for index in core_indices:
        for p in orbits[index]:
            slots=g.pieces[p];target=core_at[tuple(sorted(g.stickers[s].face for s in slots))]
            by_face={core.geometry.stickers[s].face:s for s in target}
            for s in slots:core.colors[by_face[g.stickers[s].face]]=work.colors[s]
    solution=list(solve_minx(core,cancel,progress,optimize=False))
    for move in solution:work.apply_move(move)
    if any(work.colors[s]!=g.stickers[s].face for i in core_indices for p in orbits[i] for s in g.pieces[p]):
        raise ValueError('Master Brilic shallow core replay failed')
    for stage,(index,orbit) in enumerate(targets.items()):
        if cancel and cancel():raise InterruptedError()
        if progress:progress(stage,len(targets))
        state=identify(work,only=(index,));local={p:i for i,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            position=g.stickers[state[g.pieces[home][0]]].piece
            destination[local[position]]=local[home]
        if not three_cycles(destination):continue
        primitive,base=macros[index]
        transports=Transports(work,orbit,base,cancel,both_directions=True)
        word=orbit_word(transports,orbit,destination,primitive,solution,
                        alternatives=len(g.pieces[orbit[0]])==1,search_budget=.15)
        word=color_orbit_word(work,transports,orbit,primitive,word,solution)
        for move in word:work.apply_move(move)
        solution.extend(word)
    solution=simplify(solution,5)
    replay=cube.entered()
    for move in solution:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Master Brilic full replay failed')
    if progress:progress(1,1)
    return solution
