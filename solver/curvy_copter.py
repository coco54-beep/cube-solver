"""Shape alignment and colour solving for the sphere-cut Copter model.

No scramble witness is read. Shape repair is followed by the private finite
colour action and every expanded physical turn is replayed on all regions.
The input screen supplies observed poses; this is not physical-unit verification.
Unresolved shapes are not called illegal.
"""
from functools import lru_cache
from collections import Counter
import math,time
from cube.polyhedral import Move,EDGE_AXES,dot,cross
from cube.appearance import ROTATIONS
from cube.curvy_copter import JUMBLE,inverse_point


@lru_cache(maxsize=8192)
def _aligned(frame):
    return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)


def _targets(cube,home):
    return cube.aligned_frames(home) if hasattr(cube,'aligned_frames') else ROTATIONS


def _piece_aligned(cube,home,frame):
    if hasattr(cube,'frame_aligned'):return cube.frame_aligned(home,frame)
    if not hasattr(cube,'aligned_frames'):return _aligned(frame)
    return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7
               for r in _targets(cube,home))


def _score(cube):return sum(not _piece_aligned(cube,home,frame) for home,frame in enumerate(cube.frames))


def _preparations(cube,guard):
    """Legal preparations, including observed frame-alignment angles."""
    phases=cube.edge_phases()
    for axis,normal in enumerate(EDGE_AXES):
        guard()
        try:selected=cube.selection(axis,guard)
        except ValueError:continue
        angles=set(round((target-phases[axis]+180)%360-180,8)
                   for target in (0.,180.,JUMBLE,-JUMBLE,180-JUMBLE,JUMBLE-180))
        for home in selected:
            frame=cube.frames[home]
            if _piece_aligned(cube,home,frame):continue
            local=inverse_point(frame,normal)
            index=min(range(3),key=lambda i:abs(dot(normal,frame[i])));u=frame[index]
            for target in _targets(cube,home):
                if math.dist(local,inverse_point(target,normal))>1e-7:continue
                v=target[index]
                angle=math.degrees(math.atan2(dot(normal,cross(u,v)),dot(u,v)-dot(u,normal)*dot(v,normal)))
                angles.add(round(angle,8))
        for angle in sorted(angles):
            if abs(angle)<1e-6:continue
            work=cube.clone();move=Move(axis,0,angle)
            work.apply_move(move,guard)
            yield move,work


def _repair(cube,score,cancel,guard):
    for first,one in _preparations(cube,guard):
        for second,two in _preparations(one,guard):
            if first.axis==second.axis:continue
            candidate,tail=align_edge_phases(two,cancel);guard()
            if _score(candidate)<score:return candidate,(first,second)+tail
    return None


def align_edge_phases(cube,cancel=None):
    """Attempt free carrier alignment; this alone does not restore shape."""
    work=cube.clone();word=[]
    def guard():
        if cancel and cancel():raise InterruptedError()
    for _ in range(12):
        if cancel and cancel():raise InterruptedError()
        phases=work.edge_phases();candidates=[]
        for axis,phase in enumerate(phases):
            correction=(-phase+90.)%180.-90.
            if abs(correction)<1e-7:continue
            move=Move(axis,0,correction)
            try:frames=work.proposed(move,guard)
            except ValueError:continue
            candidates.append((abs(correction),axis,move,frames))
        if not candidates:break
        _,_,move,frames=min(candidates,key=lambda row:row[:2])
        work.frames=frames;word.append(move)
    return work,tuple(word)


def normalize(cube,cancel=None,seconds=30.):
    """Guarded bounded repair of protrusions after carrier alignment.

    The independent two-preparation search can repair shapes that phase-only
    alignment misses. It is not a completeness guarantee or a colour solver.
    """
    deadline=time.monotonic()+seconds
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()>=deadline:raise TimeoutError('copter.shape_unresolved')
    work,word=align_edge_phases(cube,cancel)
    for _ in range(len(work.regions)):
        guard();score=_score(work)
        if score==0:break
        improved=_repair(work,score,cancel,guard)
        if improved is None:
            # Some protrusions need a regular setup before a repair lowers
            # the score. Disjoint turns of already aligned material cannot
            # alter the shape, so leave those colour-only branches out.
            for axis in range(12):
                guard()
                try:selected=work.selection(axis,guard)
                except ValueError:continue
                if all(_piece_aligned(work,h,work.frames[h]) for h in selected):continue
                setup=Move(axis,0,180.);positioned=work.clone();positioned.apply_move(setup,guard)
                found=_repair(positioned,score,cancel,guard)
                if found:
                    improved=found[0],(setup,)+found[1];break
        if improved is None:break
        work,extra=improved;word+=extra
    guard()
    try:work.aligned_permutation()
    except ValueError as e:
        if str(e)=='copter.align_first':raise ValueError('copter.shape_unresolved') from None
        raise
    return work,word


def solve(cube,cancel=None,progress=None,seconds=30.):
    """Restore observed poses and colours in the unpublished solid reference."""
    from cube.copter_aligned import observed_colors,expand
    from solver.copter_colours import solve as solve_colours,validate
    if cancel and cancel():raise InterruptedError()
    # Check every painted panel before spending time on the shape search.
    # Full local combinations can only be checked after obtaining slots.
    if any(type(c) is not int or c not in range(6) for c in cube.paints):
        raise ValueError('Please enter every sticker')
    if Counter(cube.paints)!=Counter(face for home,face,p in cube.panels):
        raise ValueError('The color counts do not match this puzzle')
    work,prefix=normalize(cube,cancel,seconds)
    colors=observed_colors(work);validate(colors)
    abstract=solve_colours(colors,cancel,progress);tail=expand(abstract)
    def guard():
        if cancel and cancel():raise InterruptedError()
    for move in tail:work.apply_move(move,guard)
    actual=observed_colors(work)
    if actual!=tuple(face for home,face,p in work.panels):
        raise ValueError('Copter physical colour replay failed')
    return prefix+tail
