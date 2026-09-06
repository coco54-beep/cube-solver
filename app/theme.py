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


# ===== 色板（柔和暖浅色 & 现在使用的深色） =====
DARK_PALETTE = {
    "bg": _hex("12141c"),
    "surface": _hex("2b3a56"),
    "surface_hi": _hex("33445f"),
    "text": (1, 1, 1, 1),
    "text_muted": (0.75, 0.78, 0.85, 1),
    "text_faint": (0.5, 0.53, 0.62, 1),
    "button": _hex("2b3a55"),
    "button_pressed": _hex("3d5175"),
    "button_text": (1, 1, 1, 1),
    "disabled_text": (0.5, 0.5, 0.55, 1),
    "primary": _hex("2e7d4f"),
    "primary_pressed": _hex("3d9b62"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("7d3b3b"),
    "danger_pressed": _hex("9b5050"),
    "danger_text": (1, 1, 1, 1),
    "border": (0.05, 0.05, 0.05, 1),
}

LIGHT_PALETTE = {
    "bg": _hex("faf6ef"),
    "surface": _hex("efe7d8"),
    "surface_hi": _hex("e5dac6"),
    "text": (0.23, 0.20, 0.17, 1),
    "text_muted": (0.44, 0.39, 0.33, 1),
    "text_faint": (0.57, 0.52, 0.46, 1),
    "button": _hex("e3d8c4"),
    "button_pressed": _hex("d6c8ae"),
    "button_text": (0.22, 0.19, 0.16, 1),
    "disabled_text": (0.66, 0.62, 0.56, 1),
    "primary": _hex("4d9460"),
    "primary_pressed": _hex("3f8151"),
    "primary_text": (1, 1, 1, 1),
    "danger": _hex("c05b5b"),
    "danger_pressed": _hex("ab4a4a"),
    "danger_text": (1, 1, 1, 1),
    "border": _hex("d3c8b6"),
}


class Theme(EventDispatcher):
    """持有一组主题颜色属性；切换时原地更新各属性以触发重绘。"""

    bg = ColorProperty([0.070, 0.078, 0.109, 1])
    surface = ColorProperty([0.169, 0.227, 0.337, 1])
    surface_hi = ColorProperty([0.2, 0.267, 0.373, 1])
    text = ColorProperty([1, 1, 1, 1])
    text_muted = ColorProperty([0.75, 0.78, 0.85, 1])
    text_faint = ColorProperty([0.5, 0.53, 0.62, 1])
    button = ColorProperty([0.169, 0.227, 0.333, 1])
    button_pressed = ColorProperty([0.239, 0.318, 0.459, 1])
    button_text = ColorProperty([1, 1, 1, 1])
    disabled_text = ColorProperty([0.5, 0.5, 0.55, 1])
    primary = ColorProperty([0.18, 0.49, 0.31, 1])
    primary_pressed = ColorProperty([0.239, 0.608, 0.384, 1])
    primary_text = ColorProperty([1, 1, 1, 1])
    danger = ColorProperty([0.49, 0.231, 0.231, 1])
    danger_pressed = ColorProperty([0.608, 0.314, 0.314, 1])
    danger_text = ColorProperty([1, 1, 1, 1])
    border = ColorProperty([0.05, 0.05, 0.05, 1])

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

