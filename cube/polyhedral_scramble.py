"""Lightweight legal scrambles; importing this module never loads a solver."""
import random

from cube.polyhedral import Move


_SCRAMBLE_MIN={'blossom':220}


def scramble_length(cube):
    """Scale with sticker count, preserving the existing scramble lengths."""
    length=max(30,min(320,round(len(cube.colors)/5)))
    return max(length,_SCRAMBLE_MIN.get(getattr(cube,'puzzle_kind',''),0))


def scramble(cube,length=30,seed=None):
    rng=random.Random(seed)
    moves=cube.moves()
    last=-1
    word=[]
    spec=cube.geometry.spec
    for _ in range(length):
        if cube.puzzle_kind.startswith(('cuboid_','camouflage_3')):
            moves=cube.moves()
        options=[move for move in moves if move.axis!=last] or moves
        if not options:
            raise ValueError('This puzzle has no legal scramble moves')
        move=rng.choice(options)
        move=Move(move.axis,move.layer,spec.step(move.axis)*rng.randrange(1,spec.order(move.axis)))
        cube.apply_move(move)
        word.append(move)
        last=move.axis
    return tuple(word)
