"""Independent restoration of AJ's deep/shallow corner-turning mechanism."""
from cube.polyhedral import Move
from solver.polyhedral import identify,piece_orbits,simplify,_parity,inverse_word
from solver.rex_dodecahedron import prepared,flip_paths


def validate(cube):
    g=cube.geometry;state=identify(cube)
    core=next(p for p in g.pieces if len(p)==12)
    if any(cube.colors[s]!=g.stickers[s].face for s in core):
        raise ValueError('aj.error.fixed_centres')
    for orbit in piece_orbits(cube.puzzle_kind,cube.n):
        if len(orbit)==1:continue
        local={p:i for i,p in enumerate(orbit)}
        points=[local[g.stickers[state[g.pieces[h][0]]].piece] for h in orbit]
        if _parity(points):raise ValueError('aj.error.orbit_parity')
        if len(orbit)==30:
            flips=sum(state[g.pieces[h][0]]!=g.pieces[g.stickers[state[g.pieces[h][0]]].piece][0] for h in orbit)
            if flips%2:raise ValueError('aj.error.edge_flip')
    return state


def solve(cube,cancel=None,progress=None):
    from solver.polyhedral_reduction import Transports,orbit_word
    if cancel and cancel():raise InterruptedError()
    work=cube.entered();g=work.geometry;orbits=piece_orbits(cube.puzzle_kind,cube.n)
    validate(work)
    if work.is_solved():return ()
    order,macros,flip_word,_=prepared(cube.puzzle_kind,cube.n)
    solution=[]
    # Each vertex has two stationary-position, independently oriented caps.
    # The deep cap turn also carries the shallow tip, so correct deep first.
    for axis in range(len(g.spec.axes)):
        for layer in (0,1):
            if cancel and cancel():raise InterruptedError()
            selected=set(g.layers[axis][layer])
            if layer==0:selected-=set(g.layers[axis][1])
            caps=[p for p in selected if len(g.pieces[p])==3]
            if len(caps)!=1:raise ValueError('AJ cap selection does not match its cut geometry')
            slots=g.pieces[caps[0]]
            for amount in range(3):
                move=Move(axis,layer,amount);effect=g.permutation(move)
                if all(work.colors[s]==g.stickers[effect[s]].face for s in slots):
                    if amount:work.apply_move(move);solution.append(move)
                    break
            else:raise ValueError('A piece has a mirrored or impossible orientation')
    finished=[s for o in orbits if len(o)==1 for p in o for s in g.pieces[p]]
    if any(work.colors[s]!=g.stickers[s].face for s in finished):
        raise ValueError('AJ cap restoration replay failed')
    for stage,i in enumerate(order):
        if cancel and cancel():raise InterruptedError()
        if progress:progress(stage,len(order))
        orbit=orbits[i];state=identify(work,only=(i,));local={p:j for j,p in enumerate(orbit)}
        destination=[None]*len(orbit)
        for home in orbit:
            destination[local[g.stickers[state[g.pieces[home][0]]].piece]]=local[home]
        if _parity(destination):raise ValueError('aj.error.orbit_parity')
        if destination!=list(range(len(orbit))):
            primitive,base=macros[i];transport=Transports(work,orbit,base,cancel,both_directions=True)
            word=orbit_word(transport,orbit,destination,primitive,solution,search_budget=.06)
            for move in word:
                if cancel and cancel():raise InterruptedError()
                work.apply_move(move)
            solution.extend(word)
        if len(orbit)==30:
            flipped=[p for p in orbit if any(work.colors[s]!=g.stickers[s].face for s in g.pieces[p])]
            if len(flipped)%2:raise ValueError('aj.error.edge_flip')
            for a,b in zip(flipped[::2],flipped[1::2]):
                path=flip_paths(cube.puzzle_kind,cube.n)[tuple(sorted((a,b)))]
                word=inverse_word(path,3)+flip_word+path
                for move in word:
                    if cancel and cancel():raise InterruptedError()
                    work.apply_move(move)
                solution.extend(word)
        finished.extend(s for p in orbit for s in g.pieces[p])
        if any(work.colors[s]!=g.stickers[s].face for s in finished):
            raise ValueError('AJ stage replay does not match the entered state')
    solution=simplify(solution,3);replay=cube.entered()
    for move in solution:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('AJ full solution replay failed')
    if progress:progress(len(order),len(order))
    return solution
