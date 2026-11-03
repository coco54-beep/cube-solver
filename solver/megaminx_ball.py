"""Twenty-colour D5 ball: physical piece reduction and visible centre finish.

The 20 monochrome triangular corners do not expose their axial orientation.
The five patches on each fixed cap *do* expose centre orientation. Both facts
must survive input, rather than treating the ball as a 12-colour Megaminx.
"""
from collections import Counter,deque
from functools import lru_cache
from cube.polyhedral import PolyhedralPuzzle,Move,solved_colors


@lru_cache(maxsize=1)
def _placements():
    """Lift each visible local observation through actual layer actions."""
    ball=PolyhedralPuzzle('megaminx_ball',3);old=PolyhedralPuzzle('megaminx',3)
    g=ball.geometry;h=old.geometry;records={}
    actions=tuple((g.permutation(m),h.permutation(m)) for m in ball.moves())
    for home in range(len(g.pieces)):
        new_slots=g.pieces[home];old_slots=h.pieces[home]
        start=(new_slots,old_slots);pending=deque((start,));seen={start}
        while pending:
            new,previous=pending.popleft();position=g.stickers[new[0]].piece
            visible=tuple(sorted((slot,g.stickers[src].face) for slot,src in zip(new,new_slots)))
            key=(position,tuple(color for _,color in visible))
            assignment=tuple(sorted((slot,h.stickers[src].face) for slot,src in zip(previous,old_slots)))
            variants=records.setdefault(key,[])
            if assignment not in variants:variants.append(assignment)
            for a,b in actions:
                child=(tuple(a[i] for i in new),tuple(b[i] for i in previous))
                if child not in seen:seen.add(child);pending.append(child)
    return records


def lift(cube):
    from cube.megaminx_ball import _validate_minx
    goal=solved_colors(cube);g=cube.geometry
    if any(type(c) is not int or not 0<=c<20 for c in cube.colors):
        raise ValueError('Please enter every sticker')
    if Counter(cube.colors)!=Counter(goal):
        raise ValueError('The color counts do not match this puzzle')
    old=PolyhedralPuzzle('megaminx',3);variants=None
    for position,slots in enumerate(g.pieces):
        choices=_placements().get((position,tuple(cube.colors[i] for i in slots)))
        if not choices:raise ValueError('A piece has a mirrored or impossible orientation')
        for slot,color in choices[0]:old.colors[slot]=color
        if len(slots)==1:variants=choices
    # A monochrome corner has three equivalent visible lifts. Choose one
    # satisfying the ordinary minx twist sum; no hidden label is requested.
    for choice in variants:
        for slot,color in choice:old.colors[slot]=color
        try:_validate_minx(old)
        except ValueError:continue
        return old
    raise ValueError('The entered pieces violate an orientation or permutation constraint')


@lru_cache(maxsize=1)
def _centres():
    g=PolyhedralPuzzle('megaminx_ball',3).geometry
    return tuple(next(g.pieces[p] for p in layer[0] if len(g.pieces[p])==5) for layer in g.layers)


def _phases(colors):
    cube=PolyhedralPuzzle('megaminx_ball',3);g=cube.geometry;goal=cube.colors;phases=[]
    for axis,slots in enumerate(_centres()):
        for amount in range(5):
            inv=g.inverse_permutation(Move(axis,0,amount))
            if all(colors[i]==goal[inv[i]] for i in slots):phases.append(amount);break
        else:raise ValueError('A piece has a mirrored or impossible orientation')
    return tuple(phases)


@lru_cache(maxsize=1)
def _centre_basis():
    """Twelve independent, verified centre rotations; no large solver table.

For neighbouring axes, (A B^3)^18 fixes all edge stickers and triangular
corners. Its cap phases form a rank-12 system over F5. Hidden monochrome
corner rotations are immaterial, while every visible panel is checked.
"""
    cube=PolyhedralPuzzle('megaminx_ball',3);g=cube.geometry
    identity=tuple(range(len(cube.colors)));selected=[];echelon=[]
    free=tuple(i for piece in g.pieces if len(piece)!=5 for i in piece)
    for a in range(12):
        for b in range(12):
            if a==b:continue
            word=(Move(a,0,1),Move(b,0,3))*18
            perm=identity
            for move in word:
                action=g.permutation(move);perm=tuple(action[i] for i in perm)
            if any(perm[i]!=i for i in free):continue
            work=cube.entered()
            for move in word:work.apply_move(move)
            vector=_phases(work.colors);reduced=list(vector)
            for pivot,basis in echelon:
                factor=reduced[pivot]
                reduced=[(x-factor*y)%5 for x,y in zip(reduced,basis)]
            pivot=next((i for i,x in enumerate(reduced) if x),None)
            if pivot is None:continue
            inv=pow(reduced[pivot],-1,5)
            echelon.append((pivot,tuple(x*inv%5 for x in reduced)))
            selected.append((vector,word))
            if len(selected)==12:return tuple(selected)
    raise ValueError('D5 centre finish does not span all cap orientations')


def _finish(colors):
    basis=_centre_basis();phases=_phases(colors)
    matrix=[[basis[col][0][row] for col in range(12)]+[(-phases[row])%5] for row in range(12)]
    for col in range(12):
        pivot=next(row for row in range(col,12) if matrix[row][col])
        matrix[col],matrix[pivot]=matrix[pivot],matrix[col]
        factor=pow(matrix[col][col],-1,5);matrix[col]=[x*factor%5 for x in matrix[col]]
        for row in range(12):
            if row==col:continue
            factor=matrix[row][col]
            matrix[row]=[(x-factor*y)%5 for x,y in zip(matrix[row],matrix[col])]
    result=[]
    for (_,word),row in zip(basis,matrix):
        amount=row[-1]
        if amount>2:
            word=tuple(Move(m.axis,m.layer,(-m.amount)%5) for m in reversed(word));amount=5-amount
        result.extend(word*amount)
    return tuple(result)


def solve(cube,cancel=None,progress=None):
    from solver.polyhedral import solve_minx,simplify
    if cancel and cancel():raise InterruptedError()
    entered=lift(cube)
    word=tuple(solve_minx(entered,cancel,progress))
    replay=cube.entered()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    tail=_finish(replay.colors)
    for move in tail:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Megaminx Ball replay failed')
    return simplify(word+tail,5)
