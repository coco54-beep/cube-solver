"""Camouflage entry through the same rectangle/colour operations as the UI."""
from collections import defaultdict

import pytest

from cube.cuboid import CuboidCube
from cube.cuboid_observation import EMPTY, PLASTIC, SixViewDraft, project, bits
from cube.polyhedral_scramble import scramble


def visible_state(cube, model):
    """Compare visible colour, height and seams, without hidden piece labels."""
    result = []
    for view in project(cube, model):
        panels = defaultdict(list)
        for index, (colour, owner, depth) in enumerate(view):
            if colour != EMPTY:
                panels[owner].append(index)
        result.append((tuple((c, d) for c, _, d in view),
                       tuple(sorted(tuple(indices) for indices in panels.values()))))
    return tuple(result)


def enter_visible_panels(source):
    """Read observable panel boundaries, then draw each panel on an empty grid.

    Source owner IDs are used only to read visible cut boundaries, not copied
    into the draft. Paint generates fresh IDs. No source poses, scramble path,
    or numeric heights are supplied to the matching algorithm.
    """
    draft = SixViewDraft('camouflage_3')
    reference = project(source, draft.model)
    for face, view in enumerate(reference):
        width, _ = draft.model['shapes'][face]
        panels = defaultdict(list)
        for index, (colour, owner, depth) in enumerate(view):
            if colour != EMPTY:
                panels[colour, owner, depth].append(index)
        # Draw rear surfaces first and visible occluders afterwards, just as
        # overlapping rectangles can be entered on the flat view. Height is
        # used to choose drawing order only; each paint uses automatic depth.
        for (colour, _, depth), indices in sorted(panels.items(), key=lambda p: p[0][2]):
            rows = [i//width for i in indices]
            cols = [i % width for i in indices]
            first = min(rows)*width+min(cols)
            last = max(rows)*width+max(cols)
            rectangle = draft.rectangle(face, first, last)
            draft.paint(face, rectangle, colour)
        draft.mark_outside(face)
        assert [c for c, _, _ in draft.views[face]] == [c for c, _, _ in view]
        assert all(d is None for _, _, d in draft.views[face])
    return draft


@pytest.mark.parametrize('length', (1, 10, 40, 100))
@pytest.mark.parametrize('seed', range(12))
def test_random_camouflage_reenters_by_rectangles_with_automatic_depth(seed, length):
    source = CuboidCube.solved('camouflage_3')
    scramble(source, length, 20261021+seed)
    source.history = None
    draft = enter_visible_panels(source)
    restored_draft = SixViewDraft('camouflage_3', draft.state())
    result = restored_draft.match()
    assert result.status == 'ok', (seed, result)
    assert result.cube.history is None
    assert visible_state(result.cube, draft.model) == visible_state(source, draft.model)
    assert set(result.cube.moves()) == set(source.moves())
    move = source.moves()[0]
    expected = source.clone().apply_move(move)
    actual = result.cube.clone().apply_move(move)
    assert visible_state(actual, draft.model) == visible_state(expected, draft.model)


def test_two_and_four_samples_are_preserved_as_whole_panels():
    source = CuboidCube.solved('camouflage_3')
    draft = enter_visible_panels(source)
    sizes = set()
    for view in draft.views:
        groups = defaultdict(list)
        for index, (colour, group, _) in enumerate(view):
            if colour >= 0:
                groups[group].append(index)
        sizes.update(map(len, groups.values()))
    assert {2, 4} <= sizes
    result = draft.match()
    assert result.status == 'ok', result
    assert visible_state(result.cube, draft.model) == visible_state(source, draft.model)


def test_adjacent_same_colour_panels_cannot_be_merged_into_one_large_piece():
    source = CuboidCube.solved('camouflage_3')
    draft = enter_visible_panels(source)
    face = 2
    width, _ = draft.model['shapes'][face]
    coloured = [i for i, (colour, _, _) in enumerate(draft.views[face]) if colour >= 0]
    assert len({draft.views[face][i][1] for i in coloured}) > 1
    rows = [i//width for i in coloured]
    cols = [i % width for i in coloured]
    rectangle = draft.rectangle(face, min(rows)*width+min(cols), max(rows)*width+max(cols))
    draft.paint(face, rectangle, face)
    result = draft.match()
    assert result.status == 'conflict', result
    assert result.face == face


def test_clicking_each_cell_does_not_silently_join_a_four_cell_panel():
    source = CuboidCube.solved('camouflage_3')
    draft = enter_visible_panels(source)
    face = 2
    groups = defaultdict(list)
    for index, (colour, group, _) in enumerate(draft.views[face]):
        if colour >= 0:
            groups[group].append(index)
    panel = next(indices for indices in groups.values() if len(indices) == 4)
    colour = draft.views[face][panel[0]][0]
    for index in panel:
        draft.paint(face, (index,), colour)
    assert len({draft.views[face][i][1] for i in panel}) == 4
    result = draft.match()
    assert result.status == 'conflict', result


def test_changed_shape_includes_exposed_plastic_and_multiple_depths():
    source = CuboidCube.solved('camouflage_3')
    scramble(source, 40, 20261021)
    draft = enter_visible_panels(source)
    reference = project(source, draft.model)
    assert any(colour == PLASTIC for view in reference for colour, _, _ in view)
    assert any(len({d for c, _, d in view if c != EMPTY}) > 1 for view in reference)
    assert draft.match().status == 'ok'


@pytest.mark.parametrize('full_size,visible_size,face,piece', ((4, 2, 1, 2), (2, 1, 3, 7)))
@pytest.mark.parametrize('paint_separately', (False, True))
def test_partly_hidden_plastic_does_not_shrink_the_real_piece(
        full_size, visible_size, face, piece, paint_separately):
    source = CuboidCube.solved('camouflage_3')
    scramble(source, 40, 20261021)
    source.history = None
    draft = enter_visible_panels(source)
    reference = project(source, draft.model)
    original = draft.model['by_frame'][piece][source.frames[piece]]
    mask, depth, colour = original.views[face]
    assert colour == PLASTIC and mask.bit_count() == full_size
    visible = tuple(i for i in bits(mask) if reference[face][i][1] == piece+1)
    hidden = tuple(i for i in bits(mask) if i not in visible)
    assert len(visible) == visible_size
    assert all(reference[face][i][2] > depth for i in hidden)
    if paint_separately:
        for index in visible:
            draft.paint(face, (index,), PLASTIC)
    else:
        rectangle = draft.rectangle(face, min(visible), max(visible))
        assert set(rectangle) == set(visible)
        draft.paint(face, rectangle, PLASTIC)
    # Leave the foreground material intact, and provide no hidden black
    # samples or numeric depth hints to the matching algorithm.
    assert all(draft.views[face][i][0] == reference[face][i][0] for i in hidden)
    assert all(d is None for view in draft.views for _, _, d in view)
    result = draft.match()
    assert result.status == 'ok', result
    assert visible_state(result.cube, draft.model) == visible_state(source, draft.model)
    rebuilt = project(result.cube, draft.model)
    owners = {rebuilt[face][i][1] for i in visible}
    assert len(owners) == 1
    owner = next(iter(owners))-1
    actual = draft.model['by_frame'][owner][result.cube.frames[owner]]
    assert actual.views[face] == original.views[face]
    assert actual.views[face][0].bit_count() == full_size
