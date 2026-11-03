"""2x2 (二阶) 求解器。

2 阶魔方只有 8 个角块，无棱块、无中心块。先用角块投影距离引导短解搜索，
超过快速阶段的时间后构造合法虚拟三阶继续求解，不把时间上限当作无解。

状态：每个角位（槽）用一个小整数编码 (corner_id, orient)，其中 orient 为该角块
3 个 canonical 颜色当前的 3D 世界法线方向（每个方向编码为 0..5）。整体状态为
长度为 8 的整数元组。转动为 HTM（R/R'/R2 各算一步）。
"""

import time
from typing import List, Tuple

from cube.coordinates import TURNS, FACE_AXIS_SIGN
from cube.cube2 import Cube2
from solver.result import SolveResult, SolveStage

_FACES = ("R", "L", "U", "D", "F", "B")
_SLOT_COORDS = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
_HTM = [(f, c) for f in _FACES for c in (1, 2, 3)]

# 法线方向编码: 0..5
_NORMAL_CODE = {
    (1, 0, 0): 0, (-1, 0, 0): 1,
    (0, 1, 0): 2, (0, -1, 0): 3,
    (0, 0, 1): 4, (0, 0, -1): 5,
}
_CODE_NORMAL = {v: k for k, v in _NORMAL_CODE.items()}


def _slot_index(coord) -> int:
    x, y, z = coord
    return ((0 if x < 0 else 1) << 2) | ((0 if y < 0 else 1) << 1) | (0 if z < 0 else 1)


def _normal_rot_code(face) -> dict:
    rot = TURNS[face]
    return {code: _NORMAL_CODE[rot(*n)] for code, n in _CODE_NORMAL.items()}


class _2x2State:
    """2x2 状态（整数编码）与 HTM 邻居生成。"""

    def __init__(self):
        self.canon_norms = {}
        self.canon_colors = {}
        self._prep_canon()
        self.layer_slots = {}
        for face in _FACES:
            n_axis, n_sign = FACE_AXIS_SIGN[face]
            self.layer_slots[face] = {
                s for s, c in enumerate(_SLOT_COORDS) if c[n_axis] == n_sign
            }
        self.move_perm = {face: self._build_perm(face) for face in _FACES}
        self.norm_rot = {face: _normal_rot_code(face) for face in _FACES}

    def _prep_canon(self):
        solved = Cube2.solved()
        self.color_set_to_cid = {}
        for cub in solved.cubies.values():
            cid = _slot_index(cub.home)
            hx, hy, hz = cub.home
            canon = [(hx, 0, 0), (0, hy, 0), (0, 0, hz)]
            colors = [cub.stickers[n] for n in canon]
            self.canon_norms[cid] = canon
            self.canon_colors[cid] = colors
            self.color_set_to_cid[tuple(sorted(colors))] = cid

    def _build_perm(self, face) -> dict:
        cube = Cube2.solved()
        cube.apply_move(face)
        slot_content = {}
        for cub in cube.cubies.values():
            cid = _slot_index(cub.home)
            s = _slot_index(cub.pos)
            slot_content[s] = cid
        corner_now_slot = {c: s for s, c in slot_content.items()}
        return {s: corner_now_slot[s] for s in range(8)}

    def _encode_orient(self, orient) -> int:
        return (_NORMAL_CODE[orient[0]] << 6) | (
            _NORMAL_CODE[orient[1]] << 3) | _NORMAL_CODE[orient[2]]

    def _decode_orient(self, o) -> tuple:
        return (_CODE_NORMAL[(o >> 6) & 7], _CODE_NORMAL[(o >> 3) & 7], _CODE_NORMAL[o & 7])

    def extract(self, cube: Cube2) -> tuple:
        out = [None] * 8
        for cub in cube.cubies.values():
            s = _slot_index(cub.pos)
            cid = self.color_set_to_cid[tuple(sorted(cub.stickers.values()))]
            canon = self.canon_norms[cid]
            cols = self.canon_colors[cid]
            norm_order = [next(m for m, c in cub.stickers.items() if c == col)
                          for col in cols]
            out[s] = (cid << 9) | self._encode_orient(tuple(norm_order))
        return tuple(out)

    def solved_state(self) -> tuple:
        out = []
        for cid in range(8):
            canon = self.canon_norms[cid]
            out.append((cid << 9) | self._encode_orient(tuple(canon)))
        return tuple(out)

    def is_solved(self, state) -> bool:
        return state == self.solved_state()

    def apply(self, state, face, count=1) -> tuple:
        slot_perm = self.move_perm[face]
        layer = self.layer_slots[face]
        rot = self.norm_rot[face]
        st = state
        for _ in range(count):
            ns = [0] * 8
            for s in range(8):
                x = st[s]
                corner = x >> 9
                o = x & 511
                if s in layer:
                    n0 = rot[(o >> 6) & 7]
                    n1 = rot[(o >> 3) & 7]
                    n2 = rot[o & 7]
                    new_o = (n0 << 6) | (n1 << 3) | n2
                    ns[slot_perm[s]] = (corner << 9) | new_o
                else:
                    ns[s] = x
            st = tuple(ns)
        return st

    def neighbors(self, state, last_face=None) -> List[Tuple[tuple, str]]:
        out = []
        for face, count in _HTM:
            if last_face == face:
                continue
            if last_face is not None and _is_opposite(last_face, face) and last_face > face:
                continue
            out.append((self.apply(state, face, count), _move_str(face, count)))
        return out


def _is_opposite(a, b) -> bool:
    return {"R": "L", "L": "R", "U": "D", "D": "U", "F": "B", "B": "F"}.get(a) == b


def _move_str(face, count) -> str:
    if count == 1:
        return face
    if count == 2:
        return face + "2"
    return face + "'"


_ENGINE = None


def _get_engine() -> _2x2State:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _2x2State()
    return _ENGINE


def _solve_bidir(engine: _2x2State, start, time_limit):
    t0 = time.perf_counter()
    goal = engine.solved_state()
    if engine.is_solved(start):
        return []

    parent_fwd = {start: (None, None)}
    parent_bwd = {goal: (None, None)}
    frontier_fwd = [(start, None)]
    frontier_bwd = [(goal, None)]

    def expand(frontier, parent):
        new_frontier = []
        for node, last_face in frontier:
            for face, count in _HTM:
                if last_face == face:
                    continue
                if last_face is not None and _is_opposite(last_face, face) and last_face > face:
                    continue
                nxt = engine.apply(node, face, count)
                if nxt in parent:
                    continue
                parent[nxt] = (node, _move_str(face, count))
                new_frontier.append((nxt, face))
        return new_frontier

    while True:
        if (time.perf_counter() - t0) > time_limit:
            raise TimeoutError()
        if len(frontier_fwd) <= len(frontier_bwd):
            frontier_fwd = expand(frontier_fwd, parent_fwd)
        else:
            frontier_bwd = expand(frontier_bwd, parent_bwd)
        meet = set(parent_fwd.keys()) & set(parent_bwd.keys())
        if meet:
            mid = next(iter(meet))
            return _reconstruct(mid, parent_fwd, parent_bwd)


def _reconstruct(mid, parent_fwd, parent_bwd):
    fwd = []
    key = mid
    while True:
        pk, mv = parent_fwd[key]
        if pk is None:
            break
        fwd.append(mv)
        key = pk
    fwd.reverse()
    bwd = []
    key = mid
    while True:
        pk, mv = parent_bwd[key]
        if pk is None:
            break
        bwd.append(mv)
        key = pk
    inv = [_invert_move(mv) for mv in bwd]
    return fwd + inv


def _invert_move(mv) -> str:
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    return mv + "'"


_CORNER_DISTANCES = None


def _corner_distances(cancel):
    """Exact relaxed distances: 40320 permutations and 2187 twists.

    These reuse the already bundled move tables and need only 42507 bytes
    for distances. The search never retains a full breadth-first frontier
    of coloured 2x2 states.
    """
    global _CORNER_DISTANCES
    if _CORNER_DISTANCES is None:
        from collections import deque
        from twophase import moves as tables
        distances=[]
        for size,turns in ((40320,tables.corners_move),(2187,tables.twist_move)):
            dist=bytearray([255])*size;dist[0]=0;pending=deque([0])
            while pending:
                cancel()
                state=pending.popleft();depth=dist[state]+1;offset=state*18
                for move in range(18):
                    child=turns[offset+move]
                    if dist[child]==255:
                        dist[child]=depth;pending.append(child)
            distances.append(dist)
        _CORNER_DISTANCES=tuple(distances)
    return _CORNER_DISTANCES


def _short_corner_solution(cc,cancel,seconds):
    if seconds<=0:
        cancel()
        return None
    from twophase import moves as tables
    permutation_distance,twist_distance=_corner_distances(cancel)
    permutation,twist=cc.get_corners(),cc.get_twist()
    deadline=time.perf_counter()+max(0.,seconds)
    path=[];nodes=0
    def visit(p,t,remaining,last):
        nonlocal nodes
        nodes+=1
        if nodes%1024==0:
            cancel()
            if time.perf_counter()>=deadline:raise TimeoutError()
        if max(permutation_distance[p],twist_distance[t])>remaining:return False
        if p==0 and t==0:return True
        if remaining==0:return False
        for face in range(6):
            # Opposite faces commute: retain one order, not neither order.
            if face==last or (last>=0 and last-face==3):continue
            for move in range(face*3,face*3+3):
                following=tables.corners_move[p*18+move]
                orientation=tables.twist_move[t*18+move]
                if max(permutation_distance[following],twist_distance[orientation])>=remaining:continue
                path.append(move)
                if visit(following,orientation,remaining-1,face):return True
                path.pop()
        return False
    bound=max(permutation_distance[permutation],twist_distance[twist])
    try:
        while time.perf_counter()<deadline:
            cancel()
            if visit(permutation,twist,bound,-1):
                return ['URFDLB'[m//3]+('', '2', "'")[m%3] for m in path]
            bound+=1
    except TimeoutError:
        pass
    return None


def solve_2x2(cube: Cube2, cancel_event=None, time_limit=5.0,
              progress_callback=None) -> SolveResult:
    """Solve entered corners; time_limit budgets short solutions, not success."""
    from cube.cube3 import Cube3
    from cube.conversion import cubies_to_facelets
    from solver.solver3 import _tface,_tcubie,_build_cubestring,solve_3x3
    started=time.perf_counter()
    def cancel():
        if cancel_event is not None and cancel_event.is_set():raise InterruptedError()
    def result(success,moves,message,description='角块求解'):
        return SolveResult(success,moves,message,int((time.perf_counter()-started)*1000),
                           len(moves),[SolveStage('2x2',description,moves)] if success else [])
    cancel()
    if set(cube.cubies)!=set(_SLOT_COORDS):
        return result(False,[],'二阶角块位置不完整')
    virtual=Cube3.solved()
    for pos,cubie in cube.cubies.items():virtual.cubies[pos]=cubie.clone()
    faces=cubies_to_facelets(virtual.cubies,3)
    try:
        fc=_tface.FaceCube();code=fc.from_string(_build_cubestring(faces))
        if code!=_tcubie.CUBE_OK:return result(False,[],str(code))
        cc=fc.to_cubie_cube()
        # Synthetic edges carry the corner parity; a real 2x2 has no edge
        # permutation constraint. Corner identities and twist still verify.
        if cc.corner_parity():cc.ep[0],cc.ep[1]=cc.ep[1],cc.ep[0]
        code=cc.verify()
        if code!=_tcubie.CUBE_OK:return result(False,[],str(code))
    except (KeyError,ValueError,IndexError):
        return result(False,[],'二阶角块颜色或方向不合法')
    if cube.is_solved():return result(True,[],'')
    moves=_short_corner_solution(cc,cancel,float(time_limit) if time_limit is not None else 5.)
    description='角块距离引导搜索'
    if moves is None:
        cancel()
        if progress_callback:
            try:progress_callback({'label':'solver.continuing','progress':0.})
            except Exception:pass
        cancel()
        from cube.colors import DEFAULT_COLORS
        string=cc.to_facelet_cube().to_string()
        faces={f:[[DEFAULT_COLORS[string[k*9+r*3+c]] for c in range(3)]
                  for r in range(3)] for k,f in enumerate('URFDLB')}
        continuation=solve_3x3(faces)
        cancel()
        if not continuation.success:return result(False,[],continuation.message)
        moves=list(continuation.moves);description='虚拟三阶角块还原'
    replay=cube.clone()
    for move in moves:
        cancel();replay.apply_move(move)
    if not replay.is_solved():return result(False,[],'二阶还原回放校验失败')
    return result(True,moves,'',description)


def solve_2x2_facelets(facelets, cancel_event=None, time_limit=5.0) -> SolveResult:
    """从 facelet 字典求解 2x2。"""
    from cube.conversion import facelets_to_cubies
    cube = Cube2(facelets_to_cubies(facelets, 2))
    return solve_2x2(cube, cancel_event=cancel_event, time_limit=time_limit)
