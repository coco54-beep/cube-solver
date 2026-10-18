"""Visible-shape matching for four-layer coloured Axis/Windmill/Fisher input.

Repeated centre cards do not expose hidden cubie numbers. Match those labels
without changing any coloured polygon, then enforce centre/corner parity.
"""
from functools import lru_cache

from cube.mastermorphix import ROTATIONS,IDENTITY,positions_for_order,placements,transform,make_piece
from cube.shape_cube import faces_for


@lru_cache(maxsize=2048)
def surface_signature(kind,n,home,frame=IDENTITY):
    return tuple(sorted((color,tuple(sorted(tuple(round(v,6) for v in transform(frame,p)) for p in points)))
                        for points,color in faces_for(kind,home,n)))


@lru_cache(maxsize=3)
def shape_groups(kind,n=4):
    groups,group_of = {},{}
    for home in positions_for_order(n):
        maximum = max(abs(v) for v in home)
        orbit = sum(abs(v) == maximum for v in home)
        group = (orbit,min(surface_signature(kind,n,home,frame) for frame in ROTATIONS))
        groups.setdefault(group,[]).append(home)
        group_of[home] = group
    return group_of,{group:tuple(homes) for group,homes in groups.items()}


def equivalent_pieces(cube,home,frame,pos):
    group_of,groups = shape_groups(cube.puzzle_kind,cube.n)
    signature = surface_signature(cube.puzzle_kind,cube.n,home,frame)
    return tuple((candidate,rotation) for candidate in groups[group_of[home]]
                 for rotation in placements(candidate,pos)
                 if surface_signature(cube.puzzle_kind,cube.n,candidate,rotation) == signature)


def normalize_high_shape_input(cube,cancelled=lambda:False):
    from solver.nxn_orbits import parity
    if cube.n != 4 or set(cube.cubies) != set(cube.positions):
        raise ValueError('shape.error.duplicate')
    choices = {}
    for pos,piece in cube.cubies.items():
        if cancelled():
            raise InterruptedError()
        if piece.home not in cube.positions or piece.frame not in placements(piece.home,pos):
            raise ValueError('shape.error.duplicate')
        options = equivalent_pieces(cube,piece.home,piece.frame,pos)
        # Retain the user's label whenever it already represents a legal input.
        choices[pos] = sorted(options,key=lambda item:item != (piece.home,piece.frame))
        if not options:
            raise ValueError('shape.error.duplicate')
    assigned,owner = {},{}
    def match(pos,seen):
        if cancelled():
            raise InterruptedError()
        for home,frame in choices[pos]:
            if home in seen:
                continue
            seen.add(home)
            if home not in owner or match(owner[home],seen):
                owner[home] = pos
                assigned[pos] = (home,frame)
                return True
        return False
    for pos in sorted(cube.positions,key=lambda p:len(choices[p])):
        if not match(pos,set()):
            raise ValueError('shape.error.duplicate')
    corners = tuple(p for p in cube.positions if sum(abs(v) == 3 for v in p) == 3)
    centres = tuple(p for p in cube.positions if sum(abs(v) == 3 for v in p) == 1)
    def sign(positions):
        index = {p:i for i,p in enumerate(positions)}
        return parity([index[assigned[p][0]] for p in positions])
    if sign(corners) != sign(centres):
        # Two visually identical centres can absorb the invisible odd label
        # permutation. A genuine odd permutation of distinct shapes is invalid.
        for i,a in enumerate(centres):
            for b in centres[i+1:]:
                home_a,home_b = assigned[a][0],assigned[b][0]
                frame_a = next((f for h,f in choices[a] if h == home_b),None)
                frame_b = next((f for h,f in choices[b] if h == home_a),None)
                if frame_a is not None and frame_b is not None:
                    assigned[a],assigned[b] = (home_b,frame_a),(home_a,frame_b)
                    break
            else:
                continue
            break
        else:
            raise ValueError('shape.error.parity')
    result = cube.clone()
    result.cubies = {pos:make_piece(home,pos,frame,cube.n) for pos,(home,frame) in assigned.items()}
    return result
