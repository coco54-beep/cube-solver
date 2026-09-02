"""中文字体注册：让 Kivy 的 Label/Button 默认显示中文。

把 Noto Sans SC 注册为默认字体（Roboto）的替代，使所有文本直接渲染中文，
无需在每个控件上单独指定 font_name。
"""

import os

from kivy.core.text import LabelBase, DEFAULT_FONT

_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansSC.ttf")


def setup_cjk_font():
    """注册中文字体为默认。可重复调用（幂等）。"""
    path = os.path.abspath(_FONT_PATH)
    if not os.path.exists(path):
        return False
    LabelBase.register(name=DEFAULT_FONT, fn_regular=path)
    return True
