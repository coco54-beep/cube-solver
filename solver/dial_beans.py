"""Constructive, history-free solving with independently checked three-cycles."""
from collections import Counter,deque

from cube.dial_beans import KINDS,goal,FACES
from cube.polyhedral import Move,CUBE,dot,cross


def validate(cube):
    kind=cube.puzzle_kind;values=cube.colors;expected=goal(kind)
    def invalid(message,slots=()):
        error=ValueError(message);error.locations=[dict(sticker=i) for i in slots]
        raise error
    if len(values)!=len(expected) or any(type(v) is not int or v<0 for v in values):
        invalid('Please enter every sticker',[i for i,v in enumerate(values) if type(v) is not int or v<0])
    counts=Counter(values);required=Counter(expected)
    if counts!=required:
        invalid('The color counts or numbers do not match this puzzle',[i for i,v in enumerate(values) if counts[v]>required[v]])
    if kind!='time_machine':return True
    if any(v<72 for v in values[:24]) or any(v>=72 for v in values[24:]):
        invalid('Numbers belong to the ring; colours belong to the corners',
                [i for i,v in enumerate(values) if (i<24 and v<72) or (i>=24 and v>=72)])
    from solver.letter_cube import CORNER_FACES
    expected_pieces={frozenset(faces) for faces in CORNER_FACES};seen={};twists=0
    for slots in cube.geometry.pieces[:8]:
        current={cube.geometry.stickers[s].face:values[s]-72 for s in slots}
        identity=frozenset(current.values())
        if identity not in expected_pieces or identity in seen:
            invalid('A corner has an impossible colour combination',tuple(slots)+tuple(seen.get(identity,())))
        seen[identity]=slots
        order=next(f for f in CORNER_FACES if frozenset(f)==frozenset(current))
        actual=tuple(current[f] for f in order)
        twists+=next(i for i,v in enumerate(actual) if v in (0,3))
        if dot(CUBE[actual[0]],cross(CUBE[actual[1]],CUBE[actual[2]]))*dot(CUBE[order[0]],cross(CUBE[order[1]],CUBE[order[2]]))<0:
            invalid('A corner has a mirrored orientation',slots)
    if twists%3:invalid('A corner has an impossible twist')
    return True


def primitive(cube):
    """Locally derived commutators; verify their complete effect, not a label."""
    if cube.puzzle_kind=='time_machine':
        atoms=((6,1),(1,3),(6,1),(1,9),(6,11),(1,3),(6,11),(1,9),
               (11,1),(1,3),(6,1),(1,9),(6,1),(1,3),(6,11),(1,9),(6,11),(11,11))
    else:
        from cube.dial_beans import petals
        p=petals(cube.puzzle_kind);period=cube.geometry.spec.turn_order
        from cube.dial_beans import LOOP
        half=period//2;roll=period//LOOP;rotor=period//p
        # Conjugating the front rotor by two ring slots makes its support
        # meet the wing in exactly one bead. Their commutator is a pure
        # three-cycle, replacing the previous 18-move construction.
        atoms=((0,2*roll),(3*p,rotor),(0,-2*roll),(2*p,half),
               (0,2*roll),(3*p,-rotor),(0,-2*roll),(2*p,half))
    word=tuple(Move(axis,0,amount%cube.geometry.spec.turn_order) for axis,amount in atoms)
    from solver.polyhedral import apply_word
    action=apply_word(cube.geometry,word);moved=[i for i,v in enumerate(action) if i!=v]
    if len(moved)!=3:raise ValueError('The cycle does not match this mechanism')
    a=moved[0];b=action[a];c=action[b]
    if action[c]!=a:raise ValueError('The cycle is not a pure three-cycle')
    base=tuple(cube.geometry.stickers[s].piece for s in (a,b,c))
    return word,base


def corner_cube(cube):
    from cube.cube2 import Cube2
    from cube.colors import DEFAULT_COLORS
    from cube.polyhedral import mean
    core=Cube2.solved()
    for i,s in enumerate(cube.geometry.stickers[:24]):
        pos=tuple(1 if v>0 else -1 for v in mean(s.polygon))
        core.cubies[pos].stickers[CUBE[s.face]]=DEFAULT_COLORS[FACES[cube.colors[i]-72]]
    return core


def solve(cube,cancel=None,progress=None):
    def check():
        if cancel and cancel():raise InterruptedError()
    check();validate(cube)
    if cube.is_solved():return ()
    if cube.puzzle_kind in ('bean_6','bean_10'):
        from solver.beans import solve_beans
        return solve_beans(cube,cancel,progress)
    from solver.nxn_orbits import three_cycles,parity
    from solver.polyhedral import simplify
    from solver.polyhedral_reduction import Transports
    work=cube.entered();path=[];order=cube.geometry.spec.turn_order
    def apply(word):
        for move in word:check();work.apply_move(move);path.append(move)
    if cube.puzzle_kind=='time_machine':
        from solver.solver2 import solve_2x2
        class Cancel:
            def is_set(self):return bool(cancel and cancel())
        result=solve_2x2(corner_cube(work),cancel_event=Cancel(),time_limit=.5)
        if not result.success:raise ValueError(result.message)
        from cube.notation import parse_move_full
        for token in result.moves:
            face,width,count=parse_move_full(token)
            apply((Move(FACES.index(face),0,-3*count%12),))
        # A two-layer core has no fixed centres; align its solved orientation
        # to the explicitly entered face reference before solving the rings.
        target=goal('time_machine')[:24]
        pending=deque([(work.clone(),())]);seen={tuple(work.colors[:24])};alignment=None
        while pending:
            check();state,word=pending.popleft()
            if tuple(state.colors[:24])==target:alignment=word;break
            for a,b in ((1,4),(0,3),(2,5)):
                turn=(Move(a,0,3),Move(b,0,9));child=state.clone()
                for m in turn:child.apply_move(m)
                stamp=tuple(child.colors[:24])
                if stamp not in seen:seen.add(stamp);pending.append((child,word+turn))
        if alignment is None:raise ValueError('Time Machine corner alignment failed')
        apply(alignment)
        orbit=tuple(range(8,80));slots=tuple(range(24,96))
        destination=list(work.colors[24:])
        if parity(destination):apply((Move(6,0,1),));destination=list(work.colors[24:])
    word,base=primitive(work);transports=Transports(work,orbit,base,cancel,both_directions=True)
    cycles=three_cycles(destination)
    for i,cycle in enumerate(cycles):
        check()
        if progress:progress(i,len(cycles))
        apply(transports.conjugate(tuple(orbit[j] for j in cycle),word))
    path=simplify(path,order)
    replay=cube.entered()
    for move in path:check();replay.apply_move(move)
    if not replay.is_solved():raise ValueError('Dial/bean solution replay failed')
    if progress:progress(1,1)
    return tuple(path)
