"""可复用的视觉效果：柔和投影 + 垂直渐变。

Kivy 没有内建 CSS 级阴影/渐变，这里提供：
- soft_shadow(): 在控件后方叠几层半透明圆角矩形，模拟柔和投影。
- gradient():    用 stencil 把一层垂直渐变裁剪成圆角矩形，模拟渐变背景。
"""

from kivy.graphics import (Color, Line, Rectangle, RoundedRectangle)
from kivy.graphics.instructions import InstructionGroup


def lighten(rgba, amount=0.25):
    """把颜色向白色方向提亮 amount（0~1）。"""
    k = amount
    return (min(rgba[0] + (1 - rgba[0]) * k, 1),
            min(rgba[1] + (1 - rgba[1]) * k, 1),
            min(rgba[2] + (1 - rgba[2]) * k, 1),
            rgba[3])


def darken(rgba, amount=0.25):
    """把颜色向黑色方向压暗 amount（0~1）。"""
    k = 1 - amount
    return (rgba[0] * k, rgba[1] * k, rgba[2] * k, rgba[3])


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t,
            a[3] + (b[3] - a[3]) * t)


def gradient(top, bottom, pos, size, radius=None, steps=16):
    """在给定区域铺一张垂直渐变（top->bottom），底部为圆角矩形。

    实现：先画一个圆角实心底（用 bottom 色，保证右下/右下圆角正确），
    再在内部叠加多层 end- inset 的直角 Rectangle 渐变条带。条带左右内缩
    radius，避免直角角戳出圆角之外。
    返回 InstructionGroup；尺寸变化时调用方需重建。
    """
    group = InstructionGroup()
    gx, gy = pos
    gw, gh = size
    r = radius if radius else 0

    # 圆角底（用 bottom 色填充整体轮廓）
    group.add(Color(*bottom))
    group.add(RoundedRectangle(pos=(gx, gy), size=(gw, gh), radius=[r] * 4))

    # 渐变条带（左右内缩 r）
    inset = r
    band_h = gh / max(steps, 1)
    bw = gw - inset * 2
    for i in range(steps):
        f = i / float(max(steps - 1, 1))
        c = _lerp(top, bottom, f)
        y = gy + f * (gh - band_h)
        group.add(Color(*c))
        group.add(Rectangle(pos=(gx + inset, y), size=(bw, band_h + 0.5)))
    return group


def soft_shadow(pos, size, radius, shadow_rgba, layers=3, spread=4.0, blur=6.0):
    """在 pos/size 区域后方叠多层半透明圆角矩形，模拟柔和投影。

    返回为平铺指令列表（Color, RoundedRectangle, ...），调用方把它加入
    widget.canvas.before。spread 控制阴影外扩，blur 控制柔和程度。
    """
    inst = []
    for i in range(layers):
        p = i / float(max(layers - 1, 1))
        inset = spread * (1.0 - p) * 0.5
        alpha = shadow_rgba[3] * (1.0 - p) ** 2.5
        col = Color(*shadow_rgba[:3], alpha)
        rr = RoundedRectangle(
            pos=(pos[0] - spread + inset, pos[1] - blur + inset * 0.5),
            size=(size[0] + spread * 2 - inset * 2, size[1] + blur - inset),
            radius=[radius + spread * 0.6] * 4,
        )
        inst.append(col)
        inst.append(rr)
    # 恢复不透明色，避免影响后续绘制。
    inst.append(Color(1, 1, 1, 1))
    return inst
