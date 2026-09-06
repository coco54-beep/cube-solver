"""整体旋转 + 面访问导航（纯逻辑，可单元测试）。

该模块维护一个"显示整体旋转矩阵"（world），把魔方模型整体旋转，
使序列中当前面正对相机（法线 +Z）。逻辑魔方状态不被改动。

覆盖 6 个面的访问顺序 SEQ；每次 "下一步/上一步" 都是一次整体 90°
旋转（绕屏幕空间某根坐标轴），从而把序列中的上一个 / 下一个面转到
正对相机。旋转轴依据当前正对面的法线与其目标面法线在相机空间中的
方位计算得出。
"""

from cube.coordinates import FACE_NORMALS
from renderer.mat4 import Mat4

# 面访问顺序（F 起，依次整体翻转）
SEQ = ("F", "R", "U", "B", "L", "D")

_PZ = (0.0, 0.0, 1.0)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normals_to_axis(n_from, n_to):
    """给定两面法线（均为相机空间中单位坐标轴方向），返回把 n_from
    旋转到 n_to 所需的旋转轴。两法线垂直时叉积为一根坐标轴。"""
    a = _cross(n_from, n_to)
    # 若叉积为零（法线平行），不适用；相邻两面法线垂直，不会发生。
    return a


def _dir_of(v):
    """把屏幕平面向量 v 的主分量映射为方位：\"left\"/\"right\"/\"up\"/\"down\"。"""
    if abs(v[0]) >= abs(v[1]):
        return "right" if v[0] > 0 else "left"
    return "up" if v[1] > 0 else "down"


class CubeOrientation:
    """跟踪魔方整体显示旋转与当前正对面。"""

    def __init__(self, n):
        self.n = n
        self.index = 0
        self.world = Mat4()

    def current_face(self):
        return SEQ[self.index]

    def next_face(self):
        return SEQ[(self.index + 1) % len(SEQ)]

    def prev_face(self):
        return SEQ[(self.index - 1) % len(SEQ)]

    def _delta_for(self, target_face):
        """返回把 target_face 转正对相机所需的整体旋转参数 (angle, axis)。

        需要 world 变换后 target_face 的法线 q 映射到 +Z。
        q 与 +Z 垂直（因当前面正对且两面相邻），因此绕 cross(q, +Z) 转 90°
        即可，且该轴是一根坐标轴。
        """
        q = self.world.transform(*FACE_NORMALS[target_face])
        axis = _cross(q, _PZ)
        return (90.0, axis)

    def turn_next(self):
        """整体旋转到下一个面（不播放动画，仅更新数学状态）。"""
        angle, axis = self._delta_for(self.next_face())
        delta = Mat4.rotation_axis(angle, axis)
        self.world = delta * self.world
        self.index = (self.index + 1) % len(SEQ)
        return self.current_face()

    def turn_prev(self):
        """整体旋转回到上一个面。"""
        angle, axis = self._delta_for(self.prev_face())
        delta = Mat4.rotation_axis(angle, axis)
        self.world = delta * self.world
        self.index = (self.index - 1) % len(SEQ)
        return self.current_face()

    def next_axis_deg(self):
        """本次"下一步"将使用的整体旋转参数 (angle, axis)。"""
        return self._delta_for(self.next_face())

    def prev_axis_deg(self):
        """本次"上一步"将使用的整体旋转参数 (angle, axis)。"""
        return self._delta_for(self.prev_face())

    def face_for_world(self):
        """根据 world 矩阵反推正对 +Z 的面（用于断言/调试）。"""
        for face, n in FACE_NORMALS.items():
            v = self.world.transform(*n)
            if (
                abs(v[0]) < 1e-6
                and abs(v[1]) < 1e-6
                and abs(v[2] - 1.0) < 1e-6
            ):
                return face
        return None

    def screen_dir(self, face):
        """返回 face 正对相机之前所处的屏幕方位：\"left\"/\"right\"/\"up\"/\"down\"。

        相机正对 +Z（elevation/azimuth = 0）时，屏幕右方向为 +X、上方向为 +Y。
        当前 world 已让当前面正对 +Z，因此相邻 face 的法线经 world 变换后的
        X/Y 分量即为它在屏幕平面上的方位。
        """
        q = self.world.transform(*FACE_NORMALS[face])
        return _dir_of(q)

    def flip_dir(self, face):
        """返回把 face 转到正面时，魔方前端沿屏幕翻滚的方向。

        绕轴旋转把 face 法线 q 转到 +Z，同时把当前正面（+Z）转到 -q；
        因此\"翻转方向\"为 -q 所在屏幕方位（与 face 所处方位相反）。
        """
        q = self.world.transform(*FACE_NORMALS[face])
        return _dir_of((-q[0], -q[1], -q[2]))

    def next_dir(self):
        """当前\"下一步\"魔方翻转的屏幕方位。"""
        return self.flip_dir(self.next_face())

    def prev_dir(self):
        """当前\"上一步\"魔方翻转的屏幕方位。"""
        return self.flip_dir(self.prev_face())
