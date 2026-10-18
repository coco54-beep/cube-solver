"""Mirror shapemods: silver Axis/Windmill/Fisher shells solved by shape."""
from functools import lru_cache
import math

from cube.mastermorphix import (IDENTITY, ROTATIONS, positions_for_order,
                                transform, placements, make_piece,
                                MorphixInputError, AXIS_FACES)
from cube.mirror import MirrorCube
from cube.shape_cube import faces_for


def _clean_polygon(polygon):
    """Ignore coincident/collinear vertices introduced by plane clipping."""
    points = list(polygon)
    changed = True
    while changed and len(points) >= 3:
        changed = False
        for index, point in enumerate(points):
            before, after = points[index - 1], points[(index + 1) % len(points)]
            left = tuple(point[i] - before[i] for i in range(3))
            right = tuple(after[i] - point[i] for i in range(3))
            cross = (left[1]*right[2] - left[2]*right[1],
                     left[2]*right[0] - left[0]*right[2],
                     left[0]*right[1] - left[1]*right[0])
            if math.sqrt(sum(v*v for v in cross)) <= 1e-9:
                points.pop(index)
                changed = True
                break
    return tuple(points) if len(points) >= 3 else ()


@lru_cache(maxsize=182)
def _shell_polygons(kind, home):
    return tuple((cleaned, color >= 0) for polygon, color in faces_for(kind, home)
                 if (cleaned := _clean_polygon(polygon)))


@lru_cache(maxsize=2048)
def shell_signature(shape_kind, home, frame=IDENTITY):
    """Silver solid in the mechanism frame, without hidden colour labels."""
    return tuple(sorted(tuple(sorted(tuple(round(v, 6) for v in transform(frame, p))
                                     for p in polygon))
                        for polygon, _ in _shell_polygons(shape_kind, home)))


@lru_cache(maxsize=7)
def shape_groups(shape_kind):
    """One card per rigid shape, independent of its location and orientation.

    Only proper cube rotations are allowed; reflected/chiral parts remain
    separate. Silver exterior faces must stay exterior, not map to black cuts.
    """
    groups = {}
    group_of = {}
    for home in positions_for_order(3):
        polygons = _shell_polygons(shape_kind, home)
        vertices = {tuple(round(v, 8) for v in point)
                    for polygon, _ in polygons for point in polygon}
        center = tuple(sum(v[i] for v in vertices) / len(vertices) for i in range(3))
        centered = tuple((tuple(tuple(p[i] - center[i] for i in range(3))
                                for p in polygon), exterior)
                         for polygon, exterior in polygons)
        signature = (sum(v != 0 for v in home), min(
            tuple(sorted((exterior, tuple(sorted(tuple(round(v, 6) for v in transform(frame, p))
                                                for p in polygon)))
                         for polygon, exterior in centered))
            for frame in ROTATIONS))
        group_of[home] = signature
        groups.setdefault(signature, []).append(home)
    return group_of, {group: tuple(homes) for group, homes in groups.items()}


@lru_cache(maxsize=1024)
def shape_orientations(kind, home, pos):
    """All distinct legal appearances of this card at the selected slot."""
    group_of, groups = shape_groups(kind)
    appearances = {}
    for candidate in groups[group_of[home]]:
        for frame in placements(candidate, pos):
            appearances.setdefault(shell_signature(kind, candidate, frame), (candidate, frame))
    return tuple(appearances.values())


@lru_cache(maxsize=2048)
def equivalent_shells(kind, home, frame, pos):
    target = shell_signature(kind, home, frame)
    return tuple((candidate, rotation)
                 for candidate in shape_groups(kind)[1][shape_groups(kind)[0][home]]
                 for rotation in placements(candidate, pos)
                 if shell_signature(kind, candidate, rotation) == target)


def normalize_shape_input(cube, cancelled=lambda: False, *, preference=0):
    """Choose legal hidden labels while preserving every silver polygon.

    Matching tracks orientation sums and permutation parity, so repeated
    cards do not require the user to distinguish mechanically identical pieces.
    Nonzero preferences explore other legal hidden labels for the solver;
    entry screens retain the original, stable default matching.
    """
    from cube.conversion import cubies_to_facelets
    from cube.coordinates import FACE_NORMALS
    from solver.solver3 import _tface, _build_cubestring
    from twophase.enums import Corner, Edge

    if cancelled():
        raise InterruptedError()
    if set(cube.cubies) != set(cube.positions):
        raise MorphixInputError('incomplete')
    work = cube.clone()
    baseline = type(cube).solved()

    def state(cubies):
        face = _tface.FaceCube()
        face.from_string(_build_cubestring(cubies_to_facelets(cubies, 3)))
        return face.to_cubie_cube()

    # Scrambles and input already normalized by the entry screen usually have
    # legal labels. Do not solve the same matching problem a second time.
    if not preference and len({piece.home for piece in cube.cubies.values()}) == len(cube.positions):
        try:
            virtual = state(cube.cubies)
            twists = cube.center_twists()
            from solver.solver3 import _tcubie
            if virtual.verify() == _tcubie.CUBE_OK and virtual.corner_parity() == sum(twists) % 2:
                return work
        except (ValueError, KeyError):
            pass

    from random import Random
    ordering = Random(preference)
    matches = {}
    for enum, kind, modulus in ((Corner, 'corner', 3), (Edge, 'edge', 2)):
        positions = [tuple(sum(FACE_NORMALS[f][axis] for f in item.name)
                           for axis in range(3)) for item in enum]
        options = []
        for index, pos in enumerate(positions):
            piece = cube.cubies[pos]
            choices = []
            for home, frame in equivalent_shells(cube.shape_kind, piece.home, piece.frame, pos):
                candidate = make_piece(home, pos, frame)
                probe = dict(baseline.cubies)
                probe[pos] = candidate
                virtual = state(probe)
                identity = virtual.cp[index] if kind == 'corner' else virtual.ep[index]
                orientation = virtual.co[index] if kind == 'corner' else virtual.eo[index]
                choices.append((int(identity), orientation, candidate))
            if preference == 1:
                # Prefer virtual pieces already solved, without altering the
                # entered solid or confusing reflected parts with rotations.
                choices.sort(key=lambda item: (item[0] != index, item[1] != 0))
            elif preference:
                ordering.shuffle(choices)
            options.append(choices)

        def matching(parity):
            if preference == 1:
                # Optimize the assignment as a whole. A greedy preference at
                # one slot can consume the only suitable label of a later
                # slot. Keep permutation parity and orientation sums in the
                # state; the cost is only a search heuristic, not move count.
                @lru_cache(maxsize=32768)
                def minimum(used, orientation, inversions):
                    if cancelled():
                        raise InterruptedError()
                    index = used.bit_count()
                    if index == len(positions):
                        return 0 if orientation == 0 and inversions == parity else 1000
                    best = 1000
                    for identity, twist, _candidate in options[index]:
                        bit = 1 << identity
                        if used & bit:
                            continue
                        cost = 2*(identity != index) + (twist != 0)
                        cost += minimum(used | bit, (orientation + twist) % modulus,
                                        inversions ^ ((used >> (identity + 1)).bit_count() % 2))
                        best = min(best, cost)
                        if best == 0:
                            break
                    return best

                try:
                    if minimum(0, 0, 0) >= 1000:
                        return None
                    assigned = {}
                    used = orientation = inversions = 0
                    for index, pos in enumerate(positions):
                        target = minimum(used, orientation, inversions)
                        for identity, twist, candidate in options[index]:
                            bit = 1 << identity
                            if used & bit:
                                continue
                            new_orientation = (orientation + twist) % modulus
                            new_inversions = inversions ^ ((used >> (identity + 1)).bit_count() % 2)
                            cost = 2*(identity != index) + (twist != 0)
                            if cost + minimum(used | bit, new_orientation, new_inversions) == target:
                                assigned[pos] = candidate
                                used |= bit
                                orientation, inversions = new_orientation, new_inversions
                                break
                    return assigned
                finally:
                    # Matching caches must not accumulate across phone solves.
                    minimum.cache_clear()
            failed = set()
            def assign(index, used, orientation, inversions):
                if cancelled():
                    raise InterruptedError()
                if index == len(positions):
                    return {} if orientation == 0 and inversions == parity else None
                marker = (used, orientation, inversions)
                if marker in failed:
                    return None
                for identity, twist, candidate in options[index]:
                    bit = 1 << identity
                    if used & bit:
                        continue
                    tail = assign(index + 1, used | bit, (orientation + twist) % modulus,
                                  inversions ^ ((used >> (identity + 1)).bit_count() % 2))
                    if tail is not None:
                        tail[positions[index]] = candidate
                        return tail
                failed.add(marker)
                return None
            return assign(0, 0, 0, 0)
        matches[kind] = {parity: matching(parity) for parity in (0, 1)}

    # Fixed centres retain their reference axes. Symmetric centre directions
    # can absorb the hidden supercube parity without changing their appearance.
    center_options = []
    from cube.coordinates import TURNS
    for face in AXIS_FACES:
        pos = FACE_NORMALS[face]
        piece = cube.cubies[pos]
        equivalent = set(equivalent_shells(cube.shape_kind, piece.home, piece.frame, pos))
        frame = IDENTITY
        choices = []
        for turn in range(4):
            if (pos, frame) in equivalent:
                choices.append((turn, make_piece(pos, pos, frame)))
            frame = tuple(TURNS[face](*v) for v in frame)
        if not choices:
            raise MorphixInputError('centers')
        if preference > 1:
            ordering.shuffle(choices)
        center_options.append((pos, choices))

    parities = [0, 1]
    if preference > 1:
        ordering.shuffle(parities)
    preferred = []
    for parity in parities:
        if any(matches[kind][parity] is None for kind in ('corner', 'edge')):
            continue
        centers = {0: {}}
        for pos, choices in center_options:
            following = {}
            for previous, assigned in centers.items():
                for twist, piece in choices:
                    following.setdefault((previous + twist) % 2, {**assigned, pos: piece})
            centers = following
        if parity in centers:
            work.cubies.update(matches['corner'][parity])
            work.cubies.update(matches['edge'][parity])
            work.cubies.update(centers[parity])
            if preference == 1:
                cost = sum(2*(piece.home != pos) + (piece.frame != IDENTITY)
                           for pos, piece in work.cubies.items())
                preferred.append((cost, work.clone()))
                continue
            return work
    if preferred:
        return min(preferred, key=lambda item: item[0])[1]
    raise MorphixInputError('invalid')


class MirrorShapeCube(MirrorCube):
    """A mirror cube whose exterior shell follows a shape-mod profile.

    The mechanical state is the ordinary 3x3 mirror state; only the exterior
    polygons change, so the ordinary mirror solver applies unchanged. Solved
    states compare the silver shell up to the cube's global rotations.
    """

    shape_kind = None

    def is_solved(self):
        if set(self.cubies) != set(self.positions):
            return False

        current = tuple(sorted(polygon for piece in self.cubies.values()
                               for polygon in shell_signature(self.shape_kind, piece.home, piece.frame)))
        return current in solved_shells(self.shape_kind)


@lru_cache(maxsize=7)
def solved_shells(kind):
    return frozenset(tuple(sorted(polygon for home in positions_for_order(3)
                                 for polygon in shell_signature(kind, home, frame)))
                     for frame in ROTATIONS)


class MirrorWindmillCube(MirrorShapeCube):
    puzzle_kind = 'mirror_windmill'
    shape_kind = 'windmill'


class MirrorAxisCube(MirrorShapeCube):
    puzzle_kind = 'mirror_axis'
    shape_kind = 'axis'


class MirrorFisherCube(MirrorShapeCube):
    puzzle_kind = 'mirror_fisher'
    shape_kind = 'fisher'


class MirrorUnequalWindmillCube(MirrorShapeCube):
    puzzle_kind = 'mirror_windmill_unequal'
    shape_kind = 'windmill_unequal'


class MirrorUnequalFisherCube(MirrorShapeCube):
    puzzle_kind = 'mirror_fisher_unequal'
    shape_kind = 'fisher_unequal'


class MirrorOffsetWindmillCube(MirrorShapeCube):
    puzzle_kind = 'mirror_windmill_offset'
    shape_kind = 'windmill_offset'


class MirrorOffsetFisherCube(MirrorShapeCube):
    puzzle_kind = 'mirror_fisher_offset'
    shape_kind = 'fisher_offset'
