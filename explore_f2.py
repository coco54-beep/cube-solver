"""D-cross 机制精确测试: 完整 cube dump, 理解 F2 等动作对 D 边的真实作用。"""

import random
from cube.cube3 import Cube3
from cube.notation import normalize_move, parse_algorithm
from dev import (EDGES, CORNERS, build_color_map, piece_home,
                 FACE_NORMALS)

D_EDGES = [p for p in EDGES if p[1] == -1]
EDGE_HOME = {
    (0, 1, 1): "UF", (1, 1, 0): "UR", (0, 1, -1): "UB", (-1, 1, 0): "UL",
    (0, -1, 1): "DF", (1, -1, 0): "DR", (0, -1, -1): "DB", (-1, -1, 0): "DL",
    (1, 0, 1): "FR", (-1, 0, 1): "FL", (1, 0, -1): "BR", (-1, 0, -1): "BL",
}


def dump(c, face_by_color):
    """对每个非中心块: home名 -> 当前 pos名, D/U色所在面。"""
    lines = []
    for cub in c.cubies.values():
        h = piece_home(cub, face_by_color)
        if h is None or h[1] != -1:  # 只看 D 边 (home y=-1, 边是2向)
            continue
        hname = EDGE_HOME.get(h, str(h))
        cur = cub.pos
        curname = EDGE_HOME.get(cur, str(cur))
        # D 色所在面:
        dcolor = None
        for d, col in cub.stickers.items():
            # 找 D 中心颜色
            pass
        # 简单: 报告每个贴纸 (面方向->颜色)
        st = {d: col for d, col in cub.stickers.items()}
        lines.append(f"  {hname:3s} @ {curname:3s}  stickers={st}")
    return "\n".join(sorted(lines))


def d_color(c, face_by_color):
    """D 中心颜色 (Y)。"""
    for cub in c.cubies.values():
        if cub.home == (0, -1, 0):
            return list(cub.stickers.values())[0]
    return "Y"


if __name__ == "__main__":
    # Test: solved -> F2. Track where the DF edge goes and its sticker faces.
    c = Cube3.solved()
    cm, fbc = build_color_map(c)
    dc = d_color(c, fbc)
    print("=== solved ===")
    print("D-color = ", dc)
    print(dump(c, fbc))

    c.apply_move("F2")
    print("=== after F2 ===")
    print(dump(c, fbc))

    c.apply_move("F2")
    print("=== after F2 F2 (should be solved) ===")
    print("is_solved =", c.is_solved())
