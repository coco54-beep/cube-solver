"""Research only: whole-material clearance for the user's special-angle case.

Never changes the playable regular mode or treats a failed spherical-model
gate as evidence that the physical puzzle cannot turn. The video supplied
by the user is BV1KA411H7jA; their screenshot matches approximately 17:42.
"""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.butterflower import ButterflowerCube
from cube.butterflower_material import structure,cuts,AXES
from cube.spherical_cells import Arrangement,Plane
from cube.curved_partition import SphereCut
from cube.curvy_copter import inverse_point,multiply
from cube.polyhedral import CUBE,rotate,dot,Move
from cube.appearance import IDENTITY_FRAME


def run():
    masks,_,_=structure();arr=Arrangement(tuple(Plane(n,1.) for n in CUBE),cuts())
    regions=tuple(arr.region(m) for m in masks)
    def selected(frames,axis):
        result=[];blocked=[]
        for home,(region,frame) in enumerate(zip(regions,frames)):
            local=SphereCut(tuple(round(v,11) for v in inverse_point(frame,cuts()[axis].centre)),1.)
            side=region.side(local)
            if side==0:blocked.append(home)
            elif side>0:result.append(home)
        if blocked:raise ValueError(tuple(blocked))
        return set(result)
    def turn(frames,axis,angle):
        moving=selected(frames,axis)
        rotation=tuple(rotate(p,AXES[axis],math.radians(angle)) for p in IDENTITY_FRAME)
        return tuple(multiply(rotation,f) if h in moving else f for h,f in enumerate(frames))
    root=(IDENTITY_FRAME,)*len(masks);rows=[]
    angles=(60.,90.,120.,math.degrees(math.acos(1/3)),180-math.degrees(math.acos(1/3)))
    for angle in angles:
        frames=turn(root,0,angle);free=[]
        for axis,n in enumerate(AXES[:12]):
            if abs(dot(n,AXES[0])-.5)>1e-8:continue
            try:selected(frames,axis)
            except ValueError:continue
            free.append(axis)
        rows.append(dict(first_degrees=angle,free_adjacent_axes=free))
    words=[];jumble=math.degrees(math.acos(1/3))
    for sa in (-1,1):
        for sb in (-1,1):
            word=((1,sa*jumble),(6,sb*jumble),(0,180.),(6,-sb*jumble),(1,-sa*jumble))
            frames=root
            try:
                for axis,angle in word:frames=turn(frames,axis,angle)
                c=ButterflowerCube(frames=frames);action=c.aligned_permutation()
            except ValueError as error:
                words.append(dict(word=word,closed=False,error=str(error)));continue
            if any(action[action[s]]!=s for s in range(len(action))):
                raise ValueError('Closed candidate is not an involution')
            for axis,angle in word:frames=turn(frames,axis,angle)
            if ButterflowerCube(frames=frames).signature()!=ButterflowerCube().signature():
                raise ValueError('Candidate double replay did not restore all material')
            words.append(dict(word=word,closed=True,changed_fields=sum(i!=x for i,x in enumerate(action)),
                              action=action,full_material_double_replay=True))
    result=dict(profile='unverified spherical model; not physical clearance proof',
                video='https://www.bilibili.com/video/BV1KA411H7jA/',screenshot_seconds=1062,
                source_axis=0,angle_probes=rows,closed_word_probes=words)
    target=Path('artifacts/expansion-references/butterflower-research/jumble-research.json')
    target.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
