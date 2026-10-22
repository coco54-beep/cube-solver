"""Recover rigid Penrose pieces from the three visible colours.

The six solver labels are hidden identities, not six user input colours.
Local previews rebuild the shell; full reconstruction additionally matches
the inventory, corner twists, edge flips and permutation parities.
"""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic

from cube.appearance import ROTATIONS, IDENTITY_FRAME, transform_frame, with_appearance
from cube.colors import DEFAULT_COLORS
from cube.coordinates import FACE_NORMALS, rc_from_pos
from cube.cubie_model import Cubie

FACES = ('U', 'R', 'F', 'D', 'L', 'B')
VISIBLE = {'W': 'W', 'R': 'W', 'G': 'G', 'O': 'G', 'Y': 'Y', 'B': 'Y', '': ''}
COLOURS = ('W', 'G', 'Y')


def visible_facelets(facelets):
    return {face: [[VISIBLE.get(c, c) for c in row] for row in grid] for face, grid in facelets.items()}


def solved(n, kind=None):
    from cube.cube2 import Cube2
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    if n not in (2, 3, 4):
        raise ValueError('penrose.order')
    return with_appearance({2: Cube2, 3: Cube3, 4: Cube4}[n].solved(), kind or f'penrose_{n}')


def rigid_state(cube):
    """Reject legacy input which repainted stickers on the restored shell."""
    from cube.appearance import frame_for
    baseline = solved(cube.n)
    if set(cube.cubies) != set(baseline.cubies) or {p.home for p in cube.cubies.values()} != set(baseline.cubies):
        return False
    for pos, piece in cube.cubies.items():
        frame = frame_for(piece)
        if transform_frame(frame, piece.home) != pos:
            return False
        expected = {transform_frame(frame, normal): color
                    for normal, color in baseline.cubies[piece.home].stickers.items()}
        if piece.stickers != expected:
            return False
    return True


@dataclass(frozen=True)
class Choice:
    home: tuple
    frame: tuple
    stickers: tuple

    def piece(self, pos):
        return Cubie(self.home, pos, dict(self.stickers), self.frame)


@lru_cache(maxsize=3)
def catalogue(n):
    base = solved(n)
    positions = tuple(sorted(base.cubies))
    result = {}
    for pos in positions:
        choices = []
        for home, piece in base.cubies.items():
            if sorted(map(abs, home)) != sorted(map(abs, pos)):
                continue
            for frame in ROTATIONS:
                if transform_frame(frame, home) == pos:
                    stickers = tuple(sorted((transform_frame(frame, normal), color)
                                            for normal, color in piece.stickers.items()))
                    choices.append(Choice(home, frame, stickers))
        result[pos] = tuple(choices)
    return result


def options(n, pos, facelets):
    actual = {}
    choices = catalogue(n)[pos]
    normals = dict(choices[0].stickers) if choices else {}
    for face, normal in FACE_NORMALS.items():
        if normal in normals:
            r, c = rc_from_pos(n, face, pos)
            grid = facelets.get(face)
            value = grid[r][c] if grid else ''
            if value:
                actual[normal] = VISIBLE.get(value, value)
    return tuple(choice for choice in catalogue(n)[pos]
                 if all(VISIBLE[color] == actual.get(normal, VISIBLE[color]) for normal, color in choice.stickers))


@lru_cache(maxsize=2048)
def shell_signature(n, pos, choice):
    """Coloured physical patches, ignoring the invisible six-colour labels."""
    from renderer.variant_scene import _FACES, _penrose_point, _bilinear
    from cube.coordinates import get_d_maxc
    d, maxc = get_d_maxc(n); half = maxc+d*.5
    home_stickers = solved(n).cubies[choice.home].stickers
    patches = []
    for _face, normal, local in _FACES:
        corners = tuple(tuple(choice.home[a]+d*p[a] for a in range(3)) for p in local)
        points = tuple(sorted(tuple(round(v, 7) for v in transform_frame(choice.frame,
                        _penrose_point(_bilinear(corners, u, v), half, .78*d)))
                        for u in (0., .5, 1.) for v in (0., .5, 1.)))
        patches.append((VISIBLE.get(home_stickers.get(normal, ''), ''), points))
    return tuple(sorted(patches))


def preview(facelets, n, kind=None):
    cube = solved(n, kind); data = visible_facelets(facelets); unresolved = set()
    for pos, old in tuple(cube.cubies.items()):
        values = {}
        for face, normal in FACE_NORMALS.items():
            if normal in old.stickers:
                r, c = rc_from_pos(n, face, pos); values[normal] = data[face][r][c]
        candidates = options(n, pos, data) if all(values.values()) else ()
        if candidates:
            # A complete visible colour pattern determines the rounded shell.
            # Several hidden labels can still describe that same real piece.
            cube.cubies[pos] = candidates[0].piece(pos)
            continue
        cube.cubies[pos] = Cubie(pos, pos, values, IDENTITY_FRAME)
        unresolved.add(pos)
    cube.penrose_entry_unresolved = frozenset(unresolved)
    return cube


def _parity(mapping):
    values = sorted(mapping); index = {p: i for i, p in enumerate(values)}
    perm = [index[mapping[p].home] for p in values]
    return sum(perm[i] > perm[j] for i in range(len(perm)) for j in range(i+1, len(perm))) % 2


def _matching(candidates, occupied):
    """Bipartite matching for wings/centres, whose hidden labels may repeat."""
    owner = {}; picked = {}
    def insert(pos, seen):
        for choice in candidates[pos]:
            home = choice.home
            if home in occupied or home in seen:
                continue
            seen.add(home)
            if home not in owner or insert(owner[home], seen):
                owner[home] = pos; picked[pos] = choice; return True
        return False
    return picked if all(insert(pos, set()) for pos in sorted(candidates, key=lambda p: len(candidates[p]))) else None


def reconstruct(facelets, n, kind=None, cancel=None, seconds=3.):
    data = visible_facelets(facelets)
    if any(len(data.get(f, ())) != n or any(len(row) != n for row in data[f]) for f in FACES):
        raise ValueError('penrose.incomplete')
    counts = Counter(c for f in FACES for row in data[f] for c in row)
    if counts.get('', 0):
        raise ValueError('penrose.incomplete')
    if set(counts) != set(COLOURS) or any(counts[c] != 2*n*n for c in COLOURS):
        raise ValueError('penrose.counts')
    # Prefer the restored labels for a visibly restored puzzle. Equivalent
    # hidden labels must not make the reset button create a virtual scramble.
    from cube.conversion import cubies_to_facelets
    baseline = solved(n, kind)
    for frame in ROTATIONS:
        whole = solved(n, kind)
        whole.cubies = {transform_frame(frame, home): Cubie(home, transform_frame(frame, home),
                        {transform_frame(frame, normal): color for normal, color in piece.stickers.items()}, frame)
                        for home, piece in baseline.cubies.items()}
        if visible_facelets(cubies_to_facelets(whole.cubies, n)) == data:
            return whole
    candidates = {pos: options(n, pos, data) for pos in catalogue(n)}
    if any(not choices for choices in candidates.values()):
        raise ValueError('penrose.pieces')
    deadline = monotonic()+seconds; nodes = 0
    def check():
        nonlocal nodes
        nodes += 1
        if cancel and cancel():
            raise InterruptedError()
        if monotonic() >= deadline:
            raise ValueError('penrose.budget')
    corners = {p: c for p, c in candidates.items() if len(c[0].stickers) == 3}
    edges = {p: c for p, c in candidates.items() if len(c[0].stickers) == 2}
    centres = {p: c for p, c in candidates.items() if len(c[0].stickers) == 1}
    # A 3x3's six fixed centres must share one whole-cube orientation.
    global_frames = ROTATIONS if n == 3 else (IDENTITY_FRAME,)
    from cube.validation import _corner_twist, _edge_flip
    home_face = {c: f for f, c in DEFAULT_COLORS.items()}
    selected = {}; occupied = set()
    for global_frame in global_frames:
        check(); selected.clear(); occupied.clear()
        def inverse(p):
            return tuple(sum(global_frame[j][a]*p[a] for a in range(3)) for j in range(3))
        if n == 3:
            valid = True
            for pos in centres:
                choice = next((c for c in centres[pos] if c.home == inverse(pos) and c.frame == global_frame), None)
                if choice is None:
                    valid = False; break
                selected[pos] = choice; occupied.add(choice.home)
            if not valid:
                continue
        def orientations(pos, choice, corner):
            stickers = {inverse(normal): color for normal, color in choice.stickers}
            target = inverse(pos)
            colors = [stickers[tuple((1 if target[a] > 0 else -1) if j == a else 0 for j in range(3))]
                      for a in range(3) if any(normal[a] for normal in stickers)]
            if corner:
                return _corner_twist(target, next(c for c in colors if c in ('W', 'Y')), colors)
            return _edge_flip(target, colors, home_face)
        def finish():
            if n != 4:
                return dict(selected)
            wings = _matching(edges, occupied)
            if wings is None:
                return None
            centres_found = _matching(centres, occupied | {c.home for c in wings.values()})
            if centres_found is None:
                return None
            corner_parity = _parity({p: selected[p] for p in corners})
            if _parity(centres_found) != corner_parity:
                slots = list(centres_found)
                swapped = False
                for i, a in enumerate(slots):
                    for b in slots[i+1:]:
                        ca, cb = centres_found[a], centres_found[b]
                        left = next((c for c in centres[a] if c.home == cb.home), None)
                        right = next((c for c in centres[b] if c.home == ca.home), None)
                        if left and right:
                            centres_found[a], centres_found[b] = left, right; swapped = True; break
                    if swapped:
                        break
                if not swapped:
                    return None
            return {**selected, **wings, **centres_found}
        def edge_search(todo, flip=0):
            check()
            if not todo:
                mapping = {inverse(p): Choice(c.home, c.frame, c.stickers) for p, c in selected.items() if p in edges}
                corner_mapping = {inverse(p): Choice(c.home, c.frame, c.stickers) for p, c in selected.items() if p in corners}
                return finish() if flip % 2 == 0 and _parity(mapping) == _parity(corner_mapping) else None
            pos = min(todo, key=lambda p: sum(c.home not in occupied for c in edges[p]))
            for choice in edges[pos]:
                if choice.home in occupied:
                    continue
                selected[pos] = choice; occupied.add(choice.home)
                result = edge_search(todo-{pos}, (flip+orientations(pos, choice, False)) % 2)
                occupied.remove(choice.home); selected.pop(pos)
                if result is not None:
                    return result
            return None
        def corner_search(todo, twist=0):
            check()
            if not todo:
                if twist % 3:
                    return None
                return edge_search(set(edges)) if n == 3 else finish()
            pos = min(todo, key=lambda p: sum(c.home not in occupied for c in corners[p]))
            for choice in corners[pos]:
                if choice.home in occupied:
                    continue
                selected[pos] = choice; occupied.add(choice.home)
                result = corner_search(todo-{pos}, (twist+orientations(pos, choice, True)) % 3)
                occupied.remove(choice.home); selected.pop(pos)
                if result is not None:
                    return result
            return None
        result = corner_search(set(corners))
        if result is not None:
            cube = solved(n, kind)
            cube.cubies = {pos: choice.piece(pos) for pos, choice in result.items()}
            return cube
    raise ValueError('penrose.unreachable')
