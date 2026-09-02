"""开发脚本：在模型上验证 3x3 求解器的块识别与各阶段算法。"""

from cube.cube3 import Cube3
from cube.conversion import cubies_to_facelets
from cube.coordinates import FACE_NORMALS
from cube.notation import normalize_move, parse_algorithm

CORNERS = [
    (1, 1, 1), (1, 1, -1), (-1, 1, 1), (-1, 1, -1),
    (1, -1, 1), (1, -1, -1), (-1, -1, 1), (-1, -1, -1),
]
EDGES = [
    (0, 1, 1), (0, 1, -1), (-1, 1, 0), (1, 1, 0),
    (0, -1, 1), (0, -1, -1), (-1, -1, 0), (1, -1, 0),
    (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
]


def _normals_of(pos):
    ns = []
    for axis in (0, 1, 2):
        v = pos[axis]
        if v != 0:
            n = [0, 0, 0]
            n[axis] = 1 if v > 0 else -1
            ns.append(tuple(n))
    return frozenset(ns)


CORNER_HOME = {_normals_of(p): p for p in CORNERS}
EDGE_HOME = {_normals_of(p): p for p in EDGES}


CENTER_POS = {
    "U": (0, 1, 0), "D": (0, -1, 0),
    "F": (0, 0, 1), "B": (0, 0, -1),
    "R": (1, 0, 0), "L": (-1, 0, 0),
}


def build_color_map(cube):
    color_by_face = {}
    for face, pos in CENTER_POS.items():
        cub = cube.cubies[pos]
        color_by_face[face] = cub.stickers[FACE_NORMALS[face]]
    face_by_color = {c: f for f, c in color_by_face.items()}
    return color_by_face, face_by_color


def piece_home(cubie, face_by_color):
    if len(cubie.stickers) == 1:  # 中心块
        return None
    dirs = frozenset(FACE_NORMALS[face_by_color[c]] for (_, c) in cubie.stickers.items())
    if len(cubie.stickers) == 3:
        return CORNER_HOME[dirs]
    if len(cubie.stickers) == 2:
        return EDGE_HOME[dirs]
    raise ValueError("unknown")


def describe_piece(cube, home_pos, face_by_color):
    for cub in cube.cubies.values():
        h = piece_home(cub, face_by_color)
        if h is not None and h == home_pos:
            oriented = all(
                FACE_NORMALS[face_by_color[c]] == d
                for d, c in cub.stickers.items()
            )
            return (cub.pos, oriented, dict(cub.stickers))
    return None


def dump_layer(cube, face_by_color, layer):
    out = []
    for home_pos in layer:
        r = describe_piece(cube, home_pos, face_by_color)
        out.append(f"{home_pos}: pos={r[0]} orient={r[1]}")
    return out


if __name__ == "__main__":
    cube = Cube3.solved()
    color_by_face, face_by_color = build_color_map(cube)
    print("centers:", color_by_face)
    print("face_by_color:", face_by_color)

    D_EDGES = [p for p in EDGES if p[1] == -1]
    D_CORNERS = [p for p in CORNERS if p[1] == -1]
    MID_EDGES = [p for p in EDGES if p[1] == 0]

    print("solved D edges:", dump_layer(cube, face_by_color, D_EDGES))
    print("solved D corners:", dump_layer(cube, face_by_color, D_CORNERS))

    # 测试: 打乱后块识别仍然正确
    c2 = Cube3.solved()
    cbf, fbc = build_color_map(c2)
    c2.apply_moves([normalize_move(m) for m in parse_algorithm("F'")])
    print("after F':", describe_piece(c2, (0, -1, 1), fbc))

    # 随机打乱 20 步: 每块 home 识别 + D 层状态
    import random
    rng = random.Random(42)
    faces = "UDFRBL"
    c3 = Cube3.solved()
    for _ in range(20):
        f = rng.choice(faces)
        c3.apply_move(f + ("", "'", "2")[rng.randint(0, 2)])
    _, fbc3 = build_color_map(c3)
    homes = {}
    for cub in c3.cubies.values():
        h = piece_home(cub, fbc3)
        if h is None:
            continue
        if h in homes:
            raise RuntimeError(f"duplicate home {h}")
        homes[h] = cub
    print("scrambled: all 20 pieces have unique homes:", len(homes) == 20)
    print("D edges:", dump_layer(c3, fbc3, D_EDGES))
    print("D corners:", dump_layer(c3, fbc3, D_CORNERS))
