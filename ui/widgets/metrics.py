"""统一响应式尺寸：让按钮/输入等交互控件随窗口高度缩放，适配高分辨率屏幕。

背景：各屏幕用固定像素高度（如 size_hint_y=None, height=52）。在 Kivy 的
Android 环境里窗口坐标是物理像素，若始终保持 52px，则在 1080p 等高分屏上
按钮相对屏幕会变得很小、难以点击（720p 尚可，1080p 就很难按）。

本模块按「窗口高度 / 基准高度」计算缩放因子，把固定的 dp 值映射为随窗口
增大的物理像素，使按钮在任何分辨率屏幕上占比一致、都好按。桌面上窗口高度
通常在 600~1000 之间，缩放后仍接近原值（几乎无感知）；Android 高分屏则按
比例放大，保证触控目标足够大。
"""

from kivy.core.window import Window

# 基准窗口高度：当前 UI 在约 800px 高的窗口下手感最佳（按钮 52px 等）。
_BASE_H = 800.0
# 缩放范围：下限 1.0 保证在普通桌面窗口（可能小于基准高）下按钮绝不比原设计
# 更小（原设计即 52px 固定值）；上限避免极端高分屏下按钮过大。
_MIN_S = 1.0
_MAX_S = 6.0

_scale_cache = None


def _scale():
    """按窗口长边缩放，旋转时保持触控尺寸一致（带钳制）。"""
    global _scale_cache
    # The same phone should retain its touch target size when rotated.
    h = max(Window.width, Window.height) if Window.height else _BASE_H
    s = h / _BASE_H
    s = min(max(s, _MIN_S), _MAX_S)
    _scale_cache = s
    return s


def h(px):
    """把一个基准像素高度缩放为当前窗口下的像素高度。"""
    return int(round(px * _scale()))


def font(px):
    """缩放字号（注：Kivy 的 sp 本身按 density 处理，这里主要处理按键视觉比例）。"""
    return px * _scale()


def scale_factor():
    """返回当前缩放因子（供特殊布局按需使用）。"""
    return _scale()


def menu_grid_metrics(width, height):
    """Keep the six home and puzzle-directory cards identical in size."""
    wide = width > height
    columns, rows = (3, 2) if wide else (2, 3)
    padding = (h(20), h(10), h(20), h(10))
    spacing = h(8)
    gap = h(12)
    top_height, bottom_height = h(44), h(28)
    head_height = min(h(96 if wide else 132), height * .20)
    reserved = (padding[1] + padding[3] + 7 * spacing
                + top_height + bottom_height + head_height)
    card_width = (width - padding[0] - padding[2] - (columns-1)*gap) / columns
    card_height = max(1, min(card_width, (height-reserved-(rows-1)*gap) / rows))
    return dict(columns=columns, padding=padding, spacing=spacing, gap=gap,
                top_height=top_height, bottom_height=bottom_height,
                head_height=head_height, grid_height=rows*card_height+(rows-1)*gap)


def input_grid_metrics(rows, column_gap=8, row_gap=6):
    """Share exact tile dimensions between input colors and action buttons.

    Scale each component first, then derive the total height so rounding cannot
    make a color tile and its matching action button differ in height.
    """
    tile_height = h(48)
    horizontal_gap, vertical_gap = h(column_gap), h(row_gap)
    side_padding, vertical_padding = h(28), h(4)
    return {
        "height": rows * tile_height + (rows - 1) * vertical_gap + 2 * vertical_padding,
        "spacing": (horizontal_gap, vertical_gap),
        "padding": (side_padding, vertical_padding, side_padding, vertical_padding),
    }
