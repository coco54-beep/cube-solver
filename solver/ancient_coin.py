"""Orient corners, then restore the visible leaf orbit with pure cycles."""
from cube.polyhedral import Move
from solver.polyhedral import identify,piece_orbits,simplify,apply_word


def solve_ancient_coin(cube,cancel=None,progress=None):
    identify(cube)
    work=cube.entered();g=work.geometry;solution=[]
    for axis in range(6,14):
        if cancel and cancel():raise InterruptedError()
        corner=next(p for p in g.layers[axis][0] if len(g.pieces[p])==3)
        slots=g.pieces[corner]
        for amount in (0,4,8):
            move=Move(axis,0,amount);mapping=g.inverse_permutation(move)
            if all(work.colors[mapping[s]]==g.stickers[s].face for s in slots):
                if amount:work.apply_move(move);solution.append(move)
                break
        else:raise ValueError('A piece has a mirrored or impossible orientation')
    orbit=next(o for o in piece_orbits(cube.puzzle_kind,3) if len(o)==24)
    state=identify(work);locations={p:i for i,p in enumerate(orbit)};destination=[None]*24
    for home in orbit:
        position=g.stickers[state[g.pieces[home][0]]].piece
        destination[locations[position]]=locations[home]
    primitive=None
    for corner_axis in range(6,14):
        candidate=(Move(0,0,3),Move(corner_axis,0,4),Move(0,0,9),Move(corner_axis,0,8))
        permutation=apply_word(g,candidate)
        moved=[p for p in orbit if g.stickers[permutation[g.pieces[p][0]]].piece!=p]
        if len(moved)==3:primitive=candidate;break
    if primitive is None:raise ValueError('Ancient Coin cycle construction failed')
    first=moved[0];second=g.stickers[permutation[g.pieces[first][0]]].piece
    third=g.stickers[permutation[g.pieces[second][0]]].piece
    from solver.polyhedral_reduction import Transports,orbit_word
    transports=Transports(work,orbit,(first,second,third),cancel,both_directions=True)
    word=orbit_word(transports,orbit,destination,primitive,solution,search_budget=.05)
    for move in word:
        if cancel and cancel():raise InterruptedError()
        work.apply_move(move)
    solution.extend(word)
    if not work.is_solved():raise ValueError('Ancient Coin solution replay failed')
    if progress:progress(1,1)
    return simplify(solution,12)
