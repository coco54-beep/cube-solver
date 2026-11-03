"""Memory-bounded legal-turn search for bandaged cuboid mechanisms.

Offline pattern databases keep the large brick in every pattern. Missing
pieces relax constraints; the maximum pattern distance is admissible.
"""
from functools import lru_cache
from pathlib import Path
from itertools import product
from time import monotonic
import json
import zlib
import heapq
import hashlib
import struct
from array import array

from cube.appearance import ROTATIONS
from cube.cuboid import CuboidCube, layout, transform, multiply, turn_frame, IDENTITY
from cube.polyhedral import CUBE, Move


@lru_cache(maxsize=1)
def search_model(kind):
    cube = CuboidCube.solved(kind); cells, boxes, entries, lookup, base = layout(kind)
    atoms = tuple(Move(a, l, amount) for a in range(6) for l in range(cube.core_n-1)
                  for amount in range(base.spec.step(a), 4, base.spec.step(a)))
    frame_at = {frame: i for i, frame in enumerate(ROTATIONS)}
    rotations = {m: turn_frame(m.axis, m.amount) for m in atoms}
    transitions = []; legal = []; goals = []; aliases = []
    home_panels = {p: tuple({s.face for s in base.stickers if s.piece == p}) for p in range(len(cells))}
    bounds = getattr(cube, 'shell_bounds', ((-2., 3.),)*3 if kind == 'camouflage_3' else tuple((-d/2, d/2) for d in cube.dimensions))
    for piece, group in enumerate(cells):
        equivalence = {}; canonical = []
        for f, frame in enumerate(ROTATIONS):
            body = [transform(frame, c) for c in product(*boxes[piece])]
            signature = (tuple(sorted(transform(frame, p) for p in group)),
                         tuple((min(p[a] for p in body), max(p[a] for p in body)) for a in range(3)),
                         tuple(transform(frame, CUBE[face]) for face in home_panels[piece]))
            canonical.append(equivalence.setdefault(signature, f))
        aliases.append(tuple(canonical))
        rows = []; masks = []; target = []
        for f, frame in enumerate(ROTATIONS):
            current = tuple(transform(frame, p) for p in group); row = []; allowed = 0
            for i, m in enumerate(atoms):
                a, sign = next((a, v) for a, v in enumerate(CUBE[m.axis]) if v)
                threshold = cube.core_n-1-2*m.layer
                selected = {sign*p[a] >= threshold for p in current}
                dest = 255 if len(selected) != 1 else frame_at[multiply(rotations[m], frame)] if True in selected else f
                row.append(canonical[dest] if dest != 255 else 255)
                if dest != 255:
                    allowed |= 1 << i
            rows.append(bytes(row)); masks.append(allowed)
            solved_pose = (cube.pose_is_solved(piece, frame) if hasattr(cube, 'pose_is_solved') else
                (all(transform(frame, CUBE[face]) == CUBE[face] for face in home_panels[piece]) and
                all(bounds[a][0]-1e-8 <= p[a] <= bounds[a][1]+1e-8
                    for corner in product(*boxes[piece]) for p in (transform(frame, corner),) for a in range(3))))
            if solved_pose:
                target.append(canonical[f])
        transitions.append(tuple(rows)); legal.append(tuple(masks)); goals.append(tuple(sorted(set(target))))
    anchor = max(range(len(cells)), key=lambda p: len(cells[p]))
    others = sorted((p for p in range(len(cells)) if p != anchor), key=lambda p: (-len(cells[p]), -len(home_panels[p]), p))
    patterns = tuple((anchor,)+tuple(others[i:i+3]) for i in range(0, len(others), 3))
    return atoms, tuple(transitions), tuple(legal), tuple(goals), patterns, tuple(aliases)


def build_patterns(kind, destination, report=None, strong=True, model=None, metadata=None):
    """Developer-only generator; never builds search tables on a phone."""
    import numpy as np
    atoms, transitions, legal, goals, patterns, aliases = model or search_model(kind)
    if strong:
        cells = layout(kind)[0]
        heavy = sorted(range(len(cells)), key=lambda p: (-len(cells[p]), p))
        extra = (tuple(heavy[:5]), tuple(heavy[:3]+heavy[5:7]))
        patterns += tuple(p for p in extra if len(p) == 5)
    records = []; blobs = []
    for number, pieces in enumerate(patterns):
        count = 24**len(pieces)
        coordinates = (np.indices((24,)*len(pieces), dtype=np.int32).reshape(len(pieces), count)
                       if len(pieces) <= 4 else None)
        weights = np.array([24**i for i in range(len(pieces)-1, -1, -1)], dtype=np.int32)
        targets = []
        action_tables = []
        unique = set()
        for i, atom in enumerate(atoms):
            table = np.stack([np.frombuffer(b''.join(transitions[p]), dtype=np.uint8).reshape(24, -1)[:, i] for p in pieces])
            signature = table.tobytes()
            if signature in unique:
                continue
            unique.add(signature); action_tables.append(table)
            if coordinates is None:
                continue
            mapped = np.stack([table[j][coordinates[j]] for j in range(len(pieces))]).astype(np.int32)
            valid = np.all(mapped != 255, axis=0)
            result = (mapped*weights[:, None]).sum(axis=0).astype(np.int32)
            result[~valid] = -1; targets.append(result)
        distance = np.full(count, 255, dtype=np.uint8)
        initial = np.array([sum(v*w for v, w in zip(values, weights)) for values in product(*(goals[p] for p in pieces))], dtype=np.int32)
        distance[initial] = 0; frontier = initial; depth = 0
        while len(frontier):
            following = []
            decoded = None
            if coordinates is None:
                decoded = [(frontier//w) % 24 for w in weights]
            for action, table in enumerate(action_tables):
                if decoded is None:
                    nxt = targets[action][frontier]; nxt = nxt[nxt >= 0]
                else:
                    mapped = [table[j][decoded[j]] for j in range(len(pieces))]
                    valid = np.logical_and.reduce([v != 255 for v in mapped])
                    nxt = sum(v.astype(np.int32)*w for v, w in zip(mapped, weights))[valid]
                nxt = nxt[distance[nxt] == 255]
                if len(nxt):
                    nxt = np.unique(nxt); distance[nxt] = depth+1; following.append(nxt)
            frontier = np.concatenate(following) if following else np.array([], dtype=np.int32)
            depth += 1
        packed = len(pieces) > 4
        if packed:
            if np.any((distance > 14) & (distance != 255)):
                raise ValueError('Pattern exceeds nibble distance range')
            values = np.where(distance == 255, 15, distance)
            payload = (values[::2] | (values[1::2] << 4)).tobytes()
        else:
            payload = distance.tobytes()
        records.append({'pieces': pieces, 'packed': packed, 'size': len(payload)})
        blobs.append(payload)
        if report:
            report(number+1, len(patterns), int(np.count_nonzero(distance != 255)), int(distance[distance != 255].max()))
    header = json.dumps({'kind': kind, 'patterns': records, **(metadata or {})}, separators=(',', ':')).encode()
    Path(destination).write_bytes(b'CP02'+struct.pack('<I', len(header))+header+zlib.compress(b''.join(blobs), 9))


@lru_cache(maxsize=1)
def pattern_tables(kind):
    payload = (Path(__file__).parent/'data'/f'{kind}_patterns.bin').read_bytes()
    if payload[:4] != b'CP02':
        raise ValueError('Invalid cuboid search table')
    size = struct.unpack_from('<I', payload, 4)[0]; data = json.loads(payload[8:8+size])
    if data['kind'] != kind:
        raise ValueError('Wrong cuboid search model')
    blob = memoryview(zlib.decompress(payload[8+size:])); offset = 0; result = []
    for record in data['patterns']:
        count = record['size']
        if count != (24**len(record['pieces'])//2 if record['packed'] else 24**len(record['pieces'])):
            raise ValueError('Invalid cuboid pattern width')
        result.append((tuple(record['pieces']), blob[offset:offset+count], record['packed']))
        offset += count
    if offset != len(blob):
        raise ValueError('Invalid cuboid pattern data')
    return tuple(result)


@lru_cache(maxsize=1)
def packed_actions(kind):
    """Eight labelled pieces per byte alphabet; turns use C bytes.translate."""
    atoms, transitions, legal, goals, patterns, aliases = search_model(kind)
    masks = []
    for p, rows in enumerate(legal):
        values = [0]*256; offset = (p % 8)*24
        values[offset:offset+24] = rows; masks.append(tuple(values))
    actions = []
    for index in range(len(atoms)):
        blocks = []
        for start in range(0, len(transitions), 8):
            table = bytearray(range(256))
            for p in range(start, min(start+8, len(transitions))):
                offset = (p % 8)*24
                for f in range(24):
                    dest = transitions[p][f][index]
                    table[offset+f] = offset+dest if dest != 255 else 255
            blocks.append(bytes(table))
        actions.append(tuple(blocks))
    return tuple(masks), tuple(actions)


def packed_turn(state, tables):
    if len(tables)==4:
        # Camouflage and the common 4x4 cuboid layouts occupy four blocks.
        # Avoid a generator, zip and join on every expanded search edge.
        return (state[:8].translate(tables[0])+state[8:16].translate(tables[1])
                +state[16:24].translate(tables[2])+state[24:32].translate(tables[3]))
    return b''.join(state[start:start+8].translate(table) for start, table in zip(range(0, len(state), 8), tables))


def camouflage_anchor(state,cancel=None,kind='camouflage_3'):
    """Hold the unique 2x2x2 corner brick fixed, using actual legal turns.

    Every bonded span is contained in one side of each zero plane. Therefore
    complementary half-cube turns always implement a whole rotation. A legal
    slab turn moving the anchor has an equivalent complementary slab turn in
    the anchor's frame. After alignment, excluding anchor turns preserves
    reachability, while removing the 24 equivalent global holdings.
    """
    from collections import deque
    atoms,transitions,legal,goals,_,aliases=search_model(kind)
    masks,actions=packed_actions(kind)
    cells=layout(kind)[0];anchor=max(range(len(cells)),key=lambda p:len(cells[p]))
    target=(anchor%8)*24+aliases[anchor][ROTATIONS.index(IDENTITY)]
    whole=tuple((atoms.index(Move(face,1,amount)),atoms.index(Move((face+3)%6,1,(-amount)%4)))
                for face in range(3) for amount in (1,2,3))
    pending=deque([(state,())]);seen={state[anchor]}
    while pending:
        if cancel and cancel():raise InterruptedError()
        current,prefix=pending.popleft()
        if current[anchor]==target:
            pose=target-(anchor%8)*24
            fixed=sum(1<<i for i,dest in enumerate(transitions[anchor][pose]) if dest==pose)
            return current,prefix,fixed
        for pair in whole:
            child=current
            for index in pair:
                if any(not masks[p][f]&(1<<index) for p,f in enumerate(child)):break
                child=packed_turn(child,actions[index])
            else:
                if child[anchor] not in seen:
                    seen.add(child[anchor]);pending.append((child,prefix+tuple(atoms[i] for i in pair)))
    raise ValueError('cuboid.identity_unreachable')


def build_endgame(kind, destination, maximum=220000, depth=5, report=None):
    if not 1 <= depth <= 5:
        raise ValueError('Endgame depth must fit the 30-bit word encoding')
    atoms, transitions, legal, goals, patterns, aliases = search_model(kind)
    identity = ROTATIONS.index(IDENTITY)
    start = bytes((p % 8)*24+a[identity] for p, a in enumerate(aliases))
    masks, actions = packed_actions(kind)
    inverses = {i: atoms.index(m.inverse(4)) for i, m in enumerate(atoms)}
    records = {start: (0, 0)}; frontier = [start]; full = (1 << len(atoms))-1
    for level in range(depth):
        following = []; stop = False
        for state in frontier:
            mask = full
            for p, f in enumerate(state):
                mask &= masks[p][f]
            word, count = records[state]
            while mask:
                bit = mask & -mask; mask ^= bit; i = bit.bit_length()-1
                nxt = packed_turn(state, actions[i])
                if nxt not in records:
                    records[nxt] = (inverses[i]+(word << 6), count+1); following.append(nxt)
                    if len(records) >= maximum:
                        stop = True; break
            if stop:
                break
        if report:
            report(level+1, len(records), len(following))
        frontier = following
        if stop or not frontier:
            break
    keyed = {}
    for state, value in records.items():
        digest = int.from_bytes(hashlib.blake2b(state, digest_size=8).digest(), 'little')
        keyed.setdefault(digest, value)
    keys = sorted(keyed)
    blob = (struct.pack('<'+'Q'*len(keys), *keys)+struct.pack('<'+'I'*len(keys), *(keyed[k][0] for k in keys))+
            bytes(keyed[k][1] for k in keys))
    header = json.dumps({'kind': kind, 'count': len(keys)}, separators=(',', ':')).encode()
    Path(destination).write_bytes(b'CG02'+struct.pack('<I', len(header))+header+zlib.compress(blob, 9))


@lru_cache(maxsize=1)
def endgame_table(kind):
    payload = (Path(__file__).parent/'data'/f'{kind}_endgame.bin').read_bytes()
    if payload[:4] != b'CG02':
        raise ValueError('Invalid cuboid endgame version')
    size = struct.unpack_from('<I', payload, 4)[0]; header = json.loads(payload[8:8+size])
    if header['kind'] != kind:
        raise ValueError('Wrong cuboid endgame model')
    count = header['count']; blob = zlib.decompress(payload[8+size:])
    if not 0 < count <= 1000000 or len(blob) != 13*count:
        raise ValueError('Invalid cuboid endgame data')
    keys = array('Q'); keys.frombytes(blob[:count*8])
    words = array('I'); words.frombytes(blob[count*8:count*12])
    if __import__('sys').byteorder != 'little':
        keys.byteswap(); words.byteswap()
    return keys, words, blob[count*12:]


def solve_bandaged_cuboid(original, cancel=None, progress=None, seconds=None):
    """Try fast orderings, then continue a complete cancellable search.

    Overlapping pattern distances can favour a long dead end. Counting
    physically misplaced pieces provides an independent ordering, while every
    candidate still uses the same exact legal moves and final replay.
    """
    deadline=monotonic()+seconds if seconds is not None else float('inf')
    attempts=((4.,(1.,1.,0.,0.)),(4.,(.1,1.,0.,0.)),
              (4.,(5.,5.,1.,1.)),(5.,(1.,0.,1.,2.)),
              (5.,(1.,1.,0.,1.)),(7.,(1.,1.,0.,2.)),(5.,(1.,0.,5.,1.)))
    if original.puzzle_kind not in ('camouflage_3','mirror_camouflage_3') or seconds is not None and seconds<10:
        return _search_bandaged_cuboid(original,cancel,progress,seconds)
    from cube.cuboid import CuboidCube
    if isinstance(original,CuboidCube):
        # Always-legal half-cube turns absorb corner permutations. Search the
        # much smaller remaining graph before the full physical graph. This
        # bounded shortcut has its own visited set and never prunes fallback.
        from solver.camouflage_reduction import solve_octants
        remaining=deadline-monotonic()
        if remaining<=0:raise TimeoutError('cuboid.search_budget')
        try:
            word=solve_octants(original,cancel,seconds=min(3.,remaining))
        except FileNotFoundError:
            word=None  # Optional acceleration data may be absent in old installs.
        if word is not None:
            if progress:progress(1,1)
            return word
    context={}
    for budget,weights in attempts:
        if cancel and cancel():raise InterruptedError()
        remaining=deadline-monotonic()
        if remaining<=0:raise TimeoutError('cuboid.search_budget')
        try:
            return _search_bandaged_cuboid(original,cancel,progress,min(budget,remaining),
                                           weights=weights,fast_fraction=1.,_context=context)
        except TimeoutError:pass
    remaining=deadline-monotonic()
    if remaining<=0:raise TimeoutError('cuboid.search_budget')
    return _search_bandaged_cuboid(original,cancel,progress,None if seconds is None else remaining,
                                   _context=context)


def _search_bandaged_cuboid(original, cancel=None, progress=None, seconds=45., *, weights=(1.,1.,0.,0.), fast_fraction=.8,
                            _context=None):
    from solver.cuboid_static import normalize
    if cancel and cancel():raise InterruptedError()
    context={} if _context is None else _context
    if 'cube' not in context:context['cube']=normalize(original,cancel)
    cube=context['cube']
    atoms, transitions, legal, goals, _, aliases = search_model(cube.puzzle_kind)
    tables=pattern_tables(cube.puzzle_kind)
    frame_at = {frame: i for i, frame in enumerate(ROTATIONS)}
    start = bytes((p % 8)*24+aliases[p][frame_at[f]] for p, f in enumerate(cube.frames))
    goal_sets = tuple(frozenset((p % 8)*24+f for f in g) for p, g in enumerate(goals))
    masks, actions = packed_actions(cube.puzzle_kind)
    if 'alignment' not in context:
        aligned,prefix,fixed=(camouflage_anchor(start,cancel,cube.puzzle_kind) if cube.puzzle_kind in ('camouflage_3','mirror_camouflage_3')
                              else (start,(),(1<<len(atoms))-1))
        context['alignment']=aligned,prefix,fixed
    start,alignment,fixed_moves=context['alignment']
    four = []; five = []; small = []
    for pieces, distances, packed in tables:
        offset = 0
        for p in pieces:
            offset = offset*24+(p % 8)*24
        if len(pieces) == 4:
            four.append((*pieces, offset, distances))
        elif len(pieces) == 5:
            five.append((*pieces, offset, distances))
        else:
            small.append((pieces, offset, distances))
    def estimates(state):
        best = 0; total = 0
        for a, b, c, d, offset, distances in four:
            value = distances[((state[a]*24+state[b])*24+state[c])*24+state[d]-offset]
            if value > best:
                best = value
            total += value
        for a, b, c, d, e, offset, distances in five:
            index = (((state[a]*24+state[b])*24+state[c])*24+state[d])*24+state[e]-offset
            value = (distances[index//2] >> (4*(index % 2))) & 15
            if value == 15:
                value = 255
            if value > best:
                best = value
            total += value
        for pieces, offset, distances in small:
            index = 0
            for p in pieces:
                index = 24*index+state[p]
            value = distances[index-offset]
            if value > best:
                best = value
            total += value
        return best, total
    # Search orderings share only immutable facts about a physical state.
    # Their visited sets stay separate: failure in a bounded search must not
    # prune a branch from the complete fallback. These caches are per solve.
    if 'estimates' not in context:
        context['estimates']=lru_cache(maxsize=16000)(estimates)
    estimates=context['estimates']
    def heuristic(state):
        return estimates(state)[0]
    deadline = monotonic()+seconds if seconds is not None else float('inf'); nodes = 0; path = []; seen = {}
    groups = tuple((m.axis % 3, m.axis* cube.core_n+m.layer) for m in atoms)
    endings = endgame_table(cube.puzzle_kind)
    def ending(state):
        import bisect
        keys, words, counts = endings
        digest = int.from_bytes(hashlib.blake2b(state, digest_size=8).digest(), 'little')
        i = bisect.bisect_left(keys, digest)
        if i >= len(keys) or keys[i] != digest:
            return None
        code = words[i]; tail = []; current = state
        for _ in range(counts[i]):
            index = code & 63; code >>= 6; tail.append(atoms[index])
            if any(not masks[p][f] & (1 << index) for p, f in enumerate(current)):
                return None
            current = packed_turn(current, actions[index])
        # Fingerprints are only an index. Full state checking prevents a
        # collision from ever accepting an incorrect or illegal solution.
        return tuple(tail) if all(f in goal_sets[p] for p, f in enumerate(current)) else None
    if 'ending' not in context:
        context['ending']=lru_cache(maxsize=8000)(ending)
    ending=context['ending']
    def children(state, last_axis=-1, last_band=-1):
        mask = fixed_moves
        for p, f in enumerate(state):
            mask &= masks[p][f]
        while mask:
            bit = mask & -mask; mask ^= bit; index = bit.bit_length()-1
            axis, band = groups[index]
            if axis == last_axis and band <= last_band:
                continue
            nxt = packed_turn(state, actions[index])
            if nxt != state:
                yield index, nxt
    def replay(word):
        word=tuple(alignment)+tuple(word)
        result = original.entered()
        for move in word:
            if cancel and cancel():
                raise InterruptedError()
            result.apply_move(move)
        if not result.is_solved():
            raise ValueError('cuboid.replay_failed')
        return tuple(word)
    # Find an economical legal answer before trying to prove the shortest
    # depth. Memory is capped explicitly, independently of the puzzle depth.
    initial_h, initial_score = estimates(start)
    wg,ws,wh,we=weights
    def priority(state,depth,h,score):
        incorrect=sum(f not in goal_sets[p] for p,f in enumerate(state)) if we else 0
        return wg*depth+ws*score+wh*h+we*incorrect
    records = [(start, -1, -1, 0, -1, -1)]
    pending = [(priority(start,0,initial_h,initial_score), initial_h, 0)]; best = {(start, -1): 0}
    fast_deadline = min(deadline, monotonic()+max(.1, seconds*fast_fraction)) if seconds is not None else 0.
    processed = {}
    while pending and monotonic() < fast_deadline:
        if cancel and cancel():
            raise InterruptedError()
        if len(records) >= 50000:
            keep = heapq.nsmallest(1500, (item for item in pending
                if best.get((records[item[2]][0], records[item[2]][5])) == records[item[2]][3]))
            needed = set()
            for _, _, index in keep:
                while index >= 0 and index not in needed:
                    needed.add(index); index = records[index][1]
            ordered = sorted(needed); remap = {old: new for new, old in enumerate(ordered)}
            records = [(s, remap.get(parent, -1), i, d, a, b)
                       for s, parent, i, d, a, b in (records[old] for old in ordered)]
            pending = [(score, h, remap[i]) for score, h, i in keep]; heapq.heapify(pending)
            best = {(s, b): d for s, _, _, d, _, b in records}
            if len(processed) > 50000:
                processed = dict(list(processed.items())[-25000:])
            if not pending:
                break
        _, h, record = heapq.heappop(pending)
        state, parent, move_index, depth, last_axis, last_band = records[record]
        if best.get((state, last_band)) != depth:
            continue
        if processed.get((state, last_band), 1000000) <= depth:
            continue
        processed[state, last_band] = depth
        tail = ending(state)
        if (h == 0 and all(f in goal_sets[p] for p, f in enumerate(state))) or tail is not None:
            word = []
            while parent >= 0:
                word.append(atoms[move_index]); record = parent
                state, parent, move_index, depth, last_axis, last_band = records[record]
            return replay(tuple(reversed(word))+(tail or ()))
        for index, nxt in children(state, last_axis, last_band):
            axis, band = groups[index]; key = (nxt, band)
            if best.get(key, 1000000) <= depth+1 or processed.get(key, 1000000) <= depth+1:
                continue
            next_h,score=estimates(nxt)
            if next_h==255:continue
            best[key] = depth+1; position = len(records)
            records.append((nxt, record, index, depth+1, axis, band))
            heapq.heappush(pending, (priority(nxt,depth+1,next_h,score), next_h, position))
            if len(records) >= 50000:
                break
    del records, pending, best, processed
    if seconds is None:
        from solver.complete_search import deepen,Exhausted
        def complete_children(node):
            state,last_axis,last_band=node
            for index,nxt in children(state,last_axis,last_band):
                h,score=estimates(nxt)
                if h!=255:yield (nxt,*groups[index]),atoms[index]
        def complete_goal(node):
            state=node[0]
            if all(f in goal_sets[p] for p,f in enumerate(state)):return ()
            return ending(state)
        def complete_estimate(node):return estimates(node[0])[1]
        def complete_progress(bound,expanded):
            if progress:progress(-1,0)
        try:
            word=deepen((start,-1,-1),complete_goal,complete_children,complete_estimate,
                        cancel=cancel,progress=complete_progress,cache_limit=50000,
                        resume_key=('cuboid-physical-v1',cube.puzzle_kind,fixed_moves))
        except Exhausted:raise ValueError('cuboid.identity_unreachable') from None
        return replay(word)
    def visit(state, remaining, last_axis=-1, last_band=-1, known_h=None):
        nonlocal nodes
        nodes += 1
        if nodes % 256 == 0:
            if cancel and cancel():
                raise InterruptedError()
            if monotonic() >= deadline:
                raise TimeoutError('cuboid.search_budget')
        h = heuristic(state) if known_h is None else known_h
        if h > remaining:
            return h
        if h == 0 and all(f in goal_sets[p] for p, f in enumerate(state)):
            return True
        tail = ending(state)
        if tail is not None and len(tail) <= remaining:
            path.extend(tail); return True
        key = (state, last_band)
        if seen.get(key, -1) >= remaining:
            return 1000000000
        if len(seen) < 50000:
            seen[key] = remaining
        candidates = ((*estimates(nxt),index,nxt) for index,nxt in children(state,last_axis,last_band))
        minimum = 1000000000
        for h, score, index, nxt in sorted(candidates):
            if h >= remaining:
                minimum = min(minimum, h+1); continue
            path.append(atoms[index])
            result = visit(nxt, remaining-1, *groups[index], known_h=h)
            if result is True:
                return True
            path.pop(); minimum = min(minimum, result+1)
        return minimum
    bound = initial_h
    if bound == 255:
        raise ValueError('cuboid.identity_unreachable')
    while bound < 1000000000:
        if cancel and cancel():
            raise InterruptedError()
        if monotonic() >= deadline:
            raise TimeoutError('cuboid.search_budget')
        if progress:
            progress(bound, bound+1)
        seen.clear(); result = visit(start, bound)
        if result is True:
            return replay(path)
        bound = max(bound+1, result)
    raise ValueError('cuboid.identity_unreachable')
