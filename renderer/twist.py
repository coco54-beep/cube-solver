"""拧魔方（交互式拧动）的纯逻辑：拖动 -> (轴, 层坐标集合, 方向)。

与 CubeView 的投影/相机约定保持一致（见 renderer/cube_view.py）：
- cube 使用右手坐标系，Y 轴向上；逻辑坐标未做整体旋转（拧魔方界面用
  camera 旋转视角，而非 `_whole_world`）。
- `_get_camera_basis()` 返回 world 系下的 (eye, right, camera_up, forward)。
- 投影：qx = dot(P-eye,right)/z, qy = dot(P-eye,camera_up)/z，
  z = dot(P-eye,forward)；屏幕 sx = wcx + (qx-pcx)*pixel_scale。

拖动->拧动规则：
- 从按下点screen 反投影出一条穿过魔方的射线，得到抓取点 g（world 坐标）。
- 对候选轴 {X,Y,Z}，计算该轴在 g 处的*切向*速度方向（正转时）
  t_screen = project(cross(axis_vec, g))。选轴 = 使 t_screen 与拖拽方向
  d 对齐最好的那根轴；符号 = sign(dot(d, t_screen))。
- 层坐标 = g 在该轴上最接近的离散层坐标；宽层模式在抓取最外层时并入
  同侧相邻内层。

返回 TwistSpec(axis, layer_positions, sign)：
    axis: 0/1/2
    layer_positions: 需要一起转的层坐标列表（含宽层时可能多个）
    sign: +1 表示绕 +axis 右手 +90°，-1 表示绕 +axis 右手 -90°。
"""

from typing import List, Optional, Tuple

from cube.coordinates import coord_values, get_d_maxc, FACE_SPEC

AXIS_VEC = {0: (1.0, 0.0, 0.0), 1: (0.0, 1.0, 0.0), 2: (0.0, 0.0, 1.0)}

# 右手系：绕 +axis 顺时针 90° 的坐标旋转（与 Mat4.rotation_axis(+90, axis) 一致）。
ROT_PLUS = {
    0: lambda x, y, z: (x, -z, y),
    1: lambda x, y, z: (z, y, -x),
    2: lambda x, y, z: (-y, x, z),
}


class TwistSpec:
    """一次拧动的完整描述。"""

    __slots__ = ("axis", "layer_positions", "sign")

    def __init__(self, axis: int, layer_positions: List[int], sign: int):
        self.axis = axis
        self.layer_positions = list(layer_positions)
        self.sign = sign

    def __repr__(self):
        return (f"TwistSpec(axis={self.axis}, "
                f"layers={self.layer_positions}, sign={self.sign})")


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(v):
    ln = (v[0] * v[0] + v[1] * v[1] + (v[2] * v[2] if len(v) > 2 else 0.0)) ** 0.5
    if ln <= 1e-12:
        return None
    return tuple(c / ln for c in v)


def _screen_ray(eye, right, camera_up, forward, pixel_scale,
                center_x, center_y, wcx, wcy, sx, sy):
    """由屏幕点反投影出世界空间射线方向（未归一化）。

    返回 (origin, dir) 使 P = origin + t*dir 命中该屏幕点。
    origin = eye，dir = qx*right + qy*camera_up + forward。
    """
    qx = (sx - wcx) / pixel_scale + center_x
    qy = (sy - wcy) / pixel_scale + center_y
    dx = qx * right[0] + qy * camera_up[0] + forward[0]
    dy = qx * right[1] + qy * camera_up[1] + forward[1]
    dz = qx * right[2] + qy * camera_up[2] + forward[2]
    return eye, (dx, dy, dz)


def _ray_box_hit(origin, direction, half):
    """射线 vs 轴对齐盒 [-half, half]^3。

    返回最近命中点的世界坐标；未命中返回 None。
    """
    tmin = -1e30
    tmax = 1e30
    for i in range(3):
        o = origin[i]
        d = direction[i]
        if abs(d) < 1e-12:
            if o < -half or o > half:
                return None
            continue
        t1 = (-half - o) / d
        t2 = (half - o) / d
        if t1 > t2:
            t1, t2 = t2, t1
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)
        if tmin > tmax:
            return None
    if tmax < 0:
        return None
    t = tmin if tmin > 0 else tmax
    return (origin[0] + t * direction[0],
            origin[1] + t * direction[1],
            origin[2] + t * direction[2])


def _nearest_slab(n, axis, value):
    vals = coord_values(n)
    return min(vals, key=lambda v: abs(v - value))


def _wide_positions(n, axis, slab):
    """宽层模式：抓取最外层时并入同侧相邻内层。"""
    vals = coord_values(n)
    outer = max(vals) if slab > 0 else min(vals)
    if slab != outer:
        return [slab]
    inner = None
    for v in vals:
        if 0 < abs(v) < abs(slab) and (v > 0) == (slab > 0):
            if inner is None or abs(v) > abs(inner):
                inner = v
    if inner is not None:
        return sorted([slab, inner])
    return [slab]


def resolve_twist(n, basis, pixel_scale, center_x, center_y,
                  wcx, wcy, drag_screen, grab_screen, wide=False,
                  grab_pos=None, grab_face=None):
    """把一次拖动解析为 TwistSpec。

    参数：
        n: 阶数。
        basis: (eye, right, camera_up, forward)，均 world 坐标。
        pixel_scale, center_x, center_y, wcx, wcy: CubeView._last_proj 的
            投影参数（用于反投影）。
        drag_screen: 本次累计拖动向量 (dx, dy)。dx 向右、dy 向上。
        grab_screen: 按下点屏幕坐标 (sx, sy)。
        wide: 是否宽层模式。
        grab_pos: 可选。接触的小面所属 cubie 的当前空间位置（层坐标）。
        grab_face: 可选。接触的小面所在的面名（如 "U"、"R"）。
            给定时按"面的上下左右"解析：在接触面的本地坐标系中，
            上下滑动转"行"对应层，左右滑动转"列"对应层，方向取滑动正负。
            （grab_pos + grab_face 即位"点哪个小面就动哪一层/列"。）
            两者都未给定时退回用射线命中魔方外盒 + 切向速度判断。

    返回 TwistSpec；无法解析（方向不明确）时返回 None。
    """
    eye, right, camera_up, forward = basis
    d_hat = _norm((drag_screen[0], drag_screen[1], 0.0))
    if d_hat is None:
        return None

    if grab_pos is not None and grab_face is not None:
        return _resolve_face_layer(n, basis, drag_screen, grab_pos,
                                   grab_face, wide)

    origin, direction = _screen_ray(
        eye, right, camera_up, forward,
        pixel_scale, center_x, center_y, wcx, wcy,
        grab_screen[0], grab_screen[1],
    )
    _d, maxc = get_d_maxc(n)
    g = _ray_box_hit(origin, direction, float(maxc))
    if g is None:
        return None

    # 若给定接触小面的 cubie 位置，则以其为动点（层=该块所在层）；
    # 否则用射线命中盒子的交点近似。
    if grab_pos is not None:
        g = tuple(float(v) for v in grab_pos)

    # 选轴 + 方向。
    best_axis = None
    best_score = 0.0
    best_sign = 1
    for axis in range(3):
        av = AXIS_VEC[axis]
        t = _cross(av, g)  # 正转时抓取点的速度方向
        t_screen = (t[0] * right[0] + t[1] * right[1] + t[2] * right[2],
                    t[0] * camera_up[0] + t[1] * camera_up[1] + t[2] * camera_up[2])
        t_hat = _norm(t_screen)
        if t_hat is None:
            continue
        score = abs(d_hat[0] * t_hat[0] + d_hat[1] * t_hat[1])
        if score > best_score:
            best_score = score
            best_axis = axis
            sgn = 1 if (d_hat[0] * t_hat[0] + d_hat[1] * t_hat[1]) >= 0 else -1
            best_sign = sgn

    if best_axis is None or best_score < 0.3:
        return None

    slab = _nearest_slab(n, best_axis, g[best_axis])
    if wide:
        slabs = _wide_positions(n, best_axis, slab)
    else:
        slabs = [slab]
    return TwistSpec(best_axis, slabs, best_sign)


def _axis_vec(axis, sign):
    """返回沿指定轴、指定符号的单位向量（world 坐标）。"""
    v = [0.0, 0.0, 0.0]
    v[axis] = float(sign)
    return tuple(v)


def _project_dir(vec, right, camera_up, forward):
    """把 world 向量投影到屏幕，返回归一化的屏幕方向；无法判定返回 None。"""
    sx = vec[0] * right[0] + vec[1] * right[1] + vec[2] * right[2]
    sy = vec[0] * camera_up[0] + vec[1] * camera_up[1] + vec[2] * camera_up[2]
    n = _norm((sx, sy, 0.0))
    if n is None:
        return None
    return (sx, sy)


def _resolve_face_layer(n, basis, drag_screen, grab_pos, grab_face, wide):
    """以"接触小面所在面的上下左右"解析一层转动。

    FACE_SPEC 定义每个面的 row_axis/row_sign 与 col_axis/col_sign。
    在接触面的二维视角里：
        - 上下滑动（行方向占主导）转"列"对应轴，让该面上下翻转；
        - 左右滑动（列方向占主导）转"行"对应轴，让该面左右摆动。
    两层各取接触小面所属 cubie 在该轴上的层坐标（即"点哪个小面就动
    哪一行/列"）；方向取滑动正负。

    返回 TwistSpec；方向不明确（如两方向投影都极小）时返回 None。
    """
    if grab_face not in FACE_SPEC:
        return None
    n_axis, n_sign, row_axis, row_sign, col_axis, col_sign = FACE_SPEC[grab_face]

    eye, right, camera_up, forward = basis
    d_hat = _norm((drag_screen[0], drag_screen[1], 0.0))
    if d_hat is None:
        return None

    t_row = _project_dir(_axis_vec(row_axis, row_sign), right, camera_up, forward)
    t_col = _project_dir(_axis_vec(col_axis, col_sign), right, camera_up, forward)
    if t_row is None or t_col is None:
        return None

    d_row = d_hat[0] * t_row[0] + d_hat[1] * t_row[1]
    d_col = d_hat[0] * t_col[0] + d_hat[1] * t_col[1]

    # 上下滑动（行方向占主导）→ 转"列"对应轴：让面在竖直方向翻转（面上下转）。
    # 左右滑动（列方向占主导）→ 转"行"对应轴：让面在水平方向摆动（面左右转）。
    if abs(d_row) >= abs(d_col):
        axis = col_axis
        slab = grab_pos[col_axis]
    else:
        axis = row_axis
        slab = grab_pos[row_axis]

    # 方向不明确（拖拽几乎垂直于该面的行/列方向）时放弃。
    if abs(d_row) < 0.2 and abs(d_col) < 0.2:
        return None

    # 正负统一用"该轴转动下抓取点的切向速度投影"与拖动方向的一致性判定：
    # 这样无论哪个面，都是朝拖动方向转，不会因各面朝向不同而出现有的面方向相反。
    av = AXIS_VEC[axis]
    g = (float(grab_pos[0]), float(grab_pos[1]), float(grab_pos[2]))
    t = _cross(av, g)  # 正转（sign=+1）时抓取点的速度方向
    t_screen = (t[0] * right[0] + t[1] * right[1] + t[2] * right[2],
                t[0] * camera_up[0] + t[1] * camera_up[1] + t[2] * camera_up[2])
    t_hat = _norm(t_screen)
    if t_hat is not None:
        sign = 1 if (d_hat[0] * t_hat[0] + d_hat[1] * t_hat[1]) >= 0 else -1
    else:
        # 抓取点恰在旋转轴线上（切向为零）时，退回用行/列方向正负。
        if abs(d_row) >= abs(d_col):
            sign = 1 if d_row >= 0 else -1
        else:
            sign = 1 if d_col >= 0 else -1

    if wide:
        slabs = _wide_positions(n, axis, slab)
    else:
        slabs = [slab]
    return TwistSpec(axis, slabs, sign)


def apply_layer_turn(cubies, axis, layer_positions, sign):
    """对给定 cubies dict 就地应用一次层转动（90°）。

    axis: 0/1/2；layer_positions: 该轴要转的层坐标集合；sign: 方向。
    原地修改并返回同一个 dict。
    """
    rot = ROT_PLUS[axis]
    if sign < 0:
        # 负方向 = 正方向 3 次（右手 -90°）。
        def _rot(p):
            return rot(*rot(*rot(*p)))
    else:
        def _rot(p):
            return rot(*p)

    selected = {}
    for pos, c in cubies.items():
        if pos[axis] in layer_positions:
            npos = _rot(pos)
            stickers = {_rot(d): col for d, col in c.stickers.items()}
            # 保持块身份 home 不变，只移动 pos 与 sticker 方向。
            c.pos = npos
            c.stickers = stickers
            selected[npos] = c
        else:
            selected[pos] = c
    cubies.clear()
    cubies.update(selected)
    return cubies
