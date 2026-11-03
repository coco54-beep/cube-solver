"""Replay the local Mixup definitions' cut/turn recipe, without running scripts."""
import json
import math
import sys
import random
import zlib
import hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.articulated import ArticulatedCube,vertices,clipped,MIXUP_MODELS
from cube.polyhedral import CUBE,body,dot,scale,rotate,mean,unit,cross,add,key
from cube.appearance import transform_frame


def reference(kind):
    dimensions,plus=MIXUP_MODELS[kind]
    d=1/(1+2*math.sqrt(2)) if plus else math.sqrt(2)-1
    # Parts inherit selection tags when a construction cut splits them. Undo
    # reverses the selected material, including its newly split descendants.
    parts=[(tuple((p,c) for c,p in enumerate(body(CUBE))),frozenset())]
    stack=[];serial=0
    def split(axis,bound):
        nonlocal parts
        normal=tuple(float(i==axis) for i in range(3));following=[]
        for solid,tags in parts:
            values=[dot(normal,p) for p in vertices(solid)]
            if min(values)<bound-1e-7 and max(values)>bound+1e-7:
                following.extend((clipped(solid,n,b),tags) for n,b in ((normal,bound),(scale(normal,-1),-bound)))
            else:following.append((solid,tags))
        parts=following
    def split13(axis):
        split(axis,-d);split(axis,d)
    def turn(axis):
        nonlocal parts,serial
        serial+=1;token=serial;normal=tuple(float(i==axis) for i in range(3));following=[]
        for solid,tags in parts:
            if -d+1e-7<mean(vertices(solid))[axis]<d-1e-7:
                solid=tuple((tuple(rotate(p,normal,math.pi/4) for p in poly),c) for poly,c in solid)
                tags=tags|{token}
            following.append((solid,tags))
        parts=following;stack.append((token,normal))
    def undo():
        nonlocal parts
        token,normal=stack.pop();parts=[(tuple((tuple(rotate(p,normal,-math.pi/4) for p in poly),c)
            for poly,c in solid),tags-{token}) if token in tags else (solid,tags) for solid,tags in parts]
    def visible():
        nonlocal parts
        parts=[p for p in parts if any(c>=0 for _,c in p[0])]
    for axis in range(3):split13(axis)
    if dimensions==(3,3,3):visible()
    for a,b,c in ((0,1,2),(1,2,0),(2,0,1)):
        turn(a)
        for axis in range(3):split13(axis)
        turn(b)
        for axis in range(3):split13(axis)
        undo();turn(c)
        for axis in range(3):split13(axis)
        undo();undo();visible()
    for axis,n in enumerate(dimensions):
        if n==4:split(axis,0.)
    visible();assert not stack
    return [s for s,_ in parts]


def plane_signature(solid, coloured_only=False):
    rows=set()
    for poly,c in solid:
        if coloured_only and c<0:continue
        area=(0.,0.,0.)
        for a,b in zip(poly,poly[1:]+poly[:1]):area=add(area,cross(a,b))
        if dot(area,area)<1e-15:continue
        normal=unit(area)
        rows.add((c,key(normal),round(dot(normal,poly[0]),7)))
    return frozenset(rows)


def skin_signature(solid):
    rows=[]
    for poly,c in solid:
        if c<0:continue
        points=list(poly)
        changed=True
        while changed and len(points)>3:
            changed=False
            for i,p in enumerate(points):
                a=add(p,scale(points[i-1],-1));b=add(points[(i+1)%len(points)],scale(p,-1))
                area=cross(a,b)
                if dot(area,area)<1e-16:
                    points.pop(i);changed=True;break
        rows.append((c,tuple(sorted(tuple(round(v,6) for v in p) for p in points))))
    return tuple(sorted(rows))


def run():
    rows=[];housings={}
    for kind in MIXUP_MODELS:
        ref=reference(kind);actual=ArticulatedCube(kind).solids
        expected={skin_signature(p) for p in ref}
        present={skin_signature(s.faces) for s in actual}
        row=dict(kind=kind,reference_parts=len(ref),actual_parts=len(actual),
                 coloured_parts_match=expected==present,
                 closed_bodies_match={plane_signature(p) for p in ref}=={plane_signature(s.faces) for s in actual},
                 missing_coloured_parts=len(expected-present),extra_coloured_parts=len(present-expected))
        by_skin={skin_signature(s):s for s in ref};cube=ArticulatedCube(kind)
        skins=tuple(skin_signature(s.faces) for s in actual)
        from renderer.mixup_housing import skin_fingerprint
        housings[kind]=dict(skins=hashlib.sha256(repr(skins).encode()).hexdigest(),
                           skin_mesh=skin_fingerprint(kind),
                           faces=[[(poly,c) for poly,c in by_skin[sig] if c<0] for sig in skins])
        body_points=[vertices(by_skin[skin_signature(s.faces)]) for s in actual]
        rng=random.Random(20261101);checks=0;differences=[]
        for state in range(8):
            placed=[tuple(transform_frame(cube.orientations[p],v) for v in points)
                    for p,points in zip(cube.frames,body_points)]
            extents=[tuple((min(p[a] for p in points),max(p[a] for p in points)) for a in range(3)) for points in placed]
            legal=[]
            for move in cube.moves():
                cuts=cube._bands()[1][move.axis];l=move.layer
                limits=cuts[max(0,l-1):min(l+1,len(cuts))]
                reference_clear=all(not any(lo<b-1e-7 and hi>b+1e-7 for b in limits)
                                    for bounds in extents for lo,hi in (bounds[move.axis],))
                actual_clear=cube.can_apply(move);checks+=1
                if reference_clear!=actual_clear:differences.append((state,move.axis,move.layer,reference_clear,actual_clear))
                if actual_clear:legal.append(move)
            cube.apply_move(rng.choice(legal))
        row.update(clearance_checks=checks,clearance_differences=differences)
        rows.append(row);print(json.dumps(row),flush=True)
    out=Path('reports/optimization/2026-11-01/pcubes/mixup-parts.json')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if '--export-housings' in sys.argv:
        asset=Path('cube/data/mixup_housings.bin')
        asset.write_bytes(zlib.compress(json.dumps(dict(version=1,models=housings),separators=(',',':')).encode(),9))
        print('Exported reference housings:',asset.stat().st_size,'bytes',flush=True)


if __name__=='__main__':run()
