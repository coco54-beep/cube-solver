"""轻量 4x4 矩阵（列主序，OpenGL 风格，纯 Python），用于顶点投影。

存储：m[col*4 + row]（列优先）。顶点视为列向量，变换为 M * v：
    out[x] = m[0]*x + m[4]*y + m[8]*z + m[12]
    out[y] = m[1]*x + m[5]*y + m[9]*z + m[13]
    out[z] = m[2]*x + m[6]*y + m[10]*z + m[14]
    out[w] = m[3]*x + m[7]*y + m[11]*z + m[15]
"""

import math


class Mat4:
    __slots__ = ("m",)

    def __init__(self, values=None):
        if values is None:
            self.m = (1, 0, 0, 0,
                      0, 1, 0, 0,
                      0, 0, 1, 0,
                      0, 0, 0, 1)
        else:
            self.m = tuple(values)

    # ---- 构造：标准列主序 ----
    @classmethod
    def perspective(cls, fov_deg, aspect, near, far):
        f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
        a = aspect
        n, ff = near, far
        return cls((
            f / a, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (ff + n) / (n - ff), -1,
            0, 0, (2 * ff * n) / (n - ff), 0,
        ))

    @classmethod
    def look_at(cls, eye, target=(0, 0, 0), up=(0, 1, 0)):
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
        # 列主序视图矩阵：行向量分别为 (s, u2, -f)，平移为 -dot(axis, eye)
        return cls((
            sx, u2x, -fx, 0,
            sy, u2y, -fy, 0,
            sz, u2z, -fz, 0,
            -(sx * ex + sy * ey + sz * ez),
            -(u2x * ex + u2y * ey + u2z * ez),
            (fx * ex + fy * ey + fz * ez),
            1,
        ))

    @classmethod
    def translation(cls, tx, ty, tz):
        return cls((1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    tx, ty, tz, 1))

    @classmethod
    def rotation_axis(cls, deg, axis):
        r = math.radians(deg)
        c = math.cos(r)
        s = math.sin(r)
        x, y, z = axis
        return cls((
            c + x * x * (1 - c), y * x * (1 - c) + z * s, z * x * (1 - c) - y * s, 0,
            x * y * (1 - c) - z * s, c + y * y * (1 - c), z * y * (1 - c) + x * s, 0,
            x * z * (1 - c) + y * s, y * z * (1 - c) - x * s, c + z * z * (1 - c), 0,
            0, 0, 0, 1,
        ))

    # ---- 运算 ----
    def __mul__(self, other):
        """返回 self * other（列向量约定）。"""
        a, b = self.m, other.m
        # 结果 r[c][r] = sum_k a[k][r] * b[c][k]
        # a[k][r] = a[k*4+r]; b[c][k] = b[c*4+k]
        return Mat4((
            a[0]*b[0]+a[4]*b[1]+a[8]*b[2]+a[12]*b[3],
            a[1]*b[0]+a[5]*b[1]+a[9]*b[2]+a[13]*b[3],
            a[2]*b[0]+a[6]*b[1]+a[10]*b[2]+a[14]*b[3],
            a[3]*b[0]+a[7]*b[1]+a[11]*b[2]+a[15]*b[3],
            a[0]*b[4]+a[4]*b[5]+a[8]*b[6]+a[12]*b[7],
            a[1]*b[4]+a[5]*b[5]+a[9]*b[6]+a[13]*b[7],
            a[2]*b[4]+a[6]*b[5]+a[10]*b[6]+a[14]*b[7],
            a[3]*b[4]+a[7]*b[5]+a[11]*b[6]+a[15]*b[7],
            a[0]*b[8]+a[4]*b[9]+a[8]*b[10]+a[12]*b[11],
            a[1]*b[8]+a[5]*b[9]+a[9]*b[10]+a[13]*b[11],
            a[2]*b[8]+a[6]*b[9]+a[10]*b[10]+a[14]*b[11],
            a[3]*b[8]+a[7]*b[9]+a[11]*b[10]+a[15]*b[11],
            a[0]*b[12]+a[4]*b[13]+a[8]*b[14]+a[12]*b[15],
            a[1]*b[12]+a[5]*b[13]+a[9]*b[14]+a[13]*b[15],
            a[2]*b[12]+a[6]*b[13]+a[10]*b[14]+a[14]*b[15],
            a[3]*b[12]+a[7]*b[13]+a[11]*b[14]+a[15]*b[15],
        ))

    def transform4(self, x, y, z, w=1.0):
        """应用 M * v（列向量）。返回 (x, y, z, w)。"""
        m = self.m
        return (
            m[0]*x + m[4]*y + m[8]*z + m[12]*w,
            m[1]*x + m[5]*y + m[9]*z + m[13]*w,
            m[2]*x + m[6]*y + m[10]*z + m[14]*w,
            m[3]*x + m[7]*y + m[11]*z + m[15]*w,
        )

    def transform(self, x, y, z):
        r = self.transform4(x, y, z, 1.0)
        return (r[0], r[1], r[2])
