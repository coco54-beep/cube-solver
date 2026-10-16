"""Bounded native three-cycle finishes, accepted only after a full replay."""
from collections import OrderedDict
from time import monotonic

from cube.cycle_effects import three_cycle
from cube.polyhedral import Move
from solver.polyhedral import compose, inverse, inverse_word, simplify

_CACHE=OrderedDict()
_KINDS={'fto','football','icosahedron','dino'}


def _records(cube):
    if cube.puzzle_kind=='fto':
        from solver.fto import _cycle_assets
        data=_cycle_assets()
    elif cube.puzzle_kind=='football':
        from solver.football import _assets
        data=_assets()
    elif cube.puzzle_kind=='icosahedron':
        from solver.icosahedron import _cycles
        data=_cycles()
    else:
        from solver.lattice_data import _data
        data=_data()
    record=data.get(str(cube.n),{})
    from solver.lattice_data import geometry_key
    if record.get('geometry')!=geometry_key(cube.geometry):
        return ()
    result=list(record.get('cycles',{}).values())
    if record.get('edge_cycle'):
        result.append(record['edge_cycle'])
    return result


def _table(cube,cancel):
    key=(cube.puzzle_kind,cube.n)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    g=cube.geometry
    solved=bytes(s.face for s in g.stickers)
    table={}
    deadline=monotonic()+.25
    limit=min(2048,max(1,4*1024*1024//len(solved)))
    def check():
        if cancel and cancel():
            raise InterruptedError()
    def keep(word,permutation):
        state=bytes(map(solved.__getitem__,permutation))
        if state!=solved and (state not in table or len(word)<len(table[state])):
            table[state]=word
    primitives=[]
    for record in _records(cube):
        check()
        try:
            word=simplify(tuple(Move(*m) for m in record['word']),g.spec.turn_order)
            effect=three_cycle(cube.puzzle_kind,cube.n,word)
        except (KeyError,TypeError,ValueError,IndexError):
            continue
        if effect is not None:
            permutation=effect[1]
            for moves,action in ((word,permutation),
                                 (inverse_word(word,g.spec.turn_order),inverse(permutation))):
                keep(moves,action)
                primitives.append((moves,action))
        if monotonic()>=deadline:
            break
    # A single setup turn covers other slots without searching on the phone.
    if primitives and monotonic()<deadline:
        from solver.polyhedral_optimize import _atoms
        for setup in _atoms(cube):
            check()
            if len(table)>=limit or monotonic()>=deadline:
                break
            action=g.permutation(setup)
            undo=inverse(action)
            for word,permutation in primitives:
                conjugate=compose(compose(action,permutation),undo)
                moves=simplify((setup,)+word+(setup.inverse(g.spec.turn_order),),g.spec.turn_order)
                keep(moves,conjugate)
                if len(table)>=limit or monotonic()>=deadline:
                    break
    _CACHE[key]=table
    while len(_CACHE)>2:
        _CACHE.popitem(last=False)
    return table


def shorten_cycle_finish(cube,word,cancel=None):
    """Replace a matching suffix; never infer legality from three wrong pieces."""
    original=tuple(word)
    if cube.puzzle_kind not in _KINDS or len(original)<32:
        return original
    table=_table(cube,cancel)
    if not table:
        return original
    g=cube.geometry
    state=bytes(s.face for s in g.stickers)
    best=original
    actions={}
    # Reconstruct suffix states backwards from solved, avoiding another full
    # traversal of solutions with thousands of moves. Final replay checks the
    # original entered state before accepting any replacement.
    for depth,move in enumerate(reversed(original[-256:]),1):
        if cancel and cancel():
            raise InterruptedError()
        action=actions.get(move)
        if action is None:
            action=g.permutation(move)
            actions[move]=action
        state=bytes(map(state.__getitem__,action))
        finish=table.get(state)
        if finish is not None and len(finish)<depth:
            candidate=simplify(original[:-depth]+finish,g.spec.turn_order)
            if len(candidate)<len(best):
                best=candidate
    if len(best)>=len(original):
        return original
    replay=cube.entered()
    for i,move in enumerate(best):
        if i%64==0 and cancel and cancel():
            raise InterruptedError()
        replay.apply_move(move)
    return best if replay.is_solved() else original
