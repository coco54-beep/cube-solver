"""Unpublished Curvy spherical reference: search legal shape corrections.

This is a reproducible research probe, not an entry-screen solver. Each
candidate is guarded against every solid region; no scramble witness enters
the search and no coloured panels are snapped into presumed slots.
"""
import sys,math,time,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.curvy_copter import CopterState,JUMBLE,inverse_point
from cube.polyhedral import Move,dot,cross,add,scale,EDGE_AXES
from cube.appearance import ROTATIONS
from solver.curvy_copter import align_edge_phases


def aligned(frame):return any(max(abs(a-b) for u,v in zip(frame,r) for a,b in zip(u,v))<1e-7 for r in ROTATIONS)
def score(c):return sum(not aligned(frame) for frame in c.frames)


def candidates(c):
    phases=c.edge_phases()
    for axis,normal in enumerate(EDGE_AXES):
        try:selected=c.selection(axis)
        except ValueError:continue
        angles=set(round((t-phases[axis]+180)%360-180,8)
                   for t in (0.,180.,JUMBLE,-JUMBLE,180-JUMBLE,JUMBLE-180))
        # Also discover corrections that align a visible rigid frame. This
        # does not assume every attainable critical angle is +/- JUMBLE.
        for home in selected:
            frame=c.frames[home]
            if aligned(frame):continue
            local=inverse_point(frame,normal)
            u=min(frame,key=lambda v:abs(dot(normal,v)))
            for target in ROTATIONS:
                if math.dist(local,inverse_point(target,normal))>1e-7:continue
                index=frame.index(u);v=target[index]
                angle=math.degrees(math.atan2(dot(normal,cross(u,v)),dot(u,v)-dot(u,normal)*dot(v,normal)))
                angles.add(round(angle,8))
        for angle in sorted(angles):
            if abs(angle)<1e-6:continue
            move=Move(axis,0,angle);work=c.clone()
            try:work.apply_move(move)
            except ValueError:continue
            yield move,work


def walk(seed,length):
    rng=random.Random(seed);c=CopterState()
    for _ in range(length):
        options=list(c.moves());rng.shuffle(options)
        for move in options:
            try:c.apply_move(move);break
            except ValueError:continue
    return c


def run():
    started=time.monotonic();source=walk(20261027,30)
    c,prefix=align_edge_phases(CopterState(source.frames,source.paints))
    print('initial unaligned regions',score(c),flush=True)
    best=score(c);checked=0
    for a,one in candidates(c):
        for b,two in candidates(one):
            if a.axis==b.axis:continue
            work,tail=align_edge_phases(two);checked+=1;value=score(work)
            if value<best:
                best=value;print('improvement',best,(a,b)+tail,'seconds',round(time.monotonic()-started,2),flush=True)
            if value==0:
                work.aligned_permutation();print('SHAPE ALIGNED',flush=True);return
    print('checked',checked,'best',best,'seconds',round(time.monotonic()-started,2),flush=True)


if __name__=='__main__':run()
