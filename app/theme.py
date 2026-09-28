"""主题：浅色 / 深色两套色板 + 系统模式检测 + 运行期切换。

用法：
    应用持有一个 Theme 实例（app.theme）。所有 KV / Python 颜色都引用
    app.theme.<token>。切换主题时只需调用 app.set_theme_mode(mode)，
    Theme 的各颜色属性会被原地更新，已绑定的控件随之自动重绘。
"""

import os
import sys

from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ColorProperty
from kivy.utils import get_color_from_hex

# ---- 模式 ----
AUTO = "auto"
LIGHT = "light"
DARK = "dark"
MODES = (AUTO, LIGHT, DARK)


def _hex(v):
    return get_color_from_hex(v)


# ===== 色板（现代深色 & 清爽浅色，含阴影/强调色/描边） =====
DARK_PALETTE = {
    "bg": _hex("080D16"),
    "surface": _hex("101927"),
    "surface_hi": _hex("172438"),
    "card_shadow": (0.0, 0.0, 0.0, 0.32),
    "card_border": _hex("273A50"),
    "text": _hex("EAF4FC"),
    "text_muted": _hex("A0B4C7"),
    "text_faint": _hex("6D849B"),
    "button": _hex("142236"),
    "button_pressed": _hex("1B3448"),
    "button_text": _hex("EAF4FC"),
    "disabled_text": _hex("61758A"),
    "accent": _hex("54DDF4"),
    "accent_dim": _hex("175B70"),
    "primary": _hex("08A995"),
    "primary_pressed": _hex("18C7AF"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("CF526B"),
    "danger_pressed": _hex("E3657B"),
    "danger_text": (1, 1, 1, 1),
    "border": _hex("273A50"),
}

LIGHT_PALETTE = {
    "bg": _hex("EDF4F8"),
    "surface": _hex("F8FCFF"),
    "surface_hi": _hex("FFFFFF"),
    "card_shadow": (0.16, 0.34, 0.42, 0.12),
    "card_border": _hex("CDDEE7"),
    "text": _hex("10232F"),
    "text_muted": _hex("536B7A"),
    "text_faint": _hex("8296A4"),
    "button": _hex("E4EEF3"),
    "button_pressed": _hex("D6E7ED"),
    "button_text": _hex("10232F"),
    "disabled_text": _hex("A4B4BD"),
    "accent": _hex("087F9B"),
    "accent_dim": _hex("CBEAF0"),
    "primary": _hex("008F7E"),
    "primary_pressed": _hex("00A994"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("C94D64"),
    "danger_pressed": _hex("DE5B72"),
    "danger_text": (1, 1, 1, 1),
    "border": _hex("CDDEE7"),
}


class Theme(EventDispatcher):
    """持有一组主题颜色属性；切换时原地更新各属性以触发重绘。"""

    bg = ColorProperty([0.031, 0.051, 0.086, 1])
    surface = ColorProperty([0.063, 0.098, 0.153, 1])
    surface_hi = ColorProperty([0.09, 0.141, 0.22, 1])
    card_shadow = ColorProperty([0.0, 0.0, 0.0, 0.32])
    card_border = ColorProperty([0.153, 0.227, 0.314, 1])
    text = ColorProperty([0.918, 0.957, 0.988, 1])
    text_muted = ColorProperty([0.627, 0.706, 0.78, 1])
    text_faint = ColorProperty([0.427, 0.518, 0.608, 1])
    button = ColorProperty([0.078, 0.133, 0.212, 1])
    button_pressed = ColorProperty([0.106, 0.204, 0.282, 1])
    button_text = ColorProperty([0.918, 0.957, 0.988, 1])
    disabled_text = ColorProperty([0.38, 0.459, 0.541, 1])
    accent = ColorProperty([0.329, 0.867, 0.957, 1])
    accent_dim = ColorProperty([0.09, 0.357, 0.439, 1])
    primary = ColorProperty([0.031, 0.663, 0.584, 1])
    primary_pressed = ColorProperty([0.094, 0.78, 0.686, 1])
    primary_text = ColorProperty([1, 1, 1, 1])
    danger = ColorProperty([0.812, 0.322, 0.420, 1])
    danger_pressed = ColorProperty([0.890, 0.396, 0.482, 1])
    danger_text = ColorProperty([1, 1, 1, 1])
    border = ColorProperty([0.153, 0.227, 0.314, 1])

    def apply(self, is_dark: bool):
        pal = DARK_PALETTE if is_dark else LIGHT_PALETTE
        for key, val in pal.items():
            setattr(self, key, val)
        self.dispatch("on_palette")

    # 触发一次性调色板事件，供绑定在 Python 里的控件刷新。
    __events__ = ("on_palette",)

    def on_palette(self, *args):
        pass


# ===== 系统模式检测 =====
def system_is_dark() -> bool:
    """尽最大努力检测系统是否为深色模式；无法判断时返回 None。"""
    try:
        if sys.platform == "win32":
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
                return val == 0
    except Exception:
        pass

    try:
        if sys.platform.startswith("linux") and "ANDROID" in (os.environ or {}):
            # Android: 读取系统 UI 模式（尽力而为）。读取失败返回 None。
            try:
                import android  # noqa: F401
            except Exception:
                pass
    except Exception:
        pass
    return None


def resolve_dark(mode: str, default_dark: bool = True):
    """把 模式 + 系统检测解析成 is_dark。"""
    if mode == LIGHT:
        return False
    if mode == DARK:
        return True
    # auto
    detected = system_is_dark()
    return default_dark if detected is None else detected


# ===== 用户主题模式持久化 =====
def load_saved_mode() -> str:
    """读取上次保存的主题模式；无效或不存在时返回 AUTO。"""
    try:
        from app.prefs import get
        mode = get("theme_mode")
        return mode if mode in MODES else DARK
    except Exception:
        return DARK


def save_mode(mode: str):
    try:
        from app.prefs import set as _set
        _set("theme_mode", mode)
    except Exception:
        pass

