"""Reduction for Icosamate, Astrominx, Elite and Royal Icosamate."""
from functools import lru_cache
import json
import math
import random
from pathlib import Path
from types import SimpleNamespace
import zlib

from cube.polyhedral import Move, PolyhedralPuzzle, rotate, dot, unit
from solver.polyhedral import (apply_word, identify, inverse_word,
                              piece_orbits, simplify)
from solver.polyhedral_reduction import Transports, orbit_word
from solver.lattice_data import geometry_key
from solver.nxn_orbits import three_cycles


def core_points(cube):
    g=cube.geometry
    return tuple(s for orbit in piece_orbits(cube.puzzle_kind,cube.n)
                 if len(orbit)!=60 for piece in orbit for s in g.pieces[piece])


class PositionModel:
    """Project core moves to whole-piece positions for formula generation."""
    def __init__(self,cube):
        g=cube.geometry
        self.puzzle_kind=cube.puzzle_kind
        self.n=cube.n
        self.originals=tuple(piece for orbit in piece_orbits(cube.puzzle_kind,cube.n)
                             if len(orbit)!=60 for piece in orbit)
        ids={piece:i for i,piece in enumerate(self.originals)}
        self.geometry=SimpleNamespace(spec=g.spec,
                                      pieces=tuple((i,) for i in range(len(ids))),
                                      stickers=tuple(SimpleNamespace(piece=i,face=0) for i in range(len(ids))),
                                      centres=tuple(g.centres[p] for p in self.originals))
        def permutation(move):
            full=g.permutation(move)
            return tuple(ids[g.stickers[full[g.pieces[p][0]]].piece] for p in self.originals)
        self.geometry.permutation=permutation
        self.moves=cube.moves

    def targets(self):
        ids={p:i for i,p in enumerate(self.originals)}
        return {i:tuple(ids[p] for p in orbit) for i,orbit in
                enumerate(piece_orbits(self.puzzle_kind,self.n)) if len(orbit)!=60}


def orientation_units(cube,points):
    """Order each core corner cyclically and each central edge as a pair."""
    g=cube.geometry
    ids={s:i for i,s in enumerate(points)}
    result={5:[],2:[]}
    for orbit in piece_orbits(cube.puzzle_kind,cube.n):
        if len(orbit)==60:
            continue
        for piece in orbit:
            slots=g.pieces[piece]
            if len(slots)==5:
                axis=unit(g.centres[piece])
                current=slots[0]
                cycle=[]
                for _ in range(5):
                    cycle.append(ids[current])
                    direction=rotate(g.spec.normals[g.stickers[current].face],axis,2*math.pi/5)
                    current=max(slots,key=lambda s:dot(direction,g.spec.normals[g.stickers[s].face]))
                if len(set(cycle))!=5 or current!=slots[0]:
                    raise ValueError('Invalid Icosamate corner frame')
                result[5].append(tuple(cycle))
            elif len(slots)==2:
                result[2].append(tuple(ids[s] for s in slots))
    return result


def orientation_vector(permutation,units):
    result={}
    for prime,cycles in units.items():
        values=[]
        for cycle in cycles:
            if permutation[cycle[0]] not in cycle:
                raise ValueError('Position must be restored before adjusting orientation')
            shift=cycle.index(permutation[cycle[0]])
            if any(permutation[s]!=cycle[(i+shift)%prime] for i,s in enumerate(cycle)):
                raise ValueError('Mirrored or impossible core orientation')
            values.append(shift)
        result[prime]=tuple(values)
    return result


def independent_relation(vector,basis,prime):
    row=list(vector)
    for pivot,known in sorted(basis.items()):
        factor=row[pivot]
        if factor:
            row=[(a-factor*b)%prime for a,b in zip(row,known)]
    pivot=next((i for i,v in enumerate(row) if v),None)
    if pivot is None:
        return False
    scale=pow(row[pivot],-1,prime)
    basis[pivot]=tuple(v*scale%prime for v in row)
    return True


def relation_coefficients(target,relations,prime):
    basis={}
    width=len(relations)
    for index,relation in enumerate(relations):
        row=list(relation['vector'])
        coefficients=[int(i==index) for i in range(width)]
        for pivot,(known,combination) in sorted(basis.items()):
            factor=row[pivot]
            row=[(a-factor*b)%prime for a,b in zip(row,known)]
            coefficients=[(a-factor*b)%prime for a,b in zip(coefficients,combination)]
        pivot=next((i for i,v in enumerate(row) if v),None)
        if pivot is not None:
            scale=pow(row[pivot],-1,prime)
            basis[pivot]=(tuple(v*scale%prime for v in row),
                          tuple(v*scale%prime for v in coefficients))
    row=list(target)
    result=[0]*width
    for pivot,(known,combination) in sorted(basis.items()):
        factor=row[pivot]
        row=[(a-factor*b)%prime for a,b in zip(row,known)]
        result=[(a+factor*b)%prime for a,b in zip(result,combination)]
    if any(row):
        raise ValueError('The entered core violates an orientation constraint')
    return result


@lru_cache(maxsize=1)
def _cycles():
    return json.loads((Path(__file__).parent/'data'/'icosahedron_cycles.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _cores():
    data=(Path(__file__).parent/'data'/'icosahedron_core.bin').read_bytes()
    return json.loads(zlib.decompress(data))


@lru_cache(maxsize=1)
def _edge_data():
    try:
        data=(Path(__file__).parent/'data'/'icosahedron_edges.bin').read_bytes()
        return json.loads(zlib.decompress(data))
    except (OSError,ValueError):
        return {}


@lru_cache(maxsize=8)
def _edge_generators(order):
    """Short conjugate words that span the mod-2 edge-flip kernel.

    Conjugating every stored edge-orientation relation by each legal turn gives
    a heavily overcomplete set of kernel words. The stored basis needs about
    fifteen of its long words for a typical target; because the kernel has
    dimension twenty-nine, this conjugate set has a large null space and a
    target can instead be written as a handful of the conjugates. The set is
    bundled by ``scripts/build_icosahedron_edges.py``; if it is missing, the
    same words are rebuilt from the stored relations.
    """
    cube=PolyhedralPuzzle('icosahedron',order)
    g=cube.geometry
    record=_edge_data().get(str(order))
    if record is not None and record.get('geometry')==geometry_key(g):
        return {int(key):(len(word),tuple(Move(*move) for move in word))
                for key,word in record['generators']}
    points=core_points(cube)
    ids={s:i for i,s in enumerate(points)}
    units=orientation_units(cube,points)
    core=_cores()[str(order)]
    atoms=tuple(Move(m.axis,m.layer,p*g.spec.step(m.axis))
                for m in cube.moves() for p in range(1,g.spec.order(m.axis)))
    generators={}
    for relation in core['relations']['2']:
        base=tuple(Move(*m) for m in relation['word'])
        for atom in (None,)+atoms:
            word=base if atom is None else simplify((atom.inverse(5),)+base+(atom,),5)
            full=apply_word(g,word)
            permutation=tuple(ids[full[s]] for s in points)
            try:
                vector=orientation_vector(permutation,units)[2]
            except ValueError:
                continue
            if not any(vector):
                continue
            key=0
            for i,value in enumerate(vector):
                key|=(value&1)<<i
            current=generators.get(key)
            if current is None or len(word)<current[0]:
                generators[key]=(len(word),word)
    return generators


def _sparse_edge_orientation(target,order,limit=900):
    """Express a mod-2 target as a few conjugate words using a meet in middle.

    Pairs of generator words are tabulated, so any target that is a sum of up
    to four generators is found by one lookup plus one scan. Returns None when
    no representation within the tabulated weight exists, in which case the
    caller falls back to the stored basis.
    """
    generators=_edge_generators(order)
    if not generators:
        return None
    items=sorted(generators.items(),key=lambda entry:entry[1][0])
    if len(items)>limit:
        items=items[:limit]
        # Keep every stored basis vector so the retained subset still spans the
        # whole kernel; otherwise some targets could never be represented here.
        present={key for key,_ in items}
        core=_cores().get(str(order))
        for relation in core['relations']['2'] if core else ():
            key=0
            for i,value in enumerate(relation['vector']):
                key|=(value&1)<<i
            if key not in present and key in generators:
                items.append((key,generators[key]))
                present.add(key)
    vecs=[entry[0] for entry in items]
    lengths=[entry[1][0] for entry in items]
    words=[entry[1][1] for entry in items]
    goal=0
    for i,value in enumerate(target):
        goal|=(value&1)<<i
    table={}
    size=len(vecs)
    for i in range(size):
        table.setdefault(vecs[i],(lengths[i],(i,)))
    for i in range(size):
        vi=vecs[i]
        li=lengths[i]
        for j in range(i+1,size):
            key=vi^vecs[j]
            cost=li+lengths[j]
            current=table.get(key)
            if current is None or cost<current[0]:
                table[key]=(cost,(i,j))
    goal_hit=table.get(goal)
    best=goal_hit[0] if goal_hit else None
    choice=goal_hit[1] if goal_hit else None
    for key,(cost,combination) in table.items():
        other=table.get(goal^key)
        if other is None:
            continue
        if set(combination)&set(other[1]):
            continue
        total=cost+other[0]
        if best is None or total<best:
            best=total
            choice=combination+other[1]
    if choice is None:
        return None
    return [words[i] for i in choice]


@lru_cache(maxsize=1)
def _twist_data():
    try:
        data=(Path(__file__).parent/'data'/'icosahedron_twists.bin').read_bytes()
        return json.loads(zlib.decompress(data))
    except (OSError,ValueError):
        return {}


@lru_cache(maxsize=8)
def _twist_generators(order):
    """Short sum-zero conjugates and the long sum-carrying twist relations.

    Eleven stored relations have a coordinate sum of zero and their conjugates
    keep that sum, so together with one sum-carrying relation they still span
    the full twelve-dimensional twist kernel. The families are bundled by
    ``scripts/build_icosahedron_twists.py``.
    """
    record=_twist_data().get(str(order))
    if record is None:
        return [], []
    geometry=PolyhedralPuzzle('icosahedron',order).geometry
    if record.get('geometry')!=geometry_key(geometry):
        return [], []
    short=[(tuple(vector),tuple(Move(*m) for m in word))
           for vector,word in record['short']]
    longer=[(tuple(vector),tuple(Move(*m) for m in word))
            for vector,word in record['long']]
    return short,longer


def _scaled(word,coefficient):
    if coefficient<=2:
        return word*coefficient
    return inverse_word(word,5)*(5-coefficient)


def _sparse_twist_orientation(target,order,limit=150):
    """Write a mod-5 twist target as a long relation plus a few conjugates.

    The sum of the corner rotations is the only twist-kernel invariant that
    conjugating the short relations cannot change, so one long relation fixes
    it and the sum-zero remainder is solved in the short table. Returns None if
    the bundled generators are unavailable, so the caller keeps the basis.
    """
    short,longer=_twist_generators(order)
    if not short:
        return None
    items=short[:limit]
    vecs=[vector for vector,_ in items]
    lengths=[len(word) for _,word in items]
    words=[word for _,word in items]
    size=len(vecs)
    table={}
    for i in range(size):
        for coefficient in range(1,5):
            key=tuple((coefficient*x)%5 for x in vecs[i])
            cost=min(coefficient,5-coefficient)*lengths[i]
            current=table.get(key)
            if current is None or cost<current[0]:
                table[key]=(cost,((i,coefficient),))
    for i in range(size):
        for j in range(i+1,size):
            for ci in range(1,5):
                scaled=tuple((ci*x)%5 for x in vecs[i])
                base=min(ci,5-ci)*lengths[i]
                for cj in range(1,5):
                    key=tuple((x+cj*y)%5 for x,y in zip(scaled,vecs[j]))
                    cost=base+min(cj,5-cj)*lengths[j]
                    current=table.get(key)
                    if current is None or cost<current[0]:
                        table[key]=(cost,((i,ci),(j,cj)))
    def query(remainder):
        best=None
        choice=None
        hit=table.get(remainder)
        if hit is not None:
            best,choice=hit
        for key,(cost,combination) in table.items():
            need=tuple((a-b)%5 for a,b in zip(remainder,key))
            other=table.get(need)
            if other is None:
                continue
            if {i for i,_ in combination}&{i for i,_ in other[1]}:
                continue
            total=cost+other[0]
            if best is None or total<best:
                best=total
                choice=combination+other[1]
        return best,choice
    goal=tuple(target)
    if sum(goal)%5==0:
        _cost,choice=query(goal)
        if choice is None:
            return None
        return [_scaled(words[i],coefficient) for i,coefficient in choice]
    best=None
    best_words=None
    tried=0
    for vector,word in longer:
        if sum(vector)%5==0:
            continue
        inv_sum=pow(sum(vector)%5,-1,5)
        coefficient=(sum(goal)%5*inv_sum)%5
        remainder=tuple((a-coefficient*b)%5 for a,b in zip(goal,vector))
        _cost,choice=query(remainder)
        tried+=1
        if choice is None:
            continue
        total=min(coefficient,5-coefficient)*len(word)+_cost
        if best is None or total<best:
            best=total
            best_words=[_scaled(word,coefficient)]+[_scaled(words[i],c)
                                                    for i,c in choice]
        if tried>=4:
            break
    return best_words


def _basis_orientation(target,prime,core):
    """The stored basis representation, always able to reach every target."""
    relations=core['relations'][str(prime)]
    coefficients=relation_coefficients(target,relations,prime)
    result=[]
    for coefficient,relation in zip(coefficients,relations):
        if coefficient:
            word=tuple(Move(*m) for m in relation['word'])
            if coefficient>prime//2:
                result.append(inverse_word(word,5)*(prime-coefficient))
            else:
                result.append(word*coefficient)
    return result


def _destination(work,g,orbit,labeled=None):
    """Where each piece of an orbit must travel, expressed in orbit indices."""
    if labeled is None:
        labeled=identify(work)
    indexes={p:i for i,p in enumerate(orbit)}
    destination=[None]*len(orbit)
    for home in orbit:
        position=g.stickers[labeled[g.pieces[home][0]]].piece
        destination[indexes[position]]=indexes[home]
    return destination


def _optimized_destination(work,g,orbit,labeled,trials=256):
    """Pick the same-colour labelling that leaves the fewest three-cycles.

    Single-colour orbits let any same-colour piece claim any same-colour home,
    and different choices change the permutation's cycle structure even though
    only its cycle count, not its conjugation, matters. A short random search
    among those labellings often removes a three-cycle or two per orbit; the
    replay cost is about fifteen turns each.
    """
    n=len(orbit)
    indexes={p:i for i,p in enumerate(orbit)}
    def build(labels):
        destination=[None]*n
        for home in orbit:
            position=g.stickers[labels[g.pieces[home][0]]].piece
            destination[indexes[position]]=indexes[home]
        return destination
    base=build(labeled)
    try:
        best=len(three_cycles(base))
        best_destination=base
    except ValueError:
        best=None
        best_destination=None
    # `labeled` maps each home sticker to the sticker where that home's piece
    # currently sits. Reassigning those current locations among homes of the
    # same face keeps every piece on a matching-colour slot while changing the
    # permutation's cycle structure.
    by_face={}
    for piece in orbit:
        sticker=g.pieces[piece][0]
        by_face.setdefault(g.stickers[sticker].face,[]).append(sticker)
    rng=random.Random(20240917)
    for _ in range(trials):
        labels=list(labeled)
        for face,homes in by_face.items():
            values=[labeled[home] for home in homes]
            rng.shuffle(values)
            for home,value in zip(homes,values):
                labels[home]=value
        try:
            candidate=build(labels)
            count=len(three_cycles(candidate))
        except ValueError:
            continue
        if best is None or count<best:
            best=count
            best_destination=candidate
    return best_destination if best_destination is not None else base


def solve_icosahedron(cube,cancel=None,progress=None):
    """Solve core constraints first and each independent sixty-piece orbit."""
    work=cube.entered()
    g=work.geometry
    identify(work)
    if cancel and cancel():
        raise InterruptedError()
    core=_cores().get(str(cube.n))
    if core is None or core['geometry']!=geometry_key(g):
        raise ValueError('The Icosamate core assets do not match this model')
    solution=[]
    def execute(word):
        for i,move in enumerate(word):
            if i%128==0 and cancel and cancel():
                raise InterruptedError()
            work.apply_move(move)
        solution.extend(word)
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    for index,orbit in enumerate(orbits):
        if len(orbit)==60:
            continue
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(index,len(orbits)+2)
        destination=_destination(work,g,orbit)
        cycles=three_cycles(destination)
        if not cycles:
            continue
        macro=core['position_cycles'][str(index)]
        primitive=tuple(Move(*move) for move in macro['word'])
        transports=Transports(work,orbit,tuple(macro['base']),cancel,both_directions=True)
        if len(g.pieces[orbit[0]])==1:
            # Single-colour core centres have no visible identity, so equivalent
            # cycle splits and processing orders are searched for the shortest
            # replay. Multicolour corners and edges keep their fixed split.
            execute(orbit_word(transports,orbit,destination,primitive,solution,
                               alternatives=True))
        else:
            for cycle in cycles:
                execute(transports.conjugate(tuple(orbit[i] for i in cycle),primitive))
    points=core_points(work)
    point_index={s:i for i,s in enumerate(points)}
    full=identify(work)
    state=tuple(point_index[full[s]] for s in points)
    orientations=orientation_vector(state,orientation_units(work,points))
    for prime in (5,2):
        target=tuple(-v%prime for v in orientations[prime])
        if prime==2:
            words=_sparse_edge_orientation(target,cube.n)
        else:
            words=_sparse_twist_orientation(target,cube.n)
        if words is None:
            words=_basis_orientation(target,prime,core)
        for word in words:
            execute(word)
    targets={i:orbit for i,orbit in enumerate(orbits)
             if len(orbit)==60}
    record=_cycles().get(str(cube.n))
    if record is None or record['geometry']!=geometry_key(g):
        raise ValueError('The Icosamate solver assets do not match this model')
    outer_labeled=identify(work)
    for stage,(index,orbit) in enumerate(targets.items()):
        if cancel and cancel():
            raise InterruptedError()
        if progress:
            progress(stage,len(targets))
        if len(g.pieces[orbit[0]])==1:
            destination=_optimized_destination(work,g,orbit,outer_labeled)
        else:
            destination=_destination(work,g,orbit,outer_labeled)
        cycles=three_cycles(destination)
        if not cycles:
            continue
        macro=record['cycles'][str(index)]
        primitive=tuple(Move(*move) for move in macro['word'])
        transports=Transports(work,orbit,tuple(macro['base']),cancel,both_directions=True)
        execute(orbit_word(transports,orbit,destination,primitive,solution,
                           alternatives=len(g.pieces[orbit[0]])==1))
    if not work.is_solved():
        raise ValueError('Icosamate reduction replay failed')
    return simplify(solution,5)
