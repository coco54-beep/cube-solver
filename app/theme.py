"""主题：浅色 / 深色两套色板 + 系统模式检测 + 运行期切换。

用法：
    应用持有一个 Theme 实例（app.theme）。所有 KV / Python 颜色都引用
    app.theme.<token>。切换主题时只需调用 app.set_theme_mode(mode)，
    Theme 的各颜色属性会被原地更新，已绑定的控件随之自动重绘。
"""

import os
import sys
import json
import platform

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
    "bg": _hex("0e1521"),
    "surface": _hex("1a2436"),
    "surface_hi": _hex("23304a"),
    "card_shadow": (0.0, 0.0, 0.0, 0.5),
    "card_border": _hex("2e3e59"),
    "text": _hex("eef2f8"),
    "text_muted": _hex("9fb0c5"),
    "text_faint": _hex("6d7d95"),
    "button": _hex("24334c"),
    "button_pressed": _hex("31445f"),
    "button_text": _hex("eef2f8"),
    "disabled_text": _hex("5b6779"),
    "accent": _hex("58b6ff"),
    "accent_dim": _hex("2c6a99"),
    "primary": _hex("2f9e63"),
    "primary_pressed": _hex("37bd77"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("d05a5a"),
    "danger_pressed": _hex("e06565"),
    "danger_text": (1, 1, 1, 1),
    "border": _hex("2e3e59"),
}

LIGHT_PALETTE = {
    "bg": _hex("f4f6f9"),
    "surface": _hex("ffffff"),
    "surface_hi": _hex("eef1f6"),
    "card_shadow": (0.35, 0.42, 0.55, 0.30),
    "card_border": _hex("dfe4ec"),
    "text": _hex("1c2430"),
    "text_muted": _hex("5a6675"),
    "text_faint": _hex("8b95a5"),
    "button": _hex("eef1f6"),
    "button_pressed": _hex("e0e6ef"),
    "button_text": _hex("1c2430"),
    "disabled_text": _hex("aab3c0"),
    "accent": _hex("2f7fd6"),
    "accent_dim": _hex("cfe1f6"),
    "primary": _hex("2f9e63"),
    "primary_pressed": _hex("37bd77"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("d05a5a"),
    "danger_pressed": _hex("e06565"),
    "danger_text": (1, 1, 1, 1),
    "border": _hex("dfe4ec"),
}


class Theme(EventDispatcher):
    """持有一组主题颜色属性；切换时原地更新各属性以触发重绘。"""

    bg = ColorProperty([0.055, 0.082, 0.129, 1])
    surface = ColorProperty([0.102, 0.141, 0.212, 1])
    surface_hi = ColorProperty([0.137, 0.188, 0.290, 1])
    card_shadow = ColorProperty([0.0, 0.0, 0.0, 0.5])
    card_border = ColorProperty([0.18, 0.243, 0.349, 1])
    text = ColorProperty([0.933, 0.949, 0.973, 1])
    text_muted = ColorProperty([0.624, 0.690, 0.773, 1])
    text_faint = ColorProperty([0.427, 0.49, 0.584, 1])
    button = ColorProperty([0.141, 0.2, 0.298, 1])
    button_pressed = ColorProperty([0.192, 0.267, 0.373, 1])
    button_text = ColorProperty([0.933, 0.949, 0.973, 1])
    disabled_text = ColorProperty([0.357, 0.404, 0.475, 1])
    accent = ColorProperty([0.345, 0.714, 1.0, 1])
    accent_dim = ColorProperty([0.173, 0.416, 0.6, 1])
    primary = ColorProperty([0.184, 0.62, 0.388, 1])
    primary_pressed = ColorProperty([0.216, 0.741, 0.467, 1])
    primary_text = ColorProperty([1, 1, 1, 1])
    danger = ColorProperty([0.816, 0.353, 0.353, 1])
    danger_pressed = ColorProperty([0.878, 0.396, 0.396, 1])
    danger_text = ColorProperty([1, 1, 1, 1])
    border = ColorProperty([0.18, 0.243, 0.349, 1])

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
_PREFS_FILE = os.path.join(os.path.expanduser("~"), ".cubesolver_prefs.json")


def load_saved_mode() -> str:
    """读取上次保存的主题模式；无效或不存在时返回 AUTO。"""
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        mode = data.get("theme_mode")
        return mode if mode in MODES else AUTO
    except Exception:
        return AUTO


def save_mode(mode: str):
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme_mode": mode}, f)
    except Exception:
        pass

