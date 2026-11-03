"""Bounded completion of unpainted convex cells from visible rigid poses.

No invisible identity is requested from the user. Candidate placements are
rigid copies of the actual material; separating-axis tests reject overlaps.
This is an observation hypothesis, not a reachability proof.
"""
from functools import lru_cache
from time import monotonic
import numpy as np
from cube.appearance import ROTATIONS,IDENTITY_FRAME,transform_frame
from cube.curvy_copter import multiply,inverse_point
from cube.crazy_comet import vertices
from cube.compound_solids import face_normal
from cube.rigid_placements import placements,pose_key


def shape(solid,frame):
    points=np.asarray([transform_frame(frame,p) for p in vertices(solid)])
    normals=np.asarray([transform_frame(frame,face_normal(poly)) for poly,c in solid])
    bounds=np.asarray([np.dot(n,transform_frame(frame,poly[0])) for n,(poly,c) in zip(normals,solid)])
    edges={}
    for poly,c in solid:
        for a,b in zip(poly,poly[1:]+poly[:1]):
            d=np.asarray(transform_frame(frame,tuple(y-x for x,y in zip(a,b))))
            size=np.linalg.norm(d)
            if size<1e-10:continue
            d=d/size
            if next((x for x in d if abs(x)>1e-8),1)<0:d=-d
            edges[tuple(np.round(d,6))]=d
    centre=points.mean(axis=0);radius=float(np.max(np.linalg.norm(points-centre,axis=1)))
    return points,normals,bounds,np.asarray(tuple(edges.values())),centre,radius


def overlap(a,b):
    av,an,ab,ae,ac,ar=a;bv,bn,bb,be,bc,br=b
    if np.linalg.norm(ac-bc)>=ar+br-1e-8:return False
    if np.any(np.min(bv@an.T,axis=0)>=ab-1e-8):return False
    if np.any(np.min(av@bn.T,axis=0)>=bb-1e-8):return False
    axes=np.cross(ae[:,None,:],be[None,:,:]).reshape(-1,3)
    sizes=np.linalg.norm(axes,axis=1);axes=axes[sizes>1e-8]/sizes[sizes>1e-8,None]
    if len(axes):
        pa=av@axes.T;pb=bv@axes.T
        if np.any(np.max(pa,axis=0)<=np.min(pb,axis=0)+1e-8):return False
        if np.any(np.max(pb,axis=0)<=np.min(pa,axis=0)+1e-8):return False
    return True


@lru_cache(maxsize=4)
def inventory(factory):
    cube=factory();visible={h for h,f,p in cube.panels}
    hidden=tuple(h for h in range(len(cube.solids)) if h not in visible)
    if not hidden:return (),()
    prototype=hidden[0];to_prototype=[]
    for home in hidden:
        frame=next((f for destination,f,m in placements(factory,home) if destination==prototype),None)
        if frame is None:raise ValueError('Unsupported hidden material inventory')
        to_prototype.append(frame)
    return hidden,tuple(to_prototype)


def complete(cube,cancel=None,seconds=3.):
    started=monotonic();work=cube.clone();hidden,relative=inventory(type(cube))
    if not hidden:return work
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>=seconds:raise TimeoutError('copter.shape_unresolved')
    visible=[h for h in range(len(cube.solids)) if h not in hidden]
    fixed=[shape(cube.solids[h],cube.frames[h]) for h in visible]
    prototype=cube.solids[hidden[0]];candidates=[];seen=set()
    # Keep observed internal poses when they already form a compatible fill.
    old=[shape(cube.solids[h],cube.frames[h]) for h in hidden]
    if all(not overlap(a,b) for i,a in enumerate(old) for b in fixed+old[:i]):return work
    frames=tuple(dict.fromkeys(cube.frames[h] for h in visible))
    for observed in frames:
        for symmetry in ROTATIONS:
            guard();frame=multiply(observed,symmetry)
            points=tuple(sorted(tuple(round(x,6) for x in transform_frame(frame,p)) for p in vertices(prototype)))
            if points in seen:continue
            seen.add(points);placed=shape(prototype,frame)
            if any(overlap(placed,solid) for solid in fixed):continue
            candidates.append((frame,placed))
    conflict={i:{j for j in range(i) if overlap(candidates[i][1],candidates[j][1])} for i in range(len(candidates))}
    def fit(selected,start):
        guard()
        if len(selected)==len(hidden):return selected
        if len(candidates)-start<len(hidden)-len(selected):return None
        for i in range(start,len(candidates)):
            if any(j in conflict[i] for j in selected):continue
            result=fit(selected+(i,),i+1)
            if result is not None:return result
        return None
    selected=fit((),0)
    if selected is None:raise TimeoutError('copter.shape_unresolved')
    restored=list(cube.frames)
    for home,relation,index in zip(hidden,relative,selected):restored[home]=multiply(candidates[index][0],relation)
    work.frames=tuple(restored);return work
