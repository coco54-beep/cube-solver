"""Cancellable, history-independent repair of a multi-axis rigid shell.

The search is bounded: failure is an unfinished shape search, not a proof
that a manually entered physical puzzle is impossible.
"""
import math,time
from copy import copy
from array import array
from functools import lru_cache
from cube.polyhedral import Move,dot,cross,rotate
from cube.appearance import IDENTITY_FRAME
from cube.curvy_copter import inverse_point,multiply
from cube.rigid_placements import pose_key


def solve_recorded_turns(cube, guard):
    """Return an inverse only after verifying it on the current shape and paint."""
    history = getattr(cube, 'history', None)
    if not history:
        return None
    from cube.copter_aligned import compact, inverse_word

    cube.validate_pose()
    if cube.is_solved():
        return ()
    inverse = inverse_word(history)
    shortened = compact(inverse)
    candidates = (shortened, inverse) if shortened != inverse else (inverse,)
    for word in candidates:
        replay = type(cube)(cube.frames, cube.paints)
        try:
            for move in word:
                replay.apply_move(move, guard)
        except ValueError:
            continue
        if replay.is_solved():
            guard()
            return word
    return None


@lru_cache(maxsize=8)
def _weights(factory):
    from cube.crazy_comet import volume
    return tuple(max(1,round(volume(s)*1000000)) for s in factory().solids)


def score(cube):
    # A hidden half-core is substantial material, not one leaf among many.
    # Equal piece counts wrongly prefer tiny surface repairs while leaving
    # an entire half-shell in a 60-degree Skewb position.
    weights=cube.shape_weights() if hasattr(cube,'shape_weights') else _weights(type(cube))
    return sum(w for h,(f,w) in enumerate(zip(cube.frames,weights))
               if not cube.frame_aligned(h,f))


def _state_key(cube):
    # Six-decimal search precision, as with pose_key, stored as compact
    # integers. This key prunes repeated search states, never physical gates.
    return array('i',(round(v*1000000) for f in cube.frames for col in f for v in col)).tobytes()


def candidates(cube,guard):
    axes=getattr(cube,'turn_axes',None)
    if axes is None:axes=cube.geometry.spec.axes
    primitive={a:set() for a in range(len(axes))}
    for move in cube.moves():primitive[move.axis].add(float(move.amount))
    for axis,normal in enumerate(axes):
        guard()
        try:selected=cube.selection(axis,guard)
        except ValueError:continue
        unaligned=[h for h in selected if not cube.frame_aligned(h,cube.frames[h])]
        if not unaligned:continue
        angles=set(primitive[axis])
        for home in unaligned:
            frame=cube.frames[home];local=inverse_point(frame,normal)
            index=min(range(3),key=lambda i:abs(dot(normal,frame[i])));u=frame[index]
            for target in cube.aligned_frames(home):
                if math.dist(local,inverse_point(target,normal))>1e-7:continue
                v=target[index]
                angle=math.degrees(math.atan2(dot(normal,cross(u,v)),dot(u,v)-dot(u,normal)*dot(v,normal)))
                if abs(angle)>1e-6:angles.add(round(angle,8))
        selected=set(selected)
        for angle in sorted(angles,key=lambda x:(abs(x),x)):
            if hasattr(cube,'allowed_amount') and not cube.allowed_amount(axis,angle):continue
            guard();turn=tuple(rotate(p,normal,math.radians(angle)) for p in IDENTITY_FRAME)
            # Search states contain immutable material, paint and frame tuples.
            # The source was validated on entry; generated rotations need not
            # reconstruct and revalidate every untouched frame on every node.
            work=copy(cube)
            work.frames=tuple(multiply(turn,f) if h in selected else f for h,f in enumerate(cube.frames))
            yield Move(axis,0,angle),work


def normalize(cube,cancel=None,seconds=30.):
    deadline=time.monotonic()+seconds
    def guard():
        if cancel and cancel():raise InterruptedError()
        if time.monotonic()>=deadline:raise TimeoutError('copter.shape_unresolved')
    guard();work=cube.clone();word=[];visited=set()
    for _ in range(len(work.frames)):
        guard();current=score(work)
        if current==0:
            work.aligned_permutation();return work,tuple(word)
        signature=tuple(pose_key(f) for f in work.frames)
        if signature in visited:break
        visited.add(signature);options=[]
        for move,candidate in candidates(work,guard):
            after=score(candidate)
            options.append((after,abs(move.amount),move,candidate))
        options.sort(key=lambda row:row[:2])
        if options and options[0][0]<current:
            _,_,move,work=options[0];word.append(move);continue
        # A second preparation may open the axis that gives a net decrease.
        best=None
        for _,_,first,one in options:
            for second,two in candidates(one,guard):
                if first.axis==second.axis:continue
                after=score(two)
                if after<current and (best is None or after<best[0]):
                    best=after,two,(first,second)
                    if after==0:break
            if best is not None and best[0]==0:break
        if best is None:break
        _,work,extra=best;word.extend(extra)
    # Retain alternate preparations: equally good local choices can lead to
    # different blocked axes, so greedy descent alone is insufficient.
    import heapq
    # Preserve a successful partial repair. Restarting only from the original
    # input discarded that progress and could exhaust eight beam levels merely
    # rediscovering moves the greedy phase had already validated.
    starts=[(work,tuple(word))] if word else []
    starts.append((cube.clone(),()))
    # Separate lanes prevent a locally attractive dead end from evicting every
    # original-input alternative. Alternate lanes under the shared time budget
    # instead of stopping after eight levels while time remains.
    lanes=[([(start,prefix)],{_state_key(start):None}) for start,prefix in starts];serial=0
    while lanes:
        next_lanes=[]
        for frontier,seen in lanes:
            following=[]
            for current,prefix in frontier:
                for move,child in candidates(current,guard):
                    state=_state_key(child)
                    if state in seen:continue
                    if len(seen)>=4096:seen.pop(next(iter(seen)))
                    seen[state]=None;after=score(child);serial+=1
                    if after==0:
                        child.aligned_permutation();return child,prefix+(move,)
                    row=(-after,-serial,child,prefix+(move,))
                    # Retain only the best 64 candidates, not every generated
                    # material state awaiting the end-of-level sort.
                    if len(following)<64:heapq.heappush(following,row)
                    elif row>following[0]:heapq.heapreplace(following,row)
            if following:
                next_lanes.append(([(child,prefix) for a,b,child,prefix in sorted(following,reverse=True)],seen))
        lanes=next_lanes
    guard();raise TimeoutError('copter.shape_unresolved')
