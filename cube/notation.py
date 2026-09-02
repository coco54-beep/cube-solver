"""公式解析器：解析、标准化、逆公式。

Move 三元组表示: (label, is_wide, count)
    label:   "R"/"L"/"U"/"D"/"F"/"B"/"x"/"y"/"z"
    is_wide: 是否宽层 (True/False)
    count:   顺时针90度次数, 1/2/3

后缀规则：
    无后缀 -> 1 (顺时针90度)
    '      -> 3 (逆时针90度)
    ''     -> 2 (180度, 双撇号写法)
    2      -> 2
    3      -> 3

小写 (r/u/...) 等价于宽层 (Rw/Uw/...)。
x/y/z 为整体转动，无宽层概念。
"""

from typing import List, Tuple

Move = Tuple[str, bool, int]

# 合法面标签
FACE_LABELS = ("R", "L", "U", "D", "F", "B")
WHOLE_LABELS = ("x", "y", "z")

# 后缀 -> 次数
_SUFFIX_MAP = {
    "": 1,
    "'": 3,
    "''": 2,
    "2": 2,
    "3": 3,
}


def parse_suffix(suffix: str) -> int:
    """后缀 -> 顺时针90度次数。非法后缀抛 ValueError。"""
    if suffix not in _SUFFIX_MAP:
        raise ValueError(f"非法公式后缀: {suffix!r}")
    return _SUFFIX_MAP[suffix]


def suffix_for_count(count: int) -> str:
    """次数 -> 后缀（1->'', 2->'2', 3->"'"）。"""
    if count == 1:
        return ""
    if count == 2:
        return "2"
    if count == 3:
        return "'"
    raise ValueError(f"非法次数: {count}")


def normalize_label_base(base: str) -> str:
    """小写面标签转大写；x/y/z 保持小写。"""
    if base in WHOLE_LABELS:
        return base
    up = base.upper()
    if up in FACE_LABELS:
        return up
    raise ValueError(f"非法公式标签: {base!r}")


def parse_move_str(s: str, allow_wide: bool = True) -> Move:
    """解析单个动作字符串为 (label, is_wide, count)。

    例: "R"->("R",False,1)  "R'"->("R",False,3)  "R2"->("R",False,2)
        "r"->("R",True,1)   "x2"->("x",False,2)
    """
    s = s.strip()
    if not s:
        raise ValueError("空动作")
    first = s[0]
    if first in ("R", "L", "U", "D", "F", "B"):
        base = first
        is_wide = False
        rest = s[1:]
    elif first in ("r", "l", "u", "d", "f", "b"):
        # 小写 = 宽层
        base = first.upper()
        is_wide = True
        rest = s[1:]
    elif first in ("x", "y", "z"):
        base = first
        is_wide = False
        rest = s[1:]
    else:
        raise ValueError(f"非法公式起始字符: {first!r}")

    if not allow_wide and is_wide:
        raise ValueError(f"该阶不支持宽层: {s}")

    # 提取后缀: 优先双撇号, 再单撇号, 再 2/3
    if rest == "''":
        suffix = "''"
    elif rest == "'":
        suffix = "'"
    elif rest == "2":
        suffix = "2"
    elif rest == "3":
        suffix = "3"
    elif rest == "":
        suffix = ""
    else:
        raise ValueError(f"非法后缀: {rest!r}")

    count = parse_suffix(suffix)
    return (base, is_wide, count)


def normalize_move(move: Move) -> str:
    """Move 三元组 -> 标准字符串。

    宽层用大写+小写前缀约定: 基础 "R", 宽层 "Rw", 逆 "Rw'", 180 "Rw2"。
    """
    label, is_wide, count = move
    base = "x" if label == "x" else label
    if is_wide:
        s = base + "w"
    else:
        s = base
    return s + suffix_for_count(count)


def inverse_move(move: Move) -> Move:
    """单动作逆: (label, is_wide, (4-count)%4)。"""
    label, is_wide, count = move
    return (label, is_wide, (4 - count) % 4)


def parse_algorithm(text: str, allow_wide: bool = True) -> List[Move]:
    """将公式字符串解析为标准动作列表。

    支持空格、换行、制表符分隔。
    """
    moves = []
    for tok in text.split():
        tok = tok.strip()
        if not tok:
            continue
        moves.append(parse_move_str(tok, allow_wide=allow_wide))
    return moves


def inverse_algorithm(moves: List[Move]) -> List[Move]:
    """逆序并逐个取逆。"""
    return [inverse_move(m) for m in reversed(list(moves))]


def moves_to_str(moves: List[Move]) -> str:
    """动作列表 -> 字符串（空格分隔）。"""
    return " ".join(normalize_move(m) for m in moves)
