"""D-cross 探索: 随机扰动下 D 边/角的实际状态分布, 用于设计正确的 D 层算法。"""

import random
from cube.cube3 import Cube3
from cube.notation import normalize_move, parse_algorithm
from dev import (EDGES, CORNERS, build_color_map, piece_home,
                 FACE_NORMALS, CORNER_HOME, EDGE_HOME)

D_EDGES = [p for p in EDGES if p[1] == -1]
D_CORNERS = [p for p in CORNERS if p[1] == -1]
M_EDGES = [p for p in EDGES if p[1] == 0]
U_EDGES = [p for p in EDGES if p[1] == 1]


def mk(alg, seed=None):
    c = Cube3.solved()
    rng = random.Random(seed)
    faces = ["U", "D", "F", "B", "R", "L"]
    n = 0
    for _ in range(20):
        f = rng.choice(faces)
        cnt = rng.choice([1, 2, 3])
        c.apply_move(normalize_move((f, False, cnt)))
        n += 1
    return c


def piece_state(c, home_pos, face_by_color):
    """home_pos 上的块: (当前 pos, D/U 色是否在该色应在的面, stickers)。"""
    for cub in c.cubies.values():
        h = piece_home(cub, face_by_color)
        if h is not None and h == home_pos:
            # 该块的目标面: 从 home 位置的两个/三个方向推断
            oriented = all(
                FACE_NORMALS[face_by_color[col]] == d
                for d, col in cub.stickers.items()
            )
            return (cub.pos, oriented)
    return None


if __name__ == "__main__":
    for seed in [1, 7, 42]:
        c = mk(None, seed)
        cm, fbc = build_color_map(c)
        print(f"=== seed={seed} ===")
        print("D edges :")
        for p in D_EDGES:
            pos, ori = piece_state(c, p, fbc)
            loc = "D" if pos[1] == -1 else ("U" if pos[1] == 1 else "M")
            print(f"  home {p}: now at {pos} [{loc}] oriented={ori}")
        print("D corners:")
        for p in D_CORNERS:
            pos, ori = piece_state(c, p, fbc)
            loc = "D" if pos[1] == -1 else ("U" if pos[1] == 1 else "M")
            print(f"  home {p}: now at {pos} [{loc}] oriented={ori}")
        print()
