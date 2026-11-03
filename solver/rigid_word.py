"""Shorten dynamic mechanisms using complete physical states and legal turns.

Colour-only loop removal is unsafe for bandages and extensions: equal paint
can conceal a different rigid piece layout. Keys include every home and pose.
"""
from time import monotonic


def _key_function(cube):
    from cube.appearance import ROTATIONS
    frame_ids={frame:i for i,frame in enumerate(ROTATIONS)}
    if hasattr(cube,'frames'):
        return lambda c:bytes(c.colors)+bytes(frame_ids[f] for f in c.frames)
    from cube.polyhedral import CUBE
    homes=tuple(sorted(cube.cubies))
    colors=sorted({v for c in cube.cubies.values() for v in c.stickers.values()},key=repr)
    palette={v:i+1 for i,v in enumerate(colors)}
    def key(c):
        data=bytearray()
        for home in homes:
            cubie=c.cubies_by_home(home)
            data.extend(v+32 for v in cubie.pos)
            data.extend(palette.get(cubie.stickers.get(normal),0) for normal in CUBE)
            data.append(255 if cubie.appearance_frame is None else frame_ids[cubie.appearance_frame])
        return bytes(data)
    return key


def _moves(cube):
    if hasattr(cube,'frames'):
        return tuple(type(m)(m.axis,m.layer,a) for m in cube.moves()
                     for a in range(cube.geometry.spec.step(m.axis),4,cube.geometry.spec.step(m.axis)))
    from cube.coordinates import FACE_AXIS_SIGN,layer_values
    result=[]
    for width in ((1,2) if cube.n==4 else (1,)):
        for face,(axis,_) in FACE_AXIS_SIGN.items():
            if cube.can_turn(axis,layer_values(cube.n,face,layers=width)):
                result.extend((str(width) if width>1 else '')+face+s for s in ('',"'",'2'))
    return tuple(result)


def shorten_rigid_word(cube,word,cancel=None,budget=.35):
    original=tuple(word)
    if cancel and cancel():raise InterruptedError()
    if len(original)<32 or budget<=0:return original
    deadline=monotonic()+budget;key=_key_function(cube)
    work=cube.clone();work.history=None if hasattr(cube,'frames') else []
    first=key(work);states=[first];seen={first:0};result=[]
    for i,move in enumerate(original):
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline or len(states)*len(first)>8*1024*1024:return original
        work.apply_move(move);state=key(work);end=seen.get(state)
        if end is not None:
            for old in states[end+1:]:del seen[old]
            del states[end+1:];del result[end:]
        else:
            result.append(move);states.append(state);seen[state]=len(result)
    if not work.is_solved():return original
    # Replace a long subpath by one legal move only when its complete target
    # state occurs later on the already verified path.
    work=cube.clone();work.history=None if hasattr(cube,'frames') else []
    candidate=[];cursor=0
    while cursor<len(result):
        if cancel and cancel():raise InterruptedError()
        if monotonic()>=deadline:
            candidate.extend(result[cursor:]);break
        best=cursor+1;chosen=result[cursor];child_best=None
        for move in _moves(work):
            if cancel and cancel():raise InterruptedError()
            if monotonic()>=deadline:break
            child=work.clone();child.apply_move(move)
            end=seen.get(key(child),-1)
            if end>best:best,chosen,child_best=end,move,child
        candidate.append(chosen)
        if child_best is None:work.apply_move(chosen)
        else:work=child_best
        cursor=best
    if len(candidate)>=len(original):return original
    # The deadline bounds optional improvement, not the final correctness
    # check. Cancellation remains available during this full native replay.
    replay=cube.clone()
    for move in candidate:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    return tuple(candidate) if replay.is_solved() else original
