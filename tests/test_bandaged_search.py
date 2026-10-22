"""Legal-search regression for the smallest bandaged preset."""
from cube.bandaged_cube import BandagedCube
from solver.bandaged_search import solve_bandaged_search


def test_bicube_manual_state_solves():
    cube = BandagedCube.random_scramble('bicube', length=12, seed=7)
    cube.history = []
    solution = solve_bandaged_search(cube)
    replay = cube.clone()
    replay.history = []
    replay.apply_moves(solution)
    assert replay.is_solved()


def test_two_bar_table_solves_manual_state():
    cube = BandagedCube.random_scramble('two_bar_cube', length=10, seed=3)
    cube.history = []
    solution = solve_bandaged_search(cube)
    replay = cube.clone()
    replay.history = []
    replay.apply_moves(solution)
    assert replay.is_solved()


def test_bandaged_c_table_solves_manual_state():
    cube = BandagedCube.random_scramble('bandaged_c', length=16, seed=4)
    cube.history = []
    solution = solve_bandaged_search(cube)
    replay = cube.clone()
    replay.history = []
    replay.apply_moves(solution)
    assert replay.is_solved()
