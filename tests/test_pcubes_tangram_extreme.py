"""Compare the app with an independent replay of the reference cut recipe."""
import math,random
import pytest
from cube.articulated import ArticulatedCube,clipped,vertices,overlap
from cube.appearance import transform_frame
from cube.polyhedral import CUBE,Move,body,unit,dot,cross,rotate,scale,mean,add,key


def reference_parts():
    # Reference coordinates are rotated by (x,y,z)->(x,z,-y), W=.5 -> 1.
    side=[unit(a) for a in ((1,-1,0),(-1,0,1),(0,1,-1))]
    main=unit((1,1,1));edge=.4;cap=1/math.sqrt(3)-.4*math.sqrt(6)/3
    parts=[tuple((p,i) for i,p in enumerate(body(CUBE)))]
    def split(axis,bound):
        nonlocal parts
        result=[]
        for solid in parts:
            values=[dot(axis,p) for p in vertices(solid)]
            if min(values)<bound-1e-7 and max(values)>bound+1e-7:
                result.extend((clipped(solid,axis,bound),clipped(solid,scale(axis,-1),-bound)))
            else:result.append(solid)
        parts=result
    def turn(upper,angle):
        nonlocal parts
        result=[]
        for solid in parts:
            centre=dot(main,mean(vertices(solid)))
            selected=centre>cap+1e-7 if upper else centre<-cap-1e-7
            result.append(tuple((tuple(rotate(p,main,angle) for p in face),c) for face,c in solid) if selected else solid)
        parts=result
    for axis in side:split(axis,edge)
    split(main,-cap);split(main,cap)
    for upper in (True,False):
        for angle in (math.pi/3,2*math.pi/3):
            turn(upper,angle);split(side[0],edge);split(side[2],edge)
        turn(upper,2*math.pi/3);turn(upper,math.pi/3)
    return parts


def plane_signature(solid):
    rows=set()
    for points,color in solid:
        area=(0.,0.,0.)
        for a,b in zip(points,points[1:]+points[:1]):area=add(area,cross(a,b))
        if dot(area,area)<1e-15:continue
        n=unit(area);rows.add((color,key(n),round(dot(n,points[0]),7)))
    return frozenset(rows)


def test_reference_turn_split_recipe_has_the_same_complete_visible_solids():
    c=ArticulatedCube('tangram_extreme')
    parts=[s for s in reference_parts() if any(color>=0 for _,color in s)]
    assert len(parts)==len(c.solids)==44
    assert {plane_signature(s) for s in parts}=={plane_signature(s.faces) for s in c.solids}
    assert sum(color>=0 for s in c.solids for _,color in s.faces)==66
    assert sum(color>=0 for s in c.solids if s.role=='band' for _,color in s.faces)==12


def test_middle_sixty_degrees_rotates_the_axis_set_and_rejects_stale_turns():
    c=ArticulatedCube('tangram_extreme');before=c.frames
    axes=c.geometry.spec.axes
    assert {i for i in range(7) if c.axis_available(i)}=={0,1,2,6}
    c.apply_move(Move(6,1,1))
    assert {i for i in range(7) if c.axis_available(i)}=={3,4,5,6}
    assert {key(rotate(a,axes[6],math.pi/3)) for a in axes[:3]}=={key(a) for a in axes[3:6]}
    snapshot=c.frames
    with pytest.raises(ValueError):c.apply_move(Move(0,0,3))
    assert c.frames==snapshot
    c.apply_move(Move(3,0,3)).apply_move(Move(3,0,3)).apply_move(Move(6,1,5))
    assert c.frames==before


def test_slab_check_agrees_with_full_solid_collisions_and_unseen_core():
    from solver.tangram_geometry import geometry
    model=geometry('tangram_extreme');c=model.cube.clone();rng=random.Random(31)
    hidden=[s for s in reference_parts() if not any(color>=0 for _,color in s)]
    owner=next(h for h,s in enumerate(c.solids) if s.role=='band')
    for _ in range(8):
        frames,m=rng.choice(list(model.children(c.frames)))
        assert c.proposed(m)==frames
        moving=set(c.geometry.layers[m.axis][m.layer]);axis=c.geometry.spec.axes[m.axis]
        boundary=c._bands()[1][m.axis]
        for solid in hidden:
            points=[transform_frame(c.orientations[c.frames[owner]],p) for p in vertices(solid)]
            values=[dot(axis,p) for p in points]
            assert all(not(min(values)<b-1e-7 and max(values)>b+1e-7) for b in boundary)
        fixed=[c.placed_faces(h) for h in range(len(c.solids)) if h not in moving]
        for h in moving:
            placed=c.placed_faces(h,frames[h])
            assert not any(overlap(placed,s) for s in fixed)
        c.apply_move(m)
