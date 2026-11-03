"""Order-picker labels put the order first in every language."""

import pytest

from app.i18n import set_language
from ui.screens.irregular_directory_screen import format_order_label


@pytest.fixture(autouse=True)
def _restore_language():
    yield
    set_language("zh")


def test_chinese_order_label_moves_order_to_front():
    set_language("zh")
    assert format_order_label("镜面·3阶", 3) == "3 阶 · 镜面"
    assert format_order_label("彭罗斯二阶", 2) == "2 阶 · 彭罗斯"


def test_english_order_label_uses_one_prefix():
    set_language("en")
    assert format_order_label("FTO · 3 layers", 3) == "Order 3 · FTO"
    assert format_order_label("3 · Skewb", 3) == "Order 3 · Skewb"


def test_japanese_order_label_uses_one_prefix():
    set_language("ja")
    assert format_order_label("3段 · 八面体", 3) == "3 段 · 八面体"
    assert format_order_label("FTO · 3段八面体", 3) == "3 段 · FTO 八面体"
