"""Solve colours and visible centre direction; ignore invisible square twists."""
from functools import lru_cache
import json
from pathlib import Path
import zlib

from cube.mastermorphix import IDENTITY
from cube.mirror_tower import frame_key
from cube.mirror_pyraminx import placements
from cube.polyhedral import Move
from cube.fisher_skewb import appearance
from solver.lattice_data import geometry_key
from solver.polyhedral import simplify


@lru_cache(maxsize=1)
def prepared():
    return json.loads(zlib.decompress((Path(__file__).parent/'data/fisher_skewb.bin').read_bytes()))


def solve_fisher_skewb(cube,cancel=None,progress=None):
    if cancel and cancel(): raise InterruptedError()
    cube.labeled_state()
    if cube.is_solved(): return ()
    from solver.polyhedral import solve_polyhedral
    prefix=tuple(solve_polyhedral(cube.ordinary_state(),cancel,progress))
    residual=cube.clone()
    for move in prefix:
        if cancel and cancel(): raise InterruptedError()
        residual.apply_move(move)
    if residual.is_solved(): return prefix
    record=prepared()
    if record['geometry']!=geometry_key(cube.geometry):
        raise ValueError('Fisher Skewb formulas do not match its mechanism')
    mask=0
    invisible=0
    for bit,h in enumerate(record['homes']):
        piece=residual.pieces[h]
        if piece.home!=h: raise ValueError('Fisher Skewb centre is misplaced')
        if frame_key(piece.frame)!=frame_key(IDENTITY): mask |= 1<<bit
        if len({appearance(h,f) for f in placements(3,h,h,'skewb')})==1:
            invisible |= 1<<bit
    candidates=[]
    for key,atoms in record['finishers'].items():
        if (int(key)^mask)&~invisible: continue
        word=tuple(Move(*m) for m in atoms)
        candidates.append(simplify(prefix+word,3))
    if not candidates:
        raise ValueError('Fisher Skewb centre directions violate the turn constraints')
    solution=min(candidates,key=len)
    replay=cube.clone()
    for move in solution:
        if cancel and cancel(): raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved(): raise ValueError('Fisher Skewb solution replay failed')
    return solution
