"""从魔方状态构建 3D 场景（带颜色的面）。

只渲染魔方外表面：每个 cubie 的 6 个面中，朝向立方体内部的面不画。

顶点格式：pos (3) + color (4)。

两种外形：
- "cube"：标准立方体，每个贴纸面是 2 个平面三角形 + 直线边界。
- "mastermorphix"：圆润正四面体（粽子/三阶粽子魔方），通过双线性细分
  加径向平滑映射生成圆弧面，并单独生成弯曲的块边界线。

约定：每连续 3 个顶点为一个三角形；块边界线由 outline_paths 单独返回。
"""

import math

from kivy.graphics import Mesh

from cube.coordinates import FACE_NORMALS, get_d_maxc

# 立方体半边长（1 单位网格）
HALF = 0.5
GAP = 0.0  # 间隙系数，暂为 0

# 每个 cubie 的 6 个面（法线、4 顶点局部坐标）
_FACES = [
    ("R", (1, 0, 0), [(HALF, -HALF, -HALF), (HALF, HALF, -HALF),
                       (HALF, HALF, HALF), (HALF, -HALF, HALF)]),
    ("L", (-1, 0, 0), [(-HALF, -HALF, HALF), (-HALF, HALF, HALF),
                        (-HALF, HALF, -HALF), (-HALF, -HALF, -HALF)]),
    ("U", (0, 1, 0), [(-HALF, HALF, -HALF), (HALF, HALF, -HALF),
                       (HALF, HALF, HALF), (-HALF, HALF, HALF)]),
    ("D", (0, -1, 0), [(-HALF, -HALF, HALF), (HALF, -HALF, HALF),
                        (HALF, -HALF, -HALF), (-HALF, -HALF, -HALF)]),
    ("F", (0, 0, 1), [(-HALF, -HALF, HALF), (HALF, -HALF, HALF),
                       (HALF, HALF, HALF), (-HALF, HALF, HALF)]),
    ("B", (0, 0, -1), [(HALF, -HALF, -HALF), (-HALF, -HALF, -HALF),
                        (-HALF, HALF, -HALF), (HALF, HALF, -HALF)]),
]

VERTEX_FORMAT = (
    (b'v_pos', 3, 'float'),
    (b'v_color', 4, 'float'),
)

_RGB = {
    "W": (1.0, 1.0, 1.0),
    "Y": (1.0, 0.85, 0.0),
    "R": (0.85, 0.1, 0.1),
    "O": (1.0, 0.55, 0.0),
    "B": (0.1, 0.25, 0.85),
    "G": (0.0, 0.65, 0.2),
}

# 未上色（内部面）的深色
_DARK = (0.08, 0.08, 0.08, 1.0)

# 教学演示中非聚焦块的灰色（已改为淡化，保留可读色相）
_GRAY = (0.42, 0.42, 0.44, 1.0)

# Mastermorphix 外形标识。
_MASTERMORPHIX_KIND = "mastermorphix"

# 正四面体四个顶点方向（对应于四个交错角）。
_TETRA_DIRECTIONS = (
    (1.0, 1.0, 1.0),
    (1.0, -1.0, -1.0),
    (-1.0, 1.0, -1.0),
    (-1.0, -1.0, 1.0),
)

# 圆润度：0 附近接近尖锐四面体；0.2~0.35 接近圆润粽子外观。
_MASTERMORPHIX_ROUNDNESS = 0.26
# 细分数：越大曲面越圆滑（三角形越多）。
_MASTERMORPHIX_SUBDIV = 6
# 块边界线每条边的细分点数。
_OUTLINE_SUBDIV = 10


def _smooth_max(values, sharpness):
    """平滑最大值：sharpness 越大越接近普通 max()。"""
    maximum = max(values)
    total = sum(math.exp((v - maximum) * sharpness) for v in values)
    return maximum + math.log(total) / sharpness


def _mastermorphix_vertex(x, y, z, s, roundness=_MASTERMORPHIX_ROUNDNESS):
    """把立方体外表面顶点径向映射到圆润正四面体外表面。

    roundness: 0 附近接近尖锐四面体；0.2~0.35 接近圆润粽子外观。
    """
    if s <= 1e-8:
        return x, y, z

    point = (float(x), float(y), float(z))
    values = [
        -(nx * point[0] + ny * point[1] + nz * point[2])
        for nx, ny, nz in _TETRA_DIRECTIONS
    ]

    if roundness <= 1e-6:
        denominator = max(values)
    else:
        sharpness = 1.0 / max(roundness * s, 1e-6)
        denominator = _smooth_max(values, sharpness)

    if denominator <= 1e-8:
        return x, y, z

    scale = s / denominator
    return (point[0] * scale, point[1] * scale, point[2] * scale)


def _lerp(a, b, t):
    return a + (b - a) * t


def _bilerp(v00, v10, v11, v01, u, v):
    """在四边形中执行双线性插值。"""
    a = (_lerp(v00[0], v10[0], u),
         _lerp(v00[1], v10[1], u),
         _lerp(v00[2], v10[2], u))
    b = (_lerp(v01[0], v11[0], u),
         _lerp(v01[1], v11[1], u),
         _lerp(v01[2], v11[2], u))
    return (_lerp(a[0], b[0], v),
            _lerp(a[1], b[1], v),
            _lerp(a[2], b[2], v))


def _shape(point, kind, s, rotation):
    """对点应用外形映射与（可选）刚体旋转。形变先于旋转。"""
    if kind == _MASTERMORPHIX_KIND:
        point = _mastermorphix_vertex(point[0], point[1], point[2], s)
    if rotation is not None:
        point = rotation.transform(point[0], point[1], point[2])
    return point


def _append_triangle(vertices, p0, p1, p2, color):
    for point in (p0, p1, p2):
        vertices.extend([
            point[0], point[1], point[2],
            color[0], color[1], color[2], color[3],
        ])


def _append_patch(vertices, corners, color, kind, s, rotation, subdiv):
    """把一个贴纸四边形细分成三角形并写入 vertices。"""
    v00, v10, v11, v01 = corners
    count = max(1, int(subdiv))
    for row in range(count):
        v0 = row / count
        v1 = (row + 1) / count
        for col in range(count):
            u0 = col / count
            u1 = (col + 1) / count
            p00 = _shape(_bilerp(v00, v10, v11, v01, u0, v0), kind, s, rotation)
            p10 = _shape(_bilerp(v00, v10, v11, v01, u1, v0), kind, s, rotation)
            p11 = _shape(_bilerp(v00, v10, v11, v01, u1, v1), kind, s, rotation)
            p01 = _shape(_bilerp(v00, v10, v11, v01, u0, v1), kind, s, rotation)
            _append_triangle(vertices, p00, p10, p11, color)
            _append_triangle(vertices, p00, p11, p01, color)


def _curved_path(corners, kind, s, rotation, subdivisions):
    """沿贴纸四边形边界返回一条闭合折线（3D 点列表）。"""
    path = []
    k = len(corners)
    for i in range(k):
        a = corners[i]
        b = corners[(i + 1) % k]
        for j in range(subdivisions):
            t = j / subdivisions
            p = (_lerp(a[0], b[0], t),
                 _lerp(a[1], b[1], t),
                 _lerp(a[2], b[2], t))
            path.append(_shape(p, kind, s, rotation))
    return path


def _dim(color, factor=0.35):
    """把颜色降饱和、压低亮度（但保持色相可读），用于淡化非目标块。"""
    r, g, b, a = color
    return (
        r * factor + 0.12,
        g * factor + 0.12,
        b * factor + 0.12,
        a,
    )


def build_scene(cube, moving_positions=None, rotation=None, highlight=None,
                kind="cube"):
    """构建场景。

    cube: BaseCube 实例（当前逻辑状态，cubies 以 pos 为键）。
    moving_positions: 若给定，这些位置上的 cubie 需额外施加 rotation 变换。
    rotation: Kivy Matrix，用于转动层动画。
    highlight: 若给定（可迭代的 pos 集合），只对这些位置的块显示真实颜色，
               其余块显示灰色（教学演示的"聚焦"效果）。
    kind: "cube"（标准立方体）或 "mastermorphix"（粽子/四面体形变）。

    返回 (triangle_vertices, outline_paths)：
    - triangle_vertices：每连续 3 个顶点为一个三角形（x,y,z,r,g,b,a）。
    - outline_paths：各贴纸块的闭合边界折线（每个元素为 3D 点列表）。
    """
    triangles = []
    outlines = []
    d, maxc = get_d_maxc(cube.n)
    s = maxc + HALF * d

    is_master = kind == _MASTERMORPHIX_KIND
    subdiv = _MASTERMORPHIX_SUBDIV if is_master else 1
    outline_subdiv = _OUTLINE_SUBDIV if is_master else 1

    for pos, cub in cube.cubies.items():
        x, y, z = pos
        is_moving = (
            moving_positions is not None
            and pos in moving_positions
            and rotation is not None
        )
        is_center = cub is not None and len(cub.stickers) == 1
        focused = (
            highlight is None
            or is_center
            or (cub is not None and cub.home in highlight)
        )
        block_rotation = rotation if is_moving else None

        for _face_name, normal, local_verts in _FACES:
            axis = 0 if abs(normal[0]) == 1 else (1 if abs(normal[1]) == 1 else 2)
            sign = 1 if normal[axis] > 0 else -1
            if pos[axis] != sign * maxc:
                continue
            color = _DARK
            if cub is not None:
                col = cub.stickers.get(tuple(normal))
                if col is not None:
                    c = _RGB.get(col)
                    if c is not None:
                        color = (c[0], c[1], c[2], 1.0)
            if not focused:
                color = _dim(color)

            corners = [
                (x + lx * d, y + ly * d, z + lz * d)
                for lx, ly, lz in local_verts
            ]

            _append_patch(
                triangles, corners, color, kind, s, block_rotation, subdiv,
            )
            outlines.append(
                _curved_path(corners, kind, s, block_rotation, outline_subdiv),
            )

    return triangles, outlines


def build_mesh(cube, moving_positions=None, rotation=None, kind="cube"):
    """构建可直接绘制的 Kivy Mesh（每 3 顶点一个三角形）。"""
    triangle_vertices, _outlines = build_scene(
        cube, moving_positions=moving_positions, rotation=rotation, kind=kind,
    )
    return Mesh(
        vertices=triangle_vertices,
        fmt=VERTEX_FORMAT,
        mode="triangles",
    )
