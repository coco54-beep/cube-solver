"""颜色常量定义。

默认面配色（相对方向一致）：
U = 白 (W), D = 黄 (Y), F = 绿 (G), B = 蓝 (B), R = 红 (R), L = 橙 (O)
"""

# 六种允许颜色（内部键）
VALID_COLORS = ("W", "Y", "R", "O", "B", "G")

# 中文名称
COLOR_NAMES = {
    "W": "白",
    "Y": "黄",
    "R": "红",
    "O": "橙",
    "B": "蓝",
    "G": "绿",
}

# 默认面配色：面 -> 中心颜色
DEFAULT_COLORS = {
    "U": "W",
    "D": "Y",
    "F": "G",
    "B": "B",
    "R": "R",
    "L": "O",
}


def is_valid_color(c: str) -> bool:
    """判断是否为允许的六种颜色之一。"""
    return c in VALID_COLORS
