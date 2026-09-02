"""D-cross 翻转情形: 找 D-on-P (D 边在 U 槽但 D 色在侧面) 状态, BFS 搜索修复序列。

同时验证 D-on-U 情形的 P2 下放。
"""

import random
from collections import deque

from cube.cube3 import Cube3
from cube.notation import normalize_move
from dev import (build_color_map, piece_home, FACE_NORMALS)

EDGES = {
    (0, 1, 1): "UF", (1, 1, 0): "UR", (0, 1, -1): "UB", (-1, 1, 0): "UL",
    (0, -1, 1): "DF", (1, -1, 0): "DR", (0, -1, -1): "DB", (-1, -1, 0): "DL",
    (1, 0, 1): "FR", (-1, 0, 1): "FL", (1, 0, -1): "BR", (-1, -1, -1): "BL",
}
U_SLOT = {  # home pos -> U-slot pos
    (0, -1, 1): (0, 1, 1),
    (1, -1, 0): (1, 1, 0),
    (0, -1, -1): (0, 1, -1),
    (-1, -1, 0): (-1, 1, 0),
}
P_DIR = {  # home pos -> P face normal
    (0, -1, 1): (0, 0, 1),
    (1, -1, 0): (1, 0, 0),
    (0, -1, -1): (0, 0, -1),
    (-1, -1, 0): (-1, 0, 0),
}

MOVES = ["U", "D", "F", "B", "R", "L", "U'", "D'", "F'", "B'", "R'", "L'"]


def d_color_of(c):
    for cub in c.cubies.values():
        if cub.home == (0, -1, 0):
            return list(cub.stickers.values())[0]
    return "Y"


def target_edge_state(c, face_by_color, home):
    """返回目标 D 边: (pos, on_d_face, kind) where kind in {home_ok, U-D-on-U, U-D-on-P, other}."""
    dc = d_color_of(c)
    for cub in c.cubies.values():
        h = piece_home(cub, face_by_color)
        if h is not None and h == home and len(cub.stickers) == 2:
            on_d = any(d == (0, -1, 0) and col == dc for d, col in cub.stickers.items())
            on_u = any(d == (0, 1, 0) and col == dc for d, col in cub.stickers.items())
            on_p = any(d == P_DIR[home] and col == dc for d, col in cub.stickers.items())
            if cub.pos == home and on_d:
                return cub.pos, True, "home_ok"
            if cub.pos == U_SLOT[home]:
                kind = "U-D-on-U" if on_u else ("U-D-on-P" if on_p else "U-other")
                return cub.pos, on_d, kind
            return cub.pos, on_d, "other"
    return None, False, "notfound"


def find_state(want_kind, rng_seed=0, max_trials=6000):
    """找一个目标 D 边处于 want_kind 的状态, 返回 (cube, home, edge_name, moves_list)。"""
    rng = random.Random(rng_seed)
    faces = ["U", "D", "F", "B", "R", "L"]
    homes = list(U_SLOT.keys())
    for trial in range(max_trials):
        moves_seq = []
        c = Cube3.solved()
        for _ in range(15):
            f = rng.choice(faces)
            cnt = rng.choice([1, 2, 3])
            mv = normalize_move((f, False, cnt))
            c.apply_move(mv)
            moves_seq.append(mv)
        cm, fbc = build_color_map(c)
        for home in homes:
            pos, on_d, kind = target_edge_state(c, fbc, home)
            if kind == want_kind:
                return c, home, EDGES[home], moves_seq
    return None


def bfs_fix(start_cube, home, face_by_color, max_depth=7):
    """BFS: 从 start_cube 出发, 找最短序列使目标边 home_ok。"""
    dc = d_color_of(start_cube)
    start_key = start_cube.state_key() if hasattr(start_cube, "state_key") else None
    # 用一个可哈希的状态快照
    def snap(c):
        return tuple(
            (cub.pos, frozenset(cub.stickers.items()))
            for cub in sorted(c.cubies.values(), key=lambda x: str(x.home))
        )

    goal_check = lambda c: (lambda p, o, k: k == "home_ok")( *target_edge_state(c, face_by_color, home) )

    if goal_check(start_cube):
        return []
    frontier = deque([(start_cube, [])])
    seen = {snap(start_cube)}
    while frontier:
        c, seq = frontier.popleft()
        if len(seq) >= max_depth:
            continue
        for mv in MOVES:
            c2 = c.clone()
            c2.apply_move(mv)
            if goal_check(c2):
                return seq + [mv]
            key = snap(c2)
            if key not in seen:
                seen.add(key)
                frontier.append((c2, seq + [mv]))
    return None


def main():
    # --- D-on-U: 验证 P2 下放 ---
    print("=== D-on-U: P2 下放验证 ===")
    res = find_state("U-D-on-U")
    if res:
        c, home, ename, moves_seq = res
        print(f"找到 D-on-U: {ename} home={home}, 扰动序列={[normalize_move(m)[0]+'' for m in []] or moves_seq[:3]}...")
        p_dir = P_DIR[home]
        # P2 = 该 P 面双转
        p2 = {"(0, 0, 1)": "F2", "(1, 0, 0)": "R2", "(0, 0, -1)": "B2", "(-1, 0, 0)": "L2"}[str(p_dir)]
        c2 = c.clone()
        c2.apply_move(p2)
        pos, on_d, kind = target_edge_state(c2, build_color_map(c2)[1], home)
        print(f"  应用 {p2}: 目标边 -> {pos} on_d={on_d} kind={kind}")
    else:
        print("未找到 D-on-U")

    # --- D-on-P: BFS 搜索修复 ---
    print("\n=== D-on-P: BFS 搜索修复序列 ===")
    res = find_state("U-D-on-P")
    if res:
        c, home, ename, moves_seq = res
        cm, fbc = build_color_map(c)
        pos, on_d, kind = target_edge_state(c, fbc, home)
        print(f"找到 D-on-P: {ename} home={home} pos={pos}, 扰动序列={moves_seq}")
        fix = bfs_fix(c, home, fbc, max_depth=7)
        if fix is None:
            print("BFS 未找到 (depth<=7)")
        else:
            print(f"  BFS 找到修复序列: {fix}")
            c2 = c.clone()
            for mv in fix:
                c2.apply_move(mv)
            pos2, on_d2, kind2 = target_edge_state(c2, build_color_map(c2)[1], home)
            print(f"  验证: 目标边 -> {pos2} on_d={on_d2} kind={kind2}")
    else:
        print("未找到 D-on-P")


if __name__ == "__main__":
    main()
