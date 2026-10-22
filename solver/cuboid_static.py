"""State-based constructive solver for the fixed-shape cuboid subgroups.

Physical panels, not artificial backing cells, are the permutation points.
The strong generators use only the model's legal turns. No scramble is read.
"""
from collections import defaultdict, deque
from functools import lru_cache
from types import SimpleNamespace
from pathlib import Path
from array import array
import base64
import json
import zlib

from cube.cuboid import CuboidCube, FIXED_SHAPE_KINDS, layout, transform
from solver.polyhedral import StabilizerChain, simplify, compose, inverse, inverse_word


@lru_cache(maxsize=3)
def mechanism(kind):
    if kind not in FIXED_SHAPE_KINDS:
        from solver.cuboid_extensions import extension_mechanism
        return extension_mechanism(kind)
    cube = CuboidCube.solved(kind)
    cells, boxes, entries, lookup, base = layout(kind)
    panel_groups = cube._panel_groups(cube.geometry)
    by_piece = defaultdict(list)
    for piece, face in panel_groups:
        by_piece[piece].append(face)
    def phase(piece):
        colors = by_piece[piece]
        return 0 if len(colors) == 3 else (1 if 0 in colors or 3 in colors else 2) if len(colors) == 2 else 3
    panels = tuple(sorted(panel_groups, key=lambda p: (-phase(p[0]), p)))
    panel_index = {panel: i for i, panel in enumerate(panels)}
    representatives = tuple(panel_groups[p][0] for p in panels)
    point_at = {slot: panel_index[p] for p, slots in panel_groups.items() for slot in slots}
    permutations = {}
    atoms = []
    seen = set()
    for move in cube.moves():
        perm = base.permutation(move)
        physical = tuple(point_at[perm[i]] for i in representatives)
        if physical not in seen:
            seen.add(physical); atoms.append(move)
        for power in (1, 2, 3):
            from cube.polyhedral import Move
            atom = Move(move.axis, move.layer, move.amount*power % 4)
            if not atom.amount:
                continue
            perm = base.permutation(atom)
            permutations[atom] = tuple(point_at[perm[i]] for i in representatives)
    geometry = SimpleNamespace(stickers=panels, permutation=permutations.__getitem__,
                               spec=SimpleNamespace(turn_order=4))
    adapter = SimpleNamespace(geometry=geometry, moves=lambda: tuple(atoms))
    return adapter, panels, representatives, point_at


def phase_points(kind):
    adapter = mechanism(kind)[0]
    if hasattr(adapter, 'phase_points'):
        return adapter.phase_points
    panels = mechanism(kind)[1]
    by_piece = defaultdict(list)
    for i, (piece, face) in enumerate(panels):
        by_piece[piece].append((i, face))
    groups = [[] for _ in range(4)]
    for points in by_piece.values():
        phase = (0 if len(points) == 3 else
                 (1 if any(face in (0, 3) for i, face in points) else 2) if len(points) == 2 else 3)
        groups[phase].extend(i for i, face in points)
    return tuple(tuple(sorted(g)) for g in groups if g)


def _seed_words(kind):
    """Short stabilizers; formulas are checked against every physical panel.

    References: Jaap's cube223.htm and cube334.htm. Sides in those notations
    are half turns. Inner u/d are expressed as legal nested band differences.
    """
    if kind not in FIXED_SHAPE_KINDS:
        return
    import re
    from cube.cuboid import PARTITIONS, FACES
    from cube.polyhedral import Move
    cube = CuboidCube.solved(kind)
    def token(label, amount):
        axis = FACES.index(label.upper())
        a = next(i for i, v in enumerate(cube.geometry.spec.axes[axis]) if v)
        widths = PARTITIONS[cube.core_n, cube.dimensions[a]]
        if axis >= 3:
            widths = widths[::-1]
        count = amount if label.upper() in ('U', 'D') else 2*amount
        if label.isupper():
            return (Move(axis, widths[0]-1, count % 4),)
        if len(widths) < 3:
            return ()
        return (Move(axis, sum(widths[:2])-1, count % 4), Move(axis, widths[0]-1, -count % 4))
    formulas = (
        "R D B R U2 R U2 R U2 B D' R", "R U2 R U2 R",
        "u' R u R d' R d R F d F", "R u2 F u' R u d R d' F u2 R u'",
        "R F L d L F R u", "R F L u L F R d", "u R F L d L F R",
        "d R F L u L F R", "R F L d2 L F R u2", "R F L u2 L F R d2",
        "u2 R F L d2 L F R", "d2 R F L u2 L F R",
        "R U2 R U2 R U2", "R U D' F U' D",
    )
    for formula in formulas:
        word = []
        valid = True
        for text in formula.split():
            match = re.fullmatch("([URFDLBud])(2|')?", text)
            label, suffix = match.groups()
            if label.islower() and cube.dimensions[1] < 3:
                valid = False; break
            word.extend(token(label, 2 if suffix == '2' else 3 if suffix == "'" else 1))
        if valid and all(cube.can_apply(m) for m in word):
            yield simplify(word, 4)


def build_phase_tables(kind, report=None):
    adapter = mechanism(kind)[0]
    order = adapter.geometry.spec.turn_order
    def cost(word):
        bank = getattr(adapter, 'words', None)
        return sum(len(bank[m.axis])*min(m.amount % adapter.orders[m.axis],
                    -m.amount % adapter.orders[m.axis]) for m in word) if bank else len(word)
    chain = chain_for(kind)
    identity = tuple(range(len(adapter.geometry.stickers)))
    primitive = [(adapter.geometry.permutation(m), (m,)) for m in adapter.moves()]
    setups = [(identity, ())]+primitive
    seeds = []
    for word in _seed_words(kind):
        perm = identity
        for move in word:
            perm = compose(perm, adapter.geometry.permutation(move))
        seeds.append((perm, word))
    strong = []
    for generators in chain.generators:
        for perm, word in generators:
            if word.length <= 2000:
                strong.append((perm, simplify(word.flatten(order), order)))
    previous = set(); tables = []
    for points in phase_points(kind):
        local = {p: i for i, p in enumerate(points)}
        target = tuple(range(len(points)))
        macros = {}
        def offer(perm, word):
            if any(perm[p] != p for p in previous):
                return
            projected = tuple(local[perm[p]] for p in points)
            if projected == target:
                return
            for p, w in ((projected, word), (inverse(projected), inverse_word(word, order))):
                if p not in macros or cost(w) < cost(macros[p]):
                    macros[p] = tuple(w)
        for perm, word in primitive+strong:
            offer(perm, word)
        for perm, word in seeds:
            for setup, prefix in setups:
                conjugate = compose(compose(setup, perm), inverse(setup))
                offer(conjugate, simplify(prefix+word+inverse_word(prefix, order), order))
        # Short residuals retain the previously solved phases. This captures
        # centre/core-frame corrections which are invisible on the corners.
        for perm, word in primitive+seeds:
            current = perm; residual = list(word); valid = True
            for old_points, old_macros, old_reachable in tables:
                old_local = {p: i for i, p in enumerate(old_points)}
                state = bytes(old_local[current[p]] for p in old_points)
                if state not in old_reachable:
                    valid = False; break
                while old_reachable[state][0] is not None:
                    parent, index = old_reachable[state]
                    moves = inverse_word(old_macros[index][1], order)
                    for move in moves:
                        current = compose(current, adapter.geometry.permutation(move))
                    residual.extend(moves); state = parent
            if valid:
                offer(current, simplify(residual, order))
        chosen = []
        reachable = {bytes(target): (None, None)}
        for perm, word in sorted(macros.items(), key=lambda p: cost(p[1])):
            if bytes(perm) in reachable:
                continue
            chosen.append((perm, word))
            inverse_perm = inverse(perm)
            if inverse_perm != perm:
                chosen.append((inverse_perm, inverse_word(word, order)))
            reachable = {bytes(target): (None, None)}
            pending = deque([bytes(target)])
            maps = [bytes(p) for p, w in chosen]
            while pending:
                state = pending.popleft()
                for index, action in enumerate(maps):
                    nxt = state.translate(action+bytes(range(len(action), 256)))
                    if nxt not in reachable:
                        reachable[nxt] = (state, index); pending.append(nxt)
        if report:
            report(len(tables), len(reachable), len(chosen))
        tables.append((points, tuple(chosen), reachable))
        previous.update(points)
    return tables


def write_phase_tables(kind, destination, report=None):
    encoded = []
    for points, macros, reachable in build_phase_tables(kind, report):
        states = sorted(reachable); index = {p: i for i, p in enumerate(states)}
        parents = array('I', (index[reachable[p][0]] if reachable[p][0] is not None else i for i, p in enumerate(states)))
        if __import__('sys').byteorder != 'little':
            parents.byteswap()
        actions = bytes(reachable[p][1] if reachable[p][1] is not None else 255 for p in states)
        encoded.append({'points': points, 'macros': [[[m.axis, m.layer, m.amount] for m in w] for p, w in macros],
                        'states': base64.b64encode(b''.join(states)).decode('ascii'),
                        'parents': base64.b64encode(parents.tobytes()).decode('ascii'),
                        'actions': base64.b64encode(actions).decode('ascii')})
    adapter = mechanism(kind)[0]
    payload = json.dumps({'kind': kind, 'tables': encoded, 'order': adapter.geometry.spec.turn_order,
                          'fingerprint': getattr(adapter, 'fingerprint', '')}, separators=(',', ':')).encode()
    Path(destination).write_bytes(b'CS01'+zlib.compress(payload, 9))


class PhaseTable:
    def __init__(self, record, order=4):
        from cube.polyhedral import Move
        self.points = tuple(record['points']); self.width = len(self.points)
        self.order = order
        self.states = base64.b64decode(record['states'])
        self.parents = array('I'); self.parents.frombytes(base64.b64decode(record['parents']))
        if __import__('sys').byteorder != 'little':
            self.parents.byteswap()
        self.actions = base64.b64decode(record['actions'])
        self.macros = tuple(tuple(Move(*m) for m in word) for word in record['macros'])
        if not self.width or len(self.states) != self.width*len(self.parents) or len(self.actions) != len(self.parents):
            raise ValueError('Invalid cuboid phase table')

    def find(self, state):
        low, high = 0, len(self.parents)
        while low < high:
            middle = (low+high)//2
            value = self.states[middle*self.width:(middle+1)*self.width]
            if value < state:
                low = middle+1
            else:
                high = middle
        return low if self.states[low*self.width:(low+1)*self.width] == state else None

    def solve(self, state):
        index = self.find(state)
        if index is None:
            return None
        result = []
        while self.actions[index] != 255:
            result.extend(inverse_word(self.macros[self.actions[index]], self.order))
            index = self.parents[index]
        return tuple(result)


@lru_cache(maxsize=1)
def phase_tables(kind):
    payload = (Path(__file__).parent/'data'/f'{kind}_phases.bin').read_bytes()
    if payload[:4] != b'CS01':
        raise ValueError('Invalid cuboid phase version')
    data = json.loads(zlib.decompress(payload[4:]))
    if data['kind'] != kind:
        raise ValueError('Wrong cuboid phase model')
    adapter = mechanism(kind)[0]
    if data.get('fingerprint', '') != getattr(adapter, 'fingerprint', ''):
        raise ValueError('Cuboid macro and phase table versions differ')
    return tuple(PhaseTable(r, data.get('order', 4)) for r in data['tables'])


@lru_cache(maxsize=3)
def chain_for(kind):
    return StabilizerChain(mechanism(kind)[0])


def normalize(cube, cancel=None):
    """Recover physical home identities from manually painted panels."""
    cells, boxes, entries, lookup, base = layout(cube.puzzle_kind)
    if getattr(cube, 'panel_anchored', False):
        if all(color == sticker.face for color, sticker in zip(cube.colors, base.stickers)):
            return cube
        canonical = False
    else:
        canonical = True
    for piece, frame in (() if getattr(cube, 'panel_anchored', False) else enumerate(cube.frames)):
        for face, normal in enumerate(base.spec.normals):
            axis, sign = next((a, v) for a, v in enumerate(normal) if v)
            home = next((p for p in cells[piece] if p[axis] == sign*(cube.core_n-1)), None)
            if home is not None and cube.colors[lookup[transform(frame, home), transform(frame, normal)]] != face:
                canonical = False; break
        if not canonical:
            break
    if canonical:
        return cube
    from cube.cuboid_observation import SixViewDraft
    class Cancel:
        def is_set(self):
            return bool(cancel and cancel())
    result = SixViewDraft.from_cube(cube).match(seconds=10., cancel=Cancel())
    if result.status == 'cancelled':
        raise InterruptedError()
    if result.status != 'ok':
        raise ValueError('cuboid.identity_'+result.status)
    return result.cube


def panel_state(cube):
    _, panels, representatives, point_at = mechanism(cube.puzzle_kind)
    cells, boxes, entries, lookup, base = layout(cube.puzzle_kind)
    result = []
    for (piece, face), slot in zip(panels, representatives):
        home, normal = entries[slot]
        frame = cube.frames[piece]
        result.append(point_at[lookup[transform(frame, home), transform(frame, normal)]])
    if len(set(result)) != len(result):
        raise ValueError('cuboid.identity_conflict')
    return tuple(result)


def equivalent_labels(kind, state):
    """Unmarked single-colour centres can exchange their invisible labels."""
    _, panels, _, _ = mechanism(kind)
    by_piece = defaultdict(list)
    for index, (piece, face) in enumerate(panels):
        by_piece[piece].append((index, face))
    groups = defaultdict(list)
    for piece, points in by_piece.items():
        if len(points) == 1:
            index, face = points[0]; groups[face].append(index)
    choices = [tuple(ids) for ids in groups.values() if len(ids) == 2]
    for mask in range(1 << len(choices)):
        candidate = list(state)
        for bit, (a, b) in enumerate(choices):
            if mask & (1 << bit):
                candidate[a], candidate[b] = candidate[b], candidate[a]
        yield tuple(candidate)


def solve_fixed_cuboid(cube, cancel=None, progress=None):
    canonical = normalize(cube, cancel)
    if cancel and cancel():
        raise InterruptedError()
    tables = phase_tables(cube.puzzle_kind)
    geometry = mechanism(cube.puzzle_kind)[0].geometry
    state = panel_state(canonical)
    for labels in equivalent_labels(cube.puzzle_kind, state):
        if cancel and cancel():
            raise InterruptedError()
        current = tuple(labels); word = []; valid = True
        for phase, table in enumerate(tables):
            local = {p: i for i, p in enumerate(table.points)}
            projected = bytes(local[current[p]] for p in table.points)
            moves = table.solve(projected)
            if moves is None:
                valid = False; break
            for move in moves:
                current = compose(current, geometry.permutation(move))
            word.extend(moves)
            if progress:
                progress(phase+1, len(tables))
        if not valid:
            continue
        moves = simplify(word, 4)
        replay = cube.entered()
        for move in moves:
            if cancel and cancel():
                raise InterruptedError()
            replay.apply_move(move)
        if replay.is_solved():
            if progress:
                progress(1, 1)
            return moves
    raise ValueError('cuboid.identity_unreachable')
