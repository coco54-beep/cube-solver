"""轻量 3D 数学：向量与矩阵（无 numpy 依赖）。

采用右手系，Y 轴向上。基于 Kivy 的 Matrix 指令做视图/投影变换，
避免在 Android 打包中引入 numpy。
"""

import math

from kivy.graphics.transformation import Matrix as KivyMatrix


def rotation_matrix_x(deg):
    m = KivyMatrix()
    m = m.rotate(math.radians(deg), 1, 0, 0)
    return m


def rotation_matrix_y(deg):
    m = KivyMatrix()
    m = m.rotate(math.radians(deg), 0, 1, 0)
    return m


def rotation_matrix_z(deg):
    m = KivyMatrix()
    m = m.rotate(math.radians(deg), 0, 0, 1)
    return m


def translation_matrix(tx, ty, tz):
    m = KivyMatrix()
    m = m.translate(tx, ty, tz)
    return m


def scale_matrix(s):
    m = KivyMatrix()
    m = m.scale(s, s, s)
    return m


def look_at_matrix(eye, target=(0, 0, 0), up=(0, 1, 0)):
    """视图矩阵：从 eye 看向 target。返回 Kivy Matrix（行优先）。"""
    ex, ey, ez = eye
    tx, ty, tz = target
    ux, uy, uz = up

    # forward = normalize(target - eye)
    fx, fy, fz = tx - ex, ty - ey, tz - ez
    fl = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / fl, fy / fl, fz / fl

    # side = normalize(forward x up)
    sx = fy * uz - fz * uy
    sy = fz * ux - fx * uz
    sz = fx * uy - fy * ux
    sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
    sx, sy, sz = sx / sl, sy / sl, sz / sl

    # up2 = side x forward
    u2x = sy * fz - sz * fy
    u2y = sz * fx - sx * fz
    u2z = sx * fy - sy * fx

    # 视图矩阵（行优先，Kivy 列存储，需转置写入）
    m = KivyMatrix()
    m.set([
        sx, u2x, -fx, 0.0,
        sy, u2y, -fy, 0.0,
        sz, u2z, -fz, 0.0,
        -(sx * ex + sy * ey + sz * ez),
        -(u2x * ex + u2y * ey + u2z * ez),
        (fx * ex + fy * ey + fz * ez),
        1.0,
    ])
    return m


def perspective_matrix(fov_deg, aspect, near, far):
    """透视投影矩阵。返回 Kivy Matrix（行优先）。"""
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    a = aspect
    n, ff = near, far

    m = KivyMatrix()
    m.set([
        f / a, 0.0, 0.0, 0.0,
        0.0, f, 0.0, 0.0,
        0.0, 0.0, (ff + n) / (n - ff), -1.0,
        0.0, 0.0, (2 * ff * n) / (n - ff), 0.0,
    ])
    return m


def transform_point(m, x, y, z):
    """用 Kivy Matrix 变换一个 3D 点，返回 (x, y, z)。"""
    v = m.transform_point(x, y, z)
    return (v[0], v[1], v[2])


class OrbitCamera:
    """轨道相机：绕目标点旋转。

    elevation: 仰角（度），azimuth: 方位角（度），distance: 距离。
    """

    def __init__(self, elevation=22.0, azimuth=35.0, distance=9.0,
                 target=(0, 0, 0)):
        self.elevation = elevation
        self.azimuth = azimuth
        self.distance = distance
        self.target = target

    @property
    def eye(self):
        r = self.distance
        el = math.radians(self.elevation)
        az = math.radians(self.azimuth)
        x = self.target[0] + r * math.cos(el) * math.sin(az)
        y = self.target[1] + r * math.sin(el)
        z = self.target[2] + r * math.cos(el) * math.cos(az)
        return (x, y, z)

    def view_matrix(self):
        return look_at_matrix(self.eye, self.target)

    def rotate(self, d_az, d_el):
        self.azimuth += d_az
        self.elevation += d_el
        # 收窄到 ±80°，避免相机几乎到正上/正下时透视畸变，
        # 让"旋转"看起来像"缩放"。
        self.elevation = max(-80, min(80, self.elevation))

    def zoom(self, factor):
        self.distance *= factor
        self.distance = max(2.0, min(60.0, self.distance))
