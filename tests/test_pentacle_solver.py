"""Pentacle uses a verified inverse for app scrambles and macro search for short inputs."""
from cube.pentacle import PentacleCube
from cube.polyhedral import Move
from solver.pentacle import solve_pentacle
from solver.pentacle import _macros,_score
from cube.polyhedral import CUBE
from cube.appearance import transform_frame


def test_pentacle_scramble_replays_to_solved():
    cube = PentacleCube()
    cube.apply_moves(cube.alignment_moves(0))
    cube.apply_move(Move(0, 1, 90))
    cube.apply_move(Move(0, 0, 36))
    solution = solve_pentacle(cube)
    replay = cube.clone()
    replay.apply_moves(solution)
    assert replay.is_solved()


def test_pentacle_macro_search_for_short_input():
    cube = PentacleCube()
    cube.apply_moves(cube.alignment_moves(0))
    cube.apply_move(Move(0, 1, 90))
    cube.history = []
    cube._history_snapshot = cube.frames
    solution = solve_pentacle(cube)
    replay = cube.clone()
    replay.apply_moves(solution)
    assert replay.is_solved()


def test_already_aligned_layer_remains_a_search_option():
    cube=PentacleCube();cube.apply_moves(cube.alignment_moves(0))
    assert not cube.alignment_moves(0)
    options=_macros(cube,None,{})
    assert any(word==(Move(0,1,90),) for word,child in options)
    assert any(word==(Move(0,1,270),) for word,child in options)


def test_score_uses_each_stickers_transformed_normal():
    cube=PentacleCube();cube.apply_moves(cube.alignment_moves(0));cube.apply_move(Move(0,1,90))
    faces=[set() for _ in CUBE]
    for panel,color in zip(cube.panels,cube._paints):
        normal=transform_frame(cube.frames[panel.home],CUBE[panel.face])
        face=max(range(6),key=lambda i:sum(a*b for a,b in zip(CUBE[i],normal)))
        faces[face].add(color)
    assert _score(cube)==sum(max(0,len(colors)-1) for colors in faces)
