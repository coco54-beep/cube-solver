"""Silver shell, physical legality, visible manual entry and deep replay."""
from itertools import product
import json
import pytest
from cube.cuboid import CuboidCube,layout,transform
from cube.polyhedral import CUBE,Move
from cube.polyhedral_scramble import scramble
from cube.cuboid_observation import SixViewDraft,project
from solver.cuboid import solve_cuboid
from tests.test_camouflage_six_view_entry import enter_visible_panels,visible_state

KIND='mirror_camouflage_3'


def test_offset_shell_and_three_selectively_trimmed_centres():
    cube=CuboidCube.solved(KIND);cells,boxes,_,_,_=layout(KIND)
    assert len(cells)==26 and len(cube.colors)==54 and set(cube.colors)=={0}
    assert len({p for group in cells for p in group})==sum(map(len,cells))==60
    assert tuple((min(b[a][0] for b in boxes),max(b[a][1] for b in boxes)) for a in range(3))==cube.shell_bounds
    assert cube.shell_bounds==((-3.,2.),(-2.25,2.75),(-2.75,2.25))
    assert cube.is_solved() and cube.color_count==1
    assert CuboidCube.solved('camouflage_3').color_count==6


@pytest.mark.parametrize('seed',range(6))
def test_every_reported_turn_avoids_solid_collisions_and_inverts(seed):
    cube=CuboidCube.solved(KIND);scramble(cube,100,seed)
    for move in cube.moves():
        trial=cube.clone().apply_move(move)
        boxes=[]
        for f,box in zip(trial.frames,layout(KIND)[1]):
            vertices=[transform(f,p) for p in product(*box)]
            boxes.append(tuple((min(v[a] for v in vertices),max(v[a] for v in vertices)) for a in range(3)))
        assert all(not all(min(a[k][1],b[k][1])-max(a[k][0],b[k][0])>1e-8 for k in range(3))
                   for i,a in enumerate(boxes) for b in boxes[i+1:])
        trial.apply_move(move.inverse(4));assert trial.frames==cube.frames and trial.colors==cube.colors


@pytest.mark.parametrize('length',(30,100))
@pytest.mark.parametrize('seed',range(6))
def test_visible_rectangles_and_highlighted_depth_reenter_without_hidden_state(seed,length):
    source=CuboidCube.solved(KIND);scramble(source,length,20261102+seed)
    draft=enter_visible_panels(source)
    assert all(d is None for view in draft.views for _,_,d in view)
    draft=SixViewDraft(KIND,json.loads(json.dumps(draft.state())))
    observation=project(source,draft.model)
    # Silver removes the face-colour clue. Supply only the visible depth of
    # the panel highlighted by ambiguity, using the existing depth control.
    for _ in range(16):
        result=draft.match(seconds=10)
        if result.status!='ambiguous':break
        f,i=result.face,result.cell;group=draft.views[f][i][1]
        depth=observation[f][i][2];assert depth is not None
        assert draft.views[f][i][2] is None
        draft.views[f]=[(c,g,depth if g==group else d) for c,g,d in draft.views[f]]
    assert result.status=='ok'
    cube=result.cube;before=visible_state(cube,draft.model)
    assert cube.history is None and before==visible_state(source,draft.model)
    word=solve_cuboid(cube)
    assert cube.history is None and visible_state(cube,draft.model)==before
    cube.apply_moves(word);assert cube.is_solved()


def test_checkpoint_preserves_anchored_silver_panels_and_frames():
    from app.session import encode,decode
    source=CuboidCube.solved(KIND);scramble(source,100,72)
    restored=decode(json.loads(json.dumps(encode(source))))
    assert type(restored) is type(source)
    assert restored.frames==source.frames and restored.colors==source.colors
    with pytest.raises(InterruptedError):solve_cuboid(restored,cancel=lambda:True)
