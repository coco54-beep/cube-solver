"""Invisible material must survive replay seeks and JSON restoration."""
import json
import pytest
from cube.checkpoints import capture,restore,full_state
from cube.twins_state import TwinsState
from cube.polyhedral import Move,PolyhedralPuzzle
from app.session import encode,decode


def test_cad_diagonal_checkpoint_keeps_all_hidden_poses_and_replays_twice():
    initial=TwinsState().apply_move(Move(12,0,120.));saved=capture(initial)
    assert full_state(initial)
    for _ in range(2):
        work=TwinsState();restore(work,saved)
        assert work.signature()==initial.signature()
        work.apply_move(Move(12,0,-120.));assert work.is_solved()
        restore(work,decode(json.loads(json.dumps(encode(saved)))))
        assert work.signature()==initial.signature()


def test_sticker_only_models_keep_lightweight_checkpoints():
    cube=PolyhedralPuzzle('dino',2);cube.apply_move(cube.moves()[0]);saved=capture(cube)
    assert isinstance(saved,tuple) and not full_state(cube)
    before=tuple(cube.colors);cube.apply_move(cube.moves()[1]);restore(cube,saved)
    assert tuple(cube.colors)==before
