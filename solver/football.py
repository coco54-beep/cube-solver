"""State reduction for the 32-face Tuttminx and double-layered Rayminx."""
from functools import lru_cache
import json
from pathlib import Path
from types import SimpleNamespace
import zlib

from cube.polyhedral import Move
from solver.polyhedral import identify, inverse_word, piece_orbits, simplify
from solver.polyhedral_reduction import Transports, orbit_word
from solver.icosahedron import orientation_vector, relation_coefficients
from solver.lattice_data import geometry_key
from solver.nxn_orbits import three_cycles


def edge_orbit(cube):
    if cube.n not in (3,5):
        return None
    return next((i for i,o in enumerate(piece_orbits('football',cube.n))
                 if len(o)==30 and len(cube.geometry.pieces[o[0]])==2),None)


class EdgePositions:
    """The thirty hexagon/hexagon edge positions, without their flips."""
    def __init__(self,cube):
        g=cube.geometry
        self.puzzle_kind=cube.puzzle_kind
        self.n=cube.n
        self.orbit_index=edge_orbit(cube)
        self.originals=piece_orbits(cube.puzzle_kind,cube.n)[self.orbit_index]
        ids={p:i for i,p in enumerate(self.originals)}
        self.geometry=SimpleNamespace(spec=g.spec,
            pieces=tuple((i,) for i in range(len(ids))),
            stickers=tuple(SimpleNamespace(piece=i,face=0) for i in range(len(ids))),
            centres=tuple(g.centres[p] for p in self.originals))
        def permutation(move):
            full=g.permutation(move)
            return tuple(ids[g.stickers[full[g.pieces[p][0]]].piece]
                         for p in self.originals)
        self.geometry.permutation=permutation
        self.moves=cube.moves


def edge_units(cube):
    index=edge_orbit(cube)
    orbit=piece_orbits(cube.puzzle_kind,cube.n)[index]
    points=tuple(s for p in orbit for s in cube.geometry.pieces[p])
    ids={s:i for i,s in enumerate(points)}
    return points,{2:[tuple(ids[s] for s in cube.geometry.pieces[p]) for p in orbit]}


@lru_cache(maxsize=1)
def _assets():
    return json.loads(zlib.decompress((Path(__file__).parent/'data'/'football_cycles.bin').read_bytes()))


def _solve_football_with_beam(cube,cancel=None,progress=None):
    """Fix the outer layers with a native beam, then reduce the remainder.

    On the fifth order the beam removes about a fifth of the stickers, and the
    remaining reduction is both shorter and faster than solving the full state
    with three-cycles directly.
    """
    from solver.high_minx_reduction import native_beam
    work=cube.entered()
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    positions=[p for o in orbits if len(o)>1 for p in o]
    beam=tuple(native_beam(work,positions,cancel,progress,width=64,max_depth=40))
    remaining=cube.clone()
    remaining.colors=list(work.colors)
    tail=_solve_football(remaining,cancel,progress,improve_flips=True)
    return tuple(beam)+tuple(tail)


def solve_football(cube,cancel=None,progress=None,optimize_flips=True):
    """Keep the shortest verified solve; never longer than the plain baseline."""
    import logging
    baseline=_solve_football(cube,cancel,progress)
    best=baseline
    if cube.n==5:
        try:
            candidate=_solve_football_with_beam(cube,cancel,progress)
        except InterruptedError:
            raise
        except Exception as exc:
            logging.getLogger(__name__).warning('Football beam solve rejected: %s',exc)
            candidate=None
        if candidate is not None and len(candidate)<len(best):
            check=cube.entered()
            for i,move in enumerate(candidate):
                if i%128==0 and cancel and cancel():
                    raise InterruptedError()
                check.apply_move(move)
            if check.is_solved():
                best=candidate
    # The beam candidate already uses the improved flip tail, so the separate
    # flip plan is only worth running when the beam did not win.
    if optimize_flips and best and best is baseline:
        try:
            improved=_solve_football(cube,cancel,progress,improve_flips=True)
        except InterruptedError:
            raise
        except Exception as exc:
            logging.getLogger(__name__).warning('Football flip optimization rejected: %s',exc)
            improved=None
        if improved is not None and len(improved)<len(best):
            best=improved
    return best


def _solve_football(cube,cancel=None,progress=None,improve_flips=False):
    if cancel and cancel():
        raise InterruptedError()
    work=cube.entered()
    g=work.geometry
    record=_assets().get(str(cube.n))
    if record is None or record['geometry']!=geometry_key(g):
        raise ValueError('The Tuttminx solver assets do not match this model')
    identify(work)
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    core=edge_orbit(work)
    expected={i for i,orbit in enumerate(orbits) if len(orbit)>1 and i!=core}
    if {int(index) for index in record.get('cycles',{})}!=expected or (
        core is not None and not all(key in record for key in ('edge_cycle','edge_flips'))):
        raise ValueError('The Tuttminx solver assets do not match this model')
    solution=[]
    def execute(word):
        for i,move in enumerate(word):
            if i%128==0 and cancel and cancel():
                raise InterruptedError()
            work.apply_move(move)
        solution.extend(word)
    def reduce_orbit(index,macro):
        if cancel and cancel():
            raise InterruptedError()
        orbit=orbits[index]
        labeled=identify(work)
        ids={p:i for i,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            position=g.stickers[labeled[g.pieces[home][0]]].piece
            destination[ids[position]]=ids[home]
        cycles=three_cycles(destination)
        if not cycles:
            return
        primitive=tuple(Move(*m) for m in macro['word'])
        transports=Transports(work,orbit,tuple(macro['base']),cancel,both_directions=True)
        execute(orbit_word(transports,orbit,destination,primitive,solution,
                           alternatives=len(g.pieces[orbit[0]])==1))

    if core is not None:
        reduce_orbit(core,record['edge_cycle'])
        points,units=edge_units(work)
        ids={s:i for i,s in enumerate(points)}
        full=identify(work)
        flips=orientation_vector(tuple(ids[full[s]] for s in points),units)[2]
        relations=record['edge_flips']
        coefficients=relation_coefficients(flips,relations,2)
        flip_word=simplify((Move(*m) for coefficient,relation in zip(coefficients,relations)
                            if coefficient for m in relation['word']),g.spec.turn_order)
        if improve_flips:
            from solver.football_flips import paired_flip_word
            candidate=paired_flip_word(work,record,flips,cancel)
            if candidate is None or len(candidate)>=len(flip_word):
                return None
            flip_word=candidate
        execute(flip_word)

    for stage,index in enumerate(record.get('order') or [int(i) for i in record['cycles']]):
        if progress:
            progress(stage,len(record['cycles']))
        reduce_orbit(int(index),record['cycles'][str(index)])
    if not work.is_solved():
        raise ValueError('Tuttminx reduction replay failed')
    return simplify(solution,15)
