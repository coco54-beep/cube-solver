"""Complete physical recovery after the fast Mixup reduction hits a limit.

No promise of a short runtime: this searches the finite physical model until a
verified solution is found or the user cancels. It does not reuse a scramble.
"""
from collections import deque
from functools import lru_cache
from cube.appearance import transform_frame
from cube.articulated import proper_poses
from cube.polyhedral import CUBE,dot
from solver.complete_search import deepen,Exhausted
from solver.mixup_reduction import geometry


@lru_cache(maxsize=1)
def orientation_patterns():
    """Relax every cut and every other piece, keeping actual pose transitions."""
    model=geometry('mixup_333');cube=model.cube;count=len(cube.orientations);proper=proper_poses('mixup')
    edges=[]
    for pose in range(count):
        values={model.next_pose(axis,amount,pose) for axis in range(3) for amount in range(1,8)}
        edges.append(tuple(v for v in values if v is not None and v!=pose))
    normals=tuple(tuple(dot(transform_frame(frame,CUBE[c]),CUBE[c])>1-1e-7 for c in range(6)) for frame in cube.orientations)
    patterns={}
    for mask in range(1,64):
        for corner in (False,True):
            allowed=proper if corner else range(count)
            goals=[p for p in allowed if all(normals[p][c] for c in range(6) if mask>>c&1)]
            distance=[255]*count;pending=deque(goals)
            for pose in goals:distance[pose]=0
            while pending:
                pose=pending.popleft()
                for child in edges[pose]:
                    if corner and child not in proper or distance[child]!=255:continue
                    distance[child]=distance[pose]+1;pending.append(child)
            patterns[mask,corner]=tuple(distance)
    return patterns


def solve_complete(cube,cancel=None,progress=None,cache_limit=120000):
    if cancel and cancel():raise InterruptedError()
    if cube.is_solved():return ()
    model=geometry(cube.puzzle_kind);tables=orientation_patterns()
    distances=[]
    for solid in cube.solids:
        mask=sum(1<<c for c in {c for poly,c in solid.faces if c>=0})
        distances.append(tables[mask,solid.role=='corner'])
    start=bytes(cube.frames),None
    if any(distances[h][p]==255 for h,p in enumerate(start[0])):raise ValueError('rigid.invalid')
    @lru_cache(maxsize=8192)
    def distance_total(frames):return sum(distances[h][p] for h,p in enumerate(frames))
    def estimate(state):return distance_total(state[0])
    root_shape=model.describe((0,)*len(cube.frames))[1]
    @lru_cache(maxsize=2048)
    def finish(frames):
        _,shape,bad=model.describe(frames)
        if (bad or shape!=root_shape) and any(distances[h][p] for h,p in enumerate(frames)):
            return None
        work=cube.clone();work.colors=frames
        if work.is_solved():return ()
        if bad or shape!=root_shape:return None
        from solver.mixup import project_cube,solve_projected
        try:return solve_projected(work,project_cube(work),cancel)
        except ValueError:
            # A shape alone is not a pairing certificate. Reject this handoff
            # and retain every physical branch of the complete search.
            return None
    def goal(state):
        return finish(bytes(state[0]))
    def children(state):
        frames,last=state;features=model.describe(frames)[0]
        for child,move in model.children(frames,features,last=last,guard=guard,complete=True):
            if any(distances[h][p]==255 for h,p in enumerate(child)):continue
            layers=getattr(move,'layers',()) or (move.layer,)
            yield (bytes(child),(move.axis,tuple(layers))),move
    def guard():
        if cancel and cancel():raise InterruptedError()
    def update(bound,nodes):
        if progress:progress({'label':'solver.continuing','progress':0.})
    try:word=deepen(start,goal,children,estimate,cancel=cancel,progress=update,
                    cache_limit=cache_limit,resume_key=('mixup-physical-v1',cube.puzzle_kind))
    except Exhausted:raise ValueError('mixup.state_unreachable') from None
    replay=cube.clone()
    for move in word:guard();replay.apply_move(move)
    if not replay.is_solved():raise ValueError('mixup.replay_failed')
    return word
