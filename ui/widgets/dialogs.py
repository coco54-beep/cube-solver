"""主题化 Popup 辅助。

Kivy 默认 Popup 的背景是深色贴图，浅色主题下 `app.theme.text`（深色）会与
深色底撞色、文字看不清。这里把背景替换为主题 surface 色，使浅/深主题都清晰。
"""

from kivy.graphics import Color, Rectangle


def theme_popup(popup, theme):
    """把 Popup 背景替换为 theme.surface（去掉默认深色底图）。返回 popup。"""
    try:
        popup.background = ""
    except Exception:
        pass
    with popup.canvas.before:
        popup._theme_bg_color = Color(*theme.surface)
        popup._theme_bg_rect = Rectangle(pos=popup.pos, size=popup.size)

    def _sync(*_a):
        popup._theme_bg_rect.pos = popup.pos
        popup._theme_bg_rect.size = popup.size

    popup.bind(pos=_sync, size=_sync)
    return popup
