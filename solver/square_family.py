"""Constructive entered-state solvers for the SQ family, with complete replay.

SQ-2 uses Jaap Scherphuis' adjacent-pair algorithm to derive real three-cycles
and a single swap; it does not require scramble history.
https://www.jaapsch.net/puzzles/square2.htm
"""
from collections import deque

from cube.square_family import SquareFamilyMove


def _check(cancel):
    if cancel and cancel():
        raise InterruptedError()


def simplify(word):
    result = []
    for move in word:
        amount = move.amount % (2 if move.axis == move.layers else 12)
        if not amount:
            continue
        if result and result[-1].axis == move.axis and result[-1].layers == move.layers:
            amount = (result.pop().amount+amount) % (2 if move.axis == move.layers else 12)
        if amount:
            result.append(SquareFamilyMove(move.axis,amount,move.layers))
    return result


def _solve_zero(cube, cancel, progress):
    start = tuple(cube.slots[i] for i in range(0,24,3))+(cube.middle,)
    goal = tuple(range(8))+(0,)
    moves = [(axis,amount) for axis in (0,1) for amount in (1,3,2)]+[(2,1)]
    def turn(state, move):
        axis,amount = move
        p = state[:8]
        if axis == 2:
            return p[:2]+p[4:6]+p[2:4]+p[6:]+(state[8]^1,)
        offset = 4*axis
        ring = p[offset:offset+4]
        return p[:offset]+ring[amount:]+ring[:amount]+p[offset+4:]+state[8:]
    parents = ({start:None},{goal:None})
    fronts = [{start},{goal}]
    if start == goal:
        return []
    while fronts[0] and fronts[1]:
        direction = int(len(fronts[1]) < len(fronts[0]))
        next_front = set()
        for state in fronts[direction]:
            _check(cancel)
            for move in moves:
                target = turn(state,move)
                if target in parents[direction]:
                    continue
                parents[direction][target] = (state,move)
                if target in parents[1-direction]:
                    words = []
                    for parent in parents:
                        word,cursor = [],target
                        while parent[cursor] is not None:
                            cursor, (axis,amount) = parent[cursor]
                            word.append(cube.move(axis,amount*3 if axis < 2 else 1))
                        words.append(word)
                    return list(reversed(words[0]))+[m.inverse() for m in words[1]]
                next_front.add(target)
        fronts[direction] = next_front
        if progress:
            progress(len(parents[0])+len(parents[1]),80640)
    raise ValueError('square1.error.illegal')


def _perm(move):
    axis,amount = move
    p = list(range(24))
    if axis == 2:
        p[6:12],p[12:18] = p[12:18],p[6:12]
    else:
        ring = p[axis*12:axis*12+12]
        p[axis*12:axis*12+12] = ring[amount:]+ring[:amount]
    return tuple(p.index(i) for i in range(24))


def _cycle_key(triple):
    a,b,c = triple
    return min((a,b,c),(b,c,a),(c,a,b))


_PAIR_WORD = ((2,1),(0,11),(2,1),(0,1),(1,1),(2,1),(1,11),(2,1))
_CYCLE_WORD = _PAIR_WORD+((0,1),)+_PAIR_WORD+((0,11),)


def _orbit(root, cycle, cancel):
    generators = tuple((axis,k) for axis in (0,1) for k in range(1,12))+((2,1),)
    permutations = tuple(_perm(g) for g in generators)
    canonical = _cycle_key if cycle else lambda p: tuple(sorted(p))
    root = canonical(root)
    parents,queue = {root:None},deque([root])
    while queue:
        _check(cancel)
        point = queue.popleft()
        for move,permutation in zip(generators,permutations):
            target = canonical(tuple(permutation[i] for i in point))
            if target not in parents:
                parents[target] = (point,move)
                queue.append(target)
    return parents


_ORBITS = None


def _orbits(cancel):
    global _ORBITS
    if _ORBITS is None:
        # Only 4,048 oriented triples and 276 pairs; no full S24 state table.
        cycles = _orbit((5,7,6),True,cancel)
        pairs = _orbit((17,18),False,cancel)
        if len(cycles) != 4048 or len(pairs) != 276:
            raise ValueError('sq.error.generator')
        _ORBITS = cycles,pairs
    return _ORBITS


def _conjugate(word, target, parents):
    path,cursor = [],target
    while parents[cursor] is not None:
        cursor,move = parents[cursor]
        path.append(move)
    path.reverse()
    inverse = [(axis,1 if axis == 2 else -amount % 12) for axis,amount in reversed(path)]
    return inverse+list(word)+path


def _single_swap():
    result = []
    for i in range(11):
        k = (5-i) % 12
        result.extend(((0,-k % 12),)+_PAIR_WORD+((0,k),))
    return tuple(result)+((0,11),)


def _cycle_finish(cube,cycles,cancel,progress=None):
    work = cube.clone()
    result = []
    iterations = 0
    while any(i != p for i,p in enumerate(work.slots)):
        iterations += 1
        if iterations > 24:
            raise ValueError('sq.error.generator')
        _check(cancel)
        a = next(i for i,p in enumerate(work.slots) if i != p)
        b = work.slots.index(a)
        c = work.slots.index(b)
        if c == a:
            c = next(i for i,p in enumerate(work.slots) if i not in (a,b) and i != p)
            triple = (a,b,c)
        else:
            triple = (a,c,b)
        raw = _conjugate(_CYCLE_WORD,_cycle_key(triple),cycles)
        moves = simplify([work.move(axis,amount) for axis,amount in raw])
        work.apply_moves(moves)
        result.extend(moves)
        if progress:
            progress(sum(i == p for i,p in enumerate(work.slots)),24)
    return work,simplify(result)


def _parity(cube):
    return sum(a>b for i,a in enumerate(cube.slots) for b in cube.slots[i+1:]) % 2


def _solve_two(cube,cancel,progress):
    cycles,pairs = _orbits(cancel)
    work = cube.clone()
    base = []
    if work.middle:
        move = work.move(2,1)
        work.apply_move(move)
        base.append(move)
    if _parity(work) == 0:
        solved,best = _cycle_finish(work,cycles,cancel,progress)
        best = list(best)
        # Two odd layer turns are even. A pair of them often leaves a much
        # shorter cycle decomposition than solving the entered arrangement
        # directly, at the cost of two setup moves.
        for first in range(1,12):
            for second in range(1,12):
                trial = work.clone()
                move_a = trial.move(0,first)
                move_b = trial.move(1,second)
                trial.apply_move(move_a)
                trial.apply_move(move_b)
                if _parity(trial):
                    continue
                done,word = _cycle_finish(trial,cycles,cancel,None)
                if not done.is_solved():
                    continue
                candidate = [move_a,move_b]+list(word)
                if len(candidate) < len(best):
                    best = candidate
        return simplify(base+best)
    # One 12-cycle layer turn is odd. Trying all of them flips the parity with
    # one move and often leaves a much easier cycle decomposition than the old
    # 111-move single-swap macro.
    best = None
    for axis in (0,1):
        for amount in range(1,12):
            trial = work.clone()
            move = trial.move(axis,amount)
            trial.apply_move(move)
            if _parity(trial):
                continue
            solved,word = _cycle_finish(trial,cycles,cancel,None)
            if not solved.is_solved():
                continue
            candidate = [move]+list(word)
            if best is None or len(candidate) < len(best):
                best = candidate
    if best is None:
        wrong = [i for i,p in enumerate(work.slots) if i != p]
        pair = tuple(sorted(wrong[:2])) if len(wrong) >= 2 else (17,18)
        raw = _conjugate(_single_swap(),pair,pairs)
        work = work.clone()
        moves = simplify([work.move(axis,amount) for axis,amount in raw])
        work.apply_moves(moves)
        work,word = _cycle_finish(work,cycles,cancel,progress)
        best = list(moves)+list(word)
    return simplify(base+best)


def _solve_super(cube,cancel,progress):
    from solver.square1 import solve_square1
    work = cube.clone()
    result = []
    # Keep outer layers at a legal slash boundary while solving the inner pair.
    for layer in (0,3):
        ring = work.slots[layer*12:layer*12+12]
        legal = [k for k in range(12) if ring[(k-1)%12] != ring[k]
                 and ring[(k+5)%12] != ring[(k+6)%12]]
        amount = min(legal,key=lambda k:min(k,12-k))
        if amount:
            move = work.move(layer,amount)
            work.apply_move(move)
            result.append(move)
    from time import monotonic

    def solve_pair(pair,layers,plans):
        def attempt(first,second,limit):
            trial=work.clone()
            prefix=[]
            for layer,amount in zip(layers,(first,second)):
                if amount:
                    move=trial.move(layer,amount)
                    trial.apply_move(move)
                    prefix.append(move)
            try:
                projected=trial.projection(pair)
            except ValueError:
                return None
            deadline=None if limit is None else monotonic()+limit
            try:
                word=solve_square1(projected,cancel,progress,optimize_budget=0,
                                   failed_limit=1000000,
                                   hard_deadline=deadline)
            except TimeoutError:
                return None
            for move in word:
                target=trial.move(trial.layer_count if move.axis==2
                                  else layers[move.axis],move.amount)
                trial.apply_move(target)
                prefix.append(target)
            return trial,prefix
        for first,second,limit in plans:
            got=attempt(first,second,limit)
            if got is not None:
                return got
        first,second,_=plans[0]
        return attempt(first,second,None)

    for pair,layers in ((1,(1,2)),(0,(0,3))):
        _check(cancel)
        if pair == 1:
            plans=((2,2,3.0),(1,0,2.0),(9,0,2.0),(6,0,2.0),(0,1,2.0),
                   (0,6,2.0),(10,0,2.0),(0,9,2.0),(1,1,2.0),(0,0,2.0))
        else:
            plans=((0,0,None),)
        work,moves=solve_pair(pair,layers,plans)
        result.extend(moves)
        # The SQ-1 solver also restores the shared half-centre orientation.
        # Thus the second pass has even slash parity and restores the inner
        # pair it temporarily toggles, without pretending slashes are separate.
    return simplify(result)


def solve_square_family(cube,cancel=None,progress=None):
    _check(cancel)
    cube.validate()
    if cube.is_solved():
        return []
    solver = {'square0':_solve_zero,'square2':_solve_two,'super_square1':_solve_super}[cube.puzzle_kind]
    word = simplify(solver(cube,cancel,progress))
    replay = cube.clone()
    for move in word:
        _check(cancel)
        replay.apply_move(move)
    if not replay.is_solved():
        raise ValueError('square1.error.replay')
    return word
