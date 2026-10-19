"""Restore independent corners, then the twelve oval pieces by pure cycles."""
from cube.polyhedral import Move
from solver.polyhedral import identify, piece_orbits, simplify


def solve_coin_tetrahedron(cube,cancel=None,progress=None):
    if cancel and cancel(): raise InterruptedError()
    identify(cube)
    if cube.is_solved(): return ()
    work=cube.entered()
    g=work.geometry
    solution=[]
    for axis in range(4,8):
        if cancel and cancel(): raise InterruptedError()
        corner=next(p for p in g.layers[axis][0] if len(g.pieces[p])==3)
        slots=g.pieces[corner]
        for amount in range(3):
            move=Move(axis,0,amount)
            mapping=g.inverse_permutation(move)
            if all(work.colors[mapping[s]]==g.stickers[s].face for s in slots):
                if amount:
                    work.apply_move(move)
                    solution.append(move)
                break
        else:
            raise ValueError('A piece has a mirrored or impossible orientation')
    orbits=piece_orbits(cube.puzzle_kind,cube.n)
    index,orbit=next((i,o) for i,o in enumerate(orbits) if len(o)==12)
    state=identify(work)
    locations={p:i for i,p in enumerate(orbit)}
    destination=[None]*len(orbit)
    for home in orbit:
        position=g.stickers[state[g.pieces[home][0]]].piece
        destination[locations[position]]=locations[home]
    # A face-disc turn already is a pure leaf three-cycle and fixes corners.
    primitive=(Move(0),)
    permutation=g.permutation(primitive[0])
    moved=[p for p in orbit if g.stickers[permutation[g.pieces[p][0]]].piece!=p]
    first=moved[0]
    second=g.stickers[permutation[g.pieces[first][0]]].piece
    third=g.stickers[permutation[g.pieces[second][0]]].piece
    from solver.polyhedral_reduction import Transports, orbit_word
    transports=Transports(work,orbit,(first,second,third),cancel,both_directions=True)
    word=orbit_word(transports,orbit,destination,primitive,solution,search_budget=.05)
    for move in word:
        if cancel and cancel(): raise InterruptedError()
        work.apply_move(move)
    solution.extend(word)
    if not work.is_solved(): raise ValueError('Coin Tetrahedron solution replay failed')
    if progress: progress(1,1)
    return simplify(solution,3)
