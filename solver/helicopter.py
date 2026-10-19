"""Solve entered Helicopter Cube colours with regular 180-degree edge turns."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.polyhedral import Move
from solver.lattice_data import geometry_key
from solver.polyhedral import compose, identify, inverse, inverse_word, simplify, piece_orbits, _parity


@lru_cache(maxsize=1)
def prepared():
    return json.loads(zlib.decompress((Path(__file__).parent/'data/helicopter.bin').read_bytes()))


def solve_helicopter(cube, cancel=None, progress=None):
    if cancel and cancel():
        raise InterruptedError()
    record=prepared()
    if record['geometry'] != geometry_key(cube.geometry):
        raise ValueError('Helicopter solver data do not match the model')
    full=identify(cube)
    points=tuple(record['points'])
    index={s:i for i,s in enumerate(points)}
    state=tuple(index[full[s]] for s in points)
    word=[]
    centre_points=record['centre_points']
    for k in range(len(state)-1,centre_points-1,-1):
        if cancel and cancel():
            raise InterruptedError()
        if state[k]!=k:
            entry=record['stages'][k].get(str(state[k]))
            if entry is None:
                raise ValueError('Helicopter state requires jumbling or violates turn constraints')
            state=compose(state,inverse(tuple(entry['permutation'])))
            word.extend(inverse_word(tuple(Move(*m) for m in entry['word']),2))
        if progress:
            progress(len(state)-k,len(state)-centre_points+4)
    work=cube.entered()
    for move in word:
        if cancel and cancel():
            raise InterruptedError()
        work.apply_move(move)
    orbits=piece_orbits('helicopter',3)
    centres={i:o for i,o in enumerate(orbits) if len(cube.geometry.pieces[o[0]])==1}
    signature=0
    for bit,orbit in enumerate(centres.values()):
        ids=tuple(index[cube.geometry.pieces[p][0]] for p in orbit)
        local={s:i for i,s in enumerate(ids)}
        signature |= _parity([local[state[s]] for s in ids]) << bit
    parity=record['parity'].get(str(signature))
    if parity is None:
        raise ValueError('Helicopter state requires jumbling or violates turn constraints')
    for atom in parity:
        if cancel and cancel():
            raise InterruptedError()
        move=Move(*atom)
        work.apply_move(move)
        word.append(move)
    from solver.polyhedral_reduction import Transports, orbit_word
    for stage,(orbit_id,orbit) in enumerate(centres.items()):
        if cancel and cancel():
            raise InterruptedError()
        full=identify(work,only={orbit_id})
        local={piece:i for i,piece in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            pos=work.geometry.stickers[full[work.geometry.pieces[home][0]]].piece
            destination[local[pos]]=local[home]
        macro=record['cycles'][str(orbit_id)]
        primitive=tuple(Move(*m) for m in macro['word'])
        transports=Transports(work,orbit,tuple(macro['base']),cancel,both_directions=True)
        addition=orbit_word(transports,orbit,destination,primitive,word,search_budget=.02)
        for move in addition:
            if cancel and cancel():
                raise InterruptedError()
            work.apply_move(move)
        word.extend(addition)
        if progress:
            progress(len(state)-centre_points+stage+1,len(state)-centre_points+4)
    solution=simplify(word,2)
    replay=cube.entered()
    for move in solution:
        if cancel and cancel():
            raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('Helicopter solution replay failed')
    return solution
