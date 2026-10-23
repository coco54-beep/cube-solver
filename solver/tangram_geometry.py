"""Finite rigid geometry for history-independent Tangram reduction.

Every permitted turn rotates a slab separated by the actual cut planes.
The solver checks those planes for every solid; no intersected solid is split.
Returned solutions must still be replayed on the physical cube model.
"""
import math
from collections import deque
from time import monotonic
from functools import lru_cache

from cube.articulated import ArticulatedCube, multiply, turn_frame, frame_key, vertices
from cube.appearance import transform_frame
from cube.appearance import ROTATIONS
from cube.articulated_observation import polygon_key
from cube.polyhedral import Move, dot


class TangramGeometry:
    def __init__(self, kind):
        self.cube = ArticulatedCube(kind)
        self.kind = kind
        cube = self.cube
        self.axes, self.cuts = cube._bands()
        self.moves = tuple(Move(axis, layer, amount)
                           for axis in range(4)
                           for layer in (range(3) if axis == 3 else (0,))
                           for amount in range(cube.step(axis, layer), 6, cube.step(axis, layer)))
        self.move_indices = {m: i for i, m in enumerate(self.moves)}
        self.features = {}
        shapes = {}
        for home, solid in enumerate(cube.solids):
            for pose, frame in enumerate(cube.orientations):
                faces = cube.placed_faces(home, pose)
                body = tuple(sorted(polygon_key(p) for p, _ in faces))
                skins = tuple(sorted(polygon_key(p) for p, color in faces if color >= 0))
                shape = solid.role, body, skins
                shape_id = shapes.setdefault(shape, len(shapes))
                points = vertices(faces)
                anchor = transform_frame(frame, solid.anchor)
                blocked = selected = 0
                for i, move in enumerate(self.moves):
                    axis, layer = move.axis, move.layer
                    boundaries = self.cuts[axis]
                    if axis == 3:
                        boundaries = boundaries[max(0, layer-1):min(len(boundaries), layer+1)]
                        membership = sum(dot(self.axes[axis], anchor) > b+1e-7 for b in self.cuts[axis]) == layer
                    else:
                        membership = dot(self.axes[axis], anchor) > self.cuts[axis][0]+1e-7
                    values = [dot(self.axes[axis], p) for p in points]
                    if any(min(values) < b-1e-7 and max(values) > b+1e-7 for b in boundaries):blocked |= 1 << i
                    if membership:selected |= 1 << i
                self.features[home, pose] = shape_id, blocked, selected
        self.turns = {}
        for pose, frame in enumerate(cube.orientations):
            for move in self.moves:
                turn = turn_frame(self.axes[move.axis], math.tau*move.amount/6)
                self.turns[pose, move] = cube._pose_index.get(frame_key(multiply(turn, frame)))
        proper = {frame_key(f) for f in ROTATIONS}
        self.odd = tuple(frame_key(f) not in proper for f in cube.orientations)
        # The uncoloured assembly uses only 88 distinct occupied positions in
        # Extreme. A bit for each geometric position avoids copying labels
        # and sorting 44 pieces at every shape-search edge.
        self.shape_rules=[]
        for index,move in enumerate(self.moves):
            blocked=0;shifts={};known={}
            for (home,pose),(sid,forbidden,selected) in self.features.items():
                target=self.features[home,self.turns[pose,move]][0] if selected&(1<<index) else sid
                rule=(bool(forbidden&(1<<index)),target)
                if sid in known:assert known[sid]==rule
                known[sid]=rule
            for sid,(forbidden,target) in known.items():
                if forbidden:blocked|=1<<sid
                shifts[target-sid]=shifts.get(target-sid,0)|(1<<sid)
            self.shape_rules.append((move,blocked,tuple(shifts.items())))
        self.root_code=self.shape_code(cube.frames)
        self._atlas = None

    def shape(self, frames):
        return tuple(sorted(self.features[h, p][0] for h, p in enumerate(frames)))

    def shape_code(self, frames):
        code=0
        for home,pose in enumerate(frames):code|=1<<self.features[home,pose][0]
        return code

    def shape_children(self, code):
        for move,blocked,shifts in self.shape_rules:
            if code&blocked:continue
            child=0
            for delta,mask in shifts:
                bits=code&mask
                child|=bits<<delta if delta>=0 else bits>>-delta
            if child!=code:yield child,move

    def apply(self, frames, move):
        index = self.move_indices.get(move)
        if index is None:return None
        bit = 1 << index
        features = [self.features[h, p] for h, p in enumerate(frames)]
        if any(f[1] & bit for f in features):return None
        moved = False
        following = list(frames)
        for home, (pose, feature) in enumerate(zip(frames, features)):
            if not feature[2] & bit:continue
            target = self.turns[pose, move]
            if target is None:return None
            following[home] = target
            moved = True
        return tuple(following) if moved else None

    def children(self, frames):
        features = [self.features[h, p] for h, p in enumerate(frames)]
        blocked = 0
        for feature in features:blocked |= feature[1]
        for index, move in enumerate(self.moves):
            bit = 1 << index
            if blocked & bit:continue
            child = tuple(self.turns[p, move] if f[2] & bit else p for p, f in zip(frames, features))
            if None not in child and child != frames:yield child, move

    def shape_atlas(self, cancel=None):
        if self._atlas is not None:return self._atlas
        root=self.root_code
        found={root:()};pending=deque(((root,()),))
        while pending:
            if cancel and cancel():raise InterruptedError()
            state,path=pending.popleft()
            if len(path)>=7:continue
            for child,move in self.shape_children(state):
                if child in found:continue
                word=path+(move,);found[child]=word;pending.append((child,word))
        self._atlas=found
        return found

    def restore_shape(self, frames, cancel=None, progress=None, seconds=20.):
        if self.shape_code(frames).bit_count()!=len(frames):raise ValueError('rigid.invalid')
        roots=self.shape_atlas(cancel)
        begun=monotonic();beam=[(self.shape_code(frames),())];seen=set()
        for depth in range(60):
            if cancel and cancel():raise InterruptedError()
            if progress:progress(depth+1,60)
            following={};pending=set()
            for state,path in beam:
                if len(seen)>=500000 or monotonic()-begun>seconds:
                    raise ValueError('rigid.search_limit')
                key=state
                if key in seen:continue
                seen.add(key)
                if key in roots:return path+tuple(m.inverse(6) for m in reversed(roots[key]))
                for child,move in self.shape_children(state):
                    if cancel and cancel():raise InterruptedError()
                    if monotonic()-begun>seconds:raise ValueError('rigid.search_limit')
                    key=child
                    if key in seen or key in pending:continue
                    word=path+(move,)
                    if key in roots:return word+tuple(m.inverse(6) for m in reversed(roots[key]))
                    pending.add(key)
                    score=(child&~self.root_code).bit_count()
                    bucket=following.setdefault(score,[])
                    if len(bucket)<500:bucket.append((child,word))
            # A temporarily more deformed assembly may be needed to unlock
            # a side turn. Keep every deformation count represented instead
            # of letting a flat, low-score plateau consume the whole beam.
            beam=[item for score in sorted(following) for item in following[score]]
            if not beam:break
        raise ValueError('rigid.search_limit')


@lru_cache(maxsize=2)
def geometry(kind):
    return TangramGeometry(kind)
