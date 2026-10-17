"""Entry scrambles must not initialise the solver package or its tables."""
from collections import Counter
from pathlib import Path
import subprocess
import sys

import pytest

from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length


@pytest.mark.parametrize('kind,order',[
    ('pyraminx',2),('pyraminx',3),('pyraminx',4),('pyraminx',5),
    ('moyu',3),('moyu',4),('moyu',5),('skewb',3),('skewb',5),
    ('skewb',7),('dino',2),('dino',4),('dino',6),
])
def test_entry_scramble_is_legal_and_repeatable(kind,order):
    cube=PolyhedralPuzzle(kind,order)
    expected=Counter(cube.colors)
    word=scramble(cube,scramble_length(cube),seed=54)
    assert Counter(cube.colors)==expected
    assert not cube.is_solved()
    replay=PolyhedralPuzzle(kind,order)
    assert scramble(replay,len(word),seed=54)==word
    assert replay.colors==cube.colors
    for move in reversed(word):
        cube.apply_move(move.inverse(cube.geometry.spec.turn_order))
    assert cube.is_solved()


def test_scramble_does_not_import_solvers():
    code="""
import sys
from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble,scramble_length
cube=PolyhedralPuzzle('pyraminx',3)
scramble(cube,scramble_length(cube),seed=54)
assert not any(name=='solver' or name.startswith('solver.') for name in sys.modules)
assert not any(name=='twophase' or name.startswith('twophase.') for name in sys.modules)
"""
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                   check=True,capture_output=True,timeout=15)
