"""从魔方状态构建 3D 场景（带颜色的立方体面）。

只渲染魔方外表面：每个 cubie 的 6 个面中，朝向立方体内部的面不画。
每个 cubie 用一个"小立方体"：边长 gap 间隙隔开，方便观察内部。

顶点格式：pos (3) + color (4)，使用 Kivy Mesh 的 TriangleFan 组合为四边形。
"""

import math

from kivy.graphics import Mesh

from cube.coordinates import FACE_NORMALS, get_d_maxc
from renderer.mat4 import Mat4

# 立方体半边长（1 单位网格）
# HALF = 0.5 时相邻 cubie 面正好贴合，无间隙。
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

# 粽子/四角锥外形：把立方体外表面顶点按高度收敛到顶部尖点。
# S = 立方体外观半长（maxc + HALF）。apex 位于 +Y 顶端。
_PYRAMID_ROOT = "mastermorphix"


def _pyramid_vertex(x, y, z, s):
    """把一个立方体表面顶点映射到四角锥外形。

    底部(y=-s)保持最大截面，越往上(x,z)越向中心收拢，到顶部(y=+s)收敛为尖点。
    s = 立方体外观半长。返回 (x, y, z)。
    """
    if s <= 0:
        return (x, y, z)
    f = (s - y) / (2.0 * s)
    f = max(f, 0.03)  # 避免完全收敛为点导致退化三角形
    return (x * f, y, z * f)


def _dim(color, factor=0.35):
    """把颜色降饱和、压低亮度（但保持色相可读），用于淡化非目标块。"""
    r, g, b, a = color
    return (
        r * factor + 0.12,
        g * factor + 0.12,
        b * factor + 0.12,
        a,
    )


def _quad_vertices(pos, face_verts, color):
    """把一个四边形（4 顶点局部坐标）转成两组三角形顶点。"""
    out = []
    for x, y, z in face_verts:
        out.extend([pos[0] + x, pos[1] + y, pos[2] + z, *color])
    # 两个三角形: v0 v1 v2, v0 v2 v3
    # 已按四边形顺序给出 4 顶点，直接展开即可（Kivy Mesh 每 3 顶点一个三角形）
    return out


def build_scene(cube, moving_positions=None, rotation=None, highlight=None,
                kind="cube"):
    """构建场景顶点列表。

    cube: BaseCube 实例（当前逻辑状态，cubies 以 pos 为键）。
    moving_positions: 若给定，这些位置上的 cubie 需额外施加 rotation 变换。
    rotation: Kivy Matrix，用于转动层动画。
    highlight: 若给定（可迭代的 pos 集合），只对这些位置的块显示真实颜色，
               其余块显示灰色（教学演示的"聚焦"效果）。
    kind: "cube"（标准立方体）或 "mastermorphix"（粽子/四角锥形变）。
    返回 (vertices, indices)。
    """
    vertices = []
    indices = []
    vi = 0
    d, maxc = get_d_maxc(cube.n)
    # 立方体外观半长（用于四角锥形变：底部截面最大，顶端收为尖点）。
    s = maxc + HALF * d

    # 每个 cubie：6 个面，仅画外表面（pos[axis]==±maxc 才画该面）
    for pos, cub in cube.cubies.items():
        x, y, z = pos
        # 基础变换：平移到 cubie 位置（先旋转层，再平移）
        if moving_positions is not None and pos in moving_positions and rotation is not None:
            base = rotation * Mat4.translation(x, y, z)
        else:
            base = Mat4.translation(x, y, z)

        # 聚焦判断：按 cubie 稳定身份 home 跟踪（而非空间位置，转动中才能持续高亮同一批块）。
        # 中心块始终保留真实颜色，作为方向参照。
        is_center = cub is not None and len(cub.stickers) == 1
        focused = (
            highlight is None
            or is_center
            or (cub is not None and cub.home in highlight)
        )

        for face_name, normal, local_verts in _FACES:
            # 判定是否为外表面
            axis = 0 if abs(normal[0]) == 1 else (1 if abs(normal[1]) == 1 else 2)
            sign = 1 if normal[axis] > 0 else -1
            if pos[axis] != sign * maxc:
                # 内部面：仅当朝向内部空间时跳过；外表面总会命中
                continue
            # 颜色：先取真实贴纸色，再按是否聚焦做全彩/淡化。
            color = _DARK
            if cub is not None:
                col = cub.stickers.get(tuple(normal))
                if col is not None:
                    c = _RGB.get(col)
                    if c is not None:
                        color = (c[0], c[1], c[2], 1.0)
            if not focused:
                color = _dim(color)
            # 变换 4 个顶点。
            # 各阶网格间距为 d（3阶=1，4阶=2），
            # 将半边长 HALF 的局部坐标整体缩放 d 倍，
            # 使相邻 cubie 面正好贴合（3阶不受影响）。
            for lx, ly, lz in local_verts:
                p = base.transform(lx * d, ly * d, lz * d)
                if kind == _PYRAMID_ROOT:
                    p = _pyramid_vertex(p[0], p[1], p[2], s)
                vertices.extend([p[0], p[1], p[2], *color])
            indices.extend([vi, vi + 1, vi + 2, vi, vi + 2, vi + 3])
            vi += 4
    return vertices, indices


def build_mesh(cube, moving_positions=None, rotation=None):
    """构建可直接绘制的 Kivy Mesh。"""
    vertices, indices = build_scene(
        cube, moving_positions=moving_positions, rotation=rotation)
    return Mesh(vertices=vertices, indices=indices, fmt=VERTEX_FORMAT,
                mode="triangles")
