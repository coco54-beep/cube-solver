"""Build source-independent legal Tangram algorithms (offline SymPy only)."""
import sys
import json
import zlib
from collections import deque
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sympy.combinatorics import Permutation, PermutationGroup
from cube.articulated_observation import polygon_key
from solver.tangram_geometry import geometry


def build(kind):
    model = geometry(kind)
    cube = model.cube
    root = tuple(cube.frames)
    root_shape = model.shape(root)
    slots, homes = {}, []
    for h in range(len(cube.solids)):
        indices = []
        for poly, color in cube.placed_faces(h):
            if color < 0:continue
            atom = len(slots)
            indices.append(atom)
            slots[polygon_key(poly)] = atom
        homes.append(indices)
    images = {}
    def permutation(frames):
        output = [-1] * len(slots)
        for home, pose in enumerate(frames):
            if (home,pose) not in images:
                images[home,pose] = tuple(slots.get(polygon_key(p), -1) for p, color in cube.placed_faces(home, pose) if color >= 0)
            targets = images[home,pose]
            for atom, target in zip(homes[home], targets):output[atom] = target
        return None if sorted(output) != list(range(len(output))) else Permutation(output)
    loops = {}
    def remember(frames, word):
        if model.shape(frames) != root_shape:return
        p = permutation(frames)
        if p is None or p.is_identity:return
        if p not in loops or len(word) < len(loops[p]):loops[p] = tuple(word)
    for child, move in model.children(root):remember(child, (move,))
    original = list(loops.items())
    for p, pw in original:
        for q, qw in original:
            word = pw + qw + tuple(m.inverse(6) for m in reversed(pw)) + tuple(m.inverse(6) for m in reversed(qw))
            frames = root
            for move in word:
                frames = model.apply(frames, move)
                if frames is None:break
            if frames is not None:remember(frames, word)
    if kind == 'tangram_extreme':
        # Close source-independent paths through non-cubic geometry. These
        # cycles supply fine-piece actions absent from the ordinary mechanism.
        states = {root_shape:(root,())}
        pending = deque((root_shape,))
        while pending:
            frames, prefix = states[pending.popleft()]
            if len(prefix) >= 5:continue
            for child, move in model.children(frames):
                key = model.shape(child)
                if key not in states:
                    states[key] = child, prefix+(move,)
                    pending.append(key)
        for frames, prefix in states.values():
            for child, move in model.children(frames):
                key = model.shape(child)
                if key not in states:continue
                closing = tuple(m.inverse(6) for m in reversed(states[key][1]))
                closed = child
                for back in closing:
                    closed = model.apply(closed, back)
                    if closed is None:raise RuntimeError('Geometry closure is not legal')
                remember(closed, prefix+(move,)+closing)
        print('shape graph',len(states),'closed algorithms',len(loops),flush=True)
    pairs = sorted(loops.items(), key=lambda p: (len(p[0].support()), len(p[1])))
    selected = []
    for p, word in pairs:
        if not selected or not group.contains(p):
            selected.append(p)
            group = PermutationGroup(selected)
            group.schreier_sims()
    # Keep the independent basis and small useful cycles. All other loops
    # were used to establish membership before being dropped from the asset.
    pairs = [(p,w) for p,w in pairs if p in selected or len(p.support()) <= 6]
    group._schreier_sims(base=list(range(len(slots))))
    print(kind, 'atoms', len(slots), 'loops', len(pairs), 'independent', len(selected), 'order', group.order(), flush=True)
    generators = [p for p, _ in pairs]
    words = [word for _, word in pairs]
    # Verify all exported primitive algorithms on the collision-checking model.
    for p, word in pairs:
        trial = cube.clone()
        trial.apply_moves(word)
        if permutation(trial.frames) != p:raise RuntimeError('Algorithm replay differs')
    strong = list(group.strong_gens) + [p for p in generators if p not in group.strong_gens]
    lookup = {p: i+1 for i, p in enumerate(strong)}
    originals = {p: i for i, p in enumerate(generators)}
    def reference(p):return lookup[p] if p in lookup else -lookup[p**-1]
    records = [dict(permutation=p.array_form, original=originals.get(p),
                    product=[] if p in originals else [reference(q) for q in group._strong_gens_slp[p]]) for p in strong]
    from solver.tangram_table import geometry_fingerprint
    data = dict(version=1, kind=kind, geometry=geometry_fingerprint(kind), degree=len(slots), base=group.base,
                moves=[[[m.axis,m.layer,m.amount] for m in w] for w in words], strong=records,
                transversals=[{str(beta):dict(permutation=p.array_form, product=group._transversal_slp[i][beta])
                               for beta,p in orbit.items()} for i,orbit in enumerate(group.basic_transversals)])
    path = Path('solver/data')/(kind+'_group.bin')
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print('saved',path,path.stat().st_size,'bytes','strong',len(strong),flush=True)


def finish(kind):
    """Compile reusable short loops, verify them, then install the asset."""
    from tools.optimize_tangram_tables import optimize
    from tools.augment_tangram_algorithms import augment
    from tools.shorten_tangram_transversals import shorten
    from solver.tangram_table import TangramTable
    source=Path('solver/data')/(kind+'_group.bin')
    if kind=='tangram_extreme':
        source=optimize(kind,source)
        source=augment(kind,source)
        source=optimize(kind,source)
    path=shorten(kind,source)
    table=TangramTable(kind,path)
    model=table.model
    root=tuple(model.cube.frames)
    for index,record in enumerate(table.records):
        state=root
        for move in table.strong_word(index+1):
            state=model.apply(state,move)
            if state is None:raise RuntimeError('Illegal compiled loop')
        if model.shape(state)!=model.shape(root) or table.element(state)!=tuple(record['permutation']):
            raise RuntimeError('Compiled loop permutation differs')
    target=Path('solver/data')/(kind+'_group.bin')
    target.write_bytes(path.read_bytes())
    print('verified and installed',target,flush=True)


if __name__ == '__main__':
    kind=sys.argv[1] if len(sys.argv)>1 else 'tangram'
    build(kind)
    finish(kind)
