"""History-free Tangram solving and independent physical replay."""
import json
import random
import zlib
from time import monotonic

import pytest

from cube.articulated import ArticulatedCube
from cube.articulated_observation import ObservationDraft, match_observations, polygon_key
from cube.polyhedral import Move
from solver.articulated import solve_articulated
from solver.tangram_geometry import geometry
from solver.tangram_table import TangramTable, load_table


def scrambled(kind, seed, count):
    cube = ArticulatedCube(kind)
    model = geometry(kind)
    rng = random.Random(seed)
    previous = None
    for _ in range(count):
        choices = [(f, m) for f, m in model.children(cube.frames)
                   if (m.axis, m.layer) != previous]
        frames, move = rng.choice(choices)
        cube.apply_move(move)
        assert cube.frames == frames
        previous = move.axis, move.layer
    return cube


def signature(cube):
    return sorted((colour, polygon_key(points))
                  for home in range(len(cube.solids))
                  for points, colour in cube.placed_faces(home) if colour >= 0)


@pytest.mark.parametrize('kind', ['tangram', 'tangram_extreme'])
def test_fast_transitions_match_physical_cut_and_collision_checks(kind):
    model = geometry(kind)
    cube = scrambled(kind, 11, 12)
    for _ in range(4):
        code=model.shape_code(cube.frames)
        assert set(model.shape_children(code)) == {
            (model.shape_code(frames),move) for frames,move in model.children(cube.frames)
            if model.shape_code(frames)!=code}
        for move in model.moves:
            expected = model.apply(cube.frames, move)
            try:
                actual = cube.proposed(move)
            except ValueError:
                actual = None
            assert actual == expected, (kind, move)
        assert model.apply(cube.frames, Move(0, 0, 1)) is None
        cube.apply_move(next(iter(model.children(cube.frames)))[1])


@pytest.mark.parametrize('kind,count,seed',
    [('tangram',60,s) for s in (37,91,20261023)] +
    [('tangram_extreme',40,s) for s in (37,91,20261023)] +
    [('tangram_extreme',100,s) for s in (0,2)])
def test_random_state_roundtrip_manual_observations_and_physical_solve(kind, count, seed, record_property):
    source = scrambled(kind, seed, count)
    # Only visible geometry and colours cross this boundary. Neither frames
    # nor source piece IDs, scramble history or a stored inverse are supplied.
    state = json.loads(json.dumps(ObservationDraft.from_cube(source).state()))
    assert not {'frames', 'history'} & state.keys()
    begun=monotonic()
    entered = match_observations(ObservationDraft(kind, state), seconds=20.)
    matched=monotonic()
    assert entered.status == 'matched', entered.status
    cube = entered.cube
    assert not cube.history
    assert signature(cube) == signature(source)
    before = cube.frames
    word = solve_articulated(cube)
    solved=monotonic()
    assert cube.frames == before and not cube.history
    assert len(word) < 1000
    replay = cube.clone()
    replay.apply_moves(word)
    assert replay.is_solved()
    values=dict(kind=kind,seed=seed,scramble_turns=count,
                visible_observations=sum(map(len,state['views'])),
                manual_history_empty=True,geometry_matches=True,
                solution_turns=len(word),physical_replay_solved=True,
                match_seconds=round(matched-begun,3),
                solve_with_verification_seconds=round(solved-matched,3),
                independent_replay_seconds=round(monotonic()-solved,3))
    for key,value in values.items():record_property(key,value)


@pytest.mark.parametrize('kind', ['tangram', 'tangram_extreme'])
def test_every_exported_algorithm_is_a_legal_root_loop(kind):
    table = load_table(kind)
    model = table.model
    root_shape = model.shape(model.cube.frames)
    for index, record in enumerate(table.records):
        frames = tuple(model.cube.frames)
        for move in table.strong_word(index+1):
            frames = model.apply(frames, move)
            assert frames is not None
        assert model.shape(frames) == root_shape
        assert table.element(frames) == tuple(record['permutation'])


@pytest.mark.parametrize('kind', ['tangram', 'tangram_extreme'])
def test_cancel_preserves_manual_state(kind):
    cube = scrambled(kind, 7, 8)
    cube.colors = cube.frames
    before = cube.frames
    with pytest.raises(InterruptedError):
        solve_articulated(cube, cancel=lambda: True)
    assert cube.frames == before and not cube.history


def test_table_rejects_changed_physical_geometry(tmp_path):
    from pathlib import Path
    import solver.tangram_table as tables
    path = Path(tables.__file__).parent/'data'/'tangram_group.bin'
    data = json.loads(zlib.decompress(path.read_bytes()))
    data['geometry'] = 'not-the-current-physical-model'
    altered = tmp_path/'altered.bin'
    altered.write_bytes(zlib.compress(json.dumps(data).encode()))
    with pytest.raises(ValueError, match='rigid.invalid'):
        TangramTable('tangram', altered)


@pytest.mark.parametrize('kind', ['tangram','tangram_extreme'])
def test_shape_search_rejects_duplicate_occupied_geometry(kind):
    model=geometry(kind)
    occupied={}
    for (home,pose),(sid,_,_) in model.features.items():
        if sid in occupied and occupied[sid][0]!=home:
            other,other_pose=occupied[sid]
            frames=list(model.cube.frames)
            frames[home]=pose;frames[other]=other_pose
            with pytest.raises(ValueError,match='rigid.invalid'):
                model.restore_shape(tuple(frames))
            return
        occupied[sid]=home,pose
    pytest.fail('Expected a shared geometric orbit')
