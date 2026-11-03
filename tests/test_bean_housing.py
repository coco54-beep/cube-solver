"""Shell movement, occlusion and actual bead picking on both sides."""
import math
from collections import Counter

import pytest

from cube.polyhedral import PolyhedralPuzzle,rotate,key
from renderer.bean_housing import housing,owner_moves,dimensions


def signature(mesh,axis=None,angle=0,kind=None,turn_axis=None):
    # Suppress floating-point noise before quantising coordinates that lie
    # exactly halfway between two six-decimal bins (e.g. 0.0950625).
    def stable(v):return key(tuple(round(x,10) for x in v))
    records=[]
    for points,normals,material,owner in mesh:
        moving=axis is not None and owner_moves(kind,owner,turn_axis)
        records.append((material,tuple(sorted((stable(rotate(p,axis,angle) if moving else p),
                                              stable(rotate(n,axis,angle) if moving else n))
                                             for p,n in zip(points,normals)))))
    return Counter(records)


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_complete_wing_and_rotor_moves_rejoin_the_same_shell_without_a_final_jump(kind,n):
    cube=PolyhedralPuzzle(kind,n);g=cube.geometry;mesh=housing(kind);expected=signature(mesh)
    p=dimensions(kind)[0]
    assert {owner for *_,owner in mesh}==set(range(p))|{-3,-2,-1}
    assert all(math.isfinite(v) for points,_,_,_ in mesh for point in points for v in point)
    assert all(v[2]>=.006-1e-9 for points,_,_,owner in mesh if owner==-2 for v in points)
    assert all(v[2]<=-.006+1e-9 for points,_,_,owner in mesh if owner==-3 for v in points)
    for axis in range(2*p,3*p+2):
        angle=math.tau/g.spec.order(axis)
        assert signature(mesh,g.spec.axes[axis],angle,kind,axis)==expected
    assert not any(owner_moves(kind,owner,axis) for *_,owner in mesh for axis in range(2*p))


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_shell_is_not_selectable_and_every_front_or_back_bead_remains_selectable(kind,n):
    from tests.test_bandaged_manual_controls import pump,Tap
    from kivy.core.window import Window
    from renderer.dial_bean_view import DialBeanView
    from renderer.mat4 import Mat4
    from cube.polyhedral import mean
    cube=PolyhedralPuzzle(kind,n);view=DialBeanView(size_hint=(None,None),size=(600,600))
    view.set_cube(cube);view.yaw=view.pitch=0;Window.add_widget(view)
    try:
        from renderer.move_guide import MoveGuide
        guide=MoveGuide(view)
        for side in range(2):
            view.set_whole_world(Mat4.rotation_axis(180*side,(0,1,0)))
            pump();view._draw()
            expected=set(range(side*len(cube.colors)//2,(side+1)*len(cube.colors)//2))
            picked=set()
            # Use the central visible cap triangles, rather than a ring's
            # outline, to test the same points a person would actually tap.
            for polygon,index in view._polygons:
                if index not in expected or index in picked:continue
                point=mean(polygon);screen=(view.x+point[0],view.y+point[1])
                if view.pick(*screen)==index:picked.add(index)
            assert picked==expected
            assert view.pick(view.center_x,view.center_y) is None
            calls=[];view.on_pick=calls.append
            touch=Tap(view.center)
            assert view.on_touch_down(touch) and view.on_touch_up(touch)
            assert not calls
            guide.set_move(cube,cube.moves()[-1])
            guide.draw()
    finally:
        if 'guide' in locals():guide.dispose()
        view.cancel_animation();Window.remove_widget(view);pump()


@pytest.mark.parametrize('kind,n',[('bean_6',6),('bean_10',10)])
def test_dragging_each_central_knob_turns_only_its_visible_side(kind,n):
    from tests.test_bandaged_manual_controls import pump,Tap
    from kivy.core.window import Window
    from renderer.dial_bean_view import DialBeanTwistView
    from renderer.mat4 import Mat4
    cube=PolyhedralPuzzle(kind,n);view=DialBeanTwistView(size_hint=(None,None),size=(600,600))
    view.set_cube(cube);view.yaw=view.pitch=0;view.lock_view=True
    view.on_twist=cube.apply_move;selections=[];view.on_control_select=selections.append
    Window.add_widget(view)
    try:
        p=dimensions(kind)[0];half=len(cube.colors)//2
        for side in range(2):
            view.set_whole_world(Mat4.rotation_axis(180*side,(0,1,0)));pump();view._draw()
            before=list(cube.colors);touch=Tap((view.center_x+10,view.center_y))
            assert view.on_touch_down(touch)
            assert selections[-1]==3*p+side
            touch.y+=30;touch.pos=(touch.x,touch.y)
            assert view.on_touch_move(touch) and view.on_touch_up(touch)
            assert cube.colors[side*half:(side+1)*half]!=before[side*half:(side+1)*half]
            other=1-side
            assert cube.colors[other*half:(other+1)*half]==before[other*half:(other+1)*half]
        before=list(cube.colors);touch=Tap(view.center);view.on_touch_down(touch);view.cancel_touch()
        touch.x+=30;touch.pos=(touch.x,touch.y);view.on_touch_up(touch)
        assert cube.colors==before
    finally:
        view.cancel_touch();view.cancel_animation();Window.remove_widget(view);pump()
