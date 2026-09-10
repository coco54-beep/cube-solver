"""打乱公式解析：把用户粘贴的打乱字符串转成可应用的动作列表。

支持常见写法：空格/逗号/换行分隔；`Rw`/`3Rw` 宽层记号（转成内部小写宽层写法）；
`M/E/S` 中央切片；可忽略整体转动 `x/y/z`。

用法::

    moves, skipped = text_to_moves("R U R' U'", n=3)
    cube = Cube3.solved()
    cube.apply_moves(moves)
"""

import re
import random
from typing import List, Tuple

from cube.notation import parse_move_full

_WIDE_RE = re.compile(r"^(\d+)?([RLUDFB])w(''|'|2|3)?$")
_SEP_RE = re.compile(r"[,，、;；\s]+")
_PREFIX_RE = re.compile(r"^\s*(?:scramble|打乱|スクランブル)\s*[:：]\s*", re.IGNORECASE)
_WHOLE = set("xyz")
_SLICE = set("MES")

# 随机打乱
_FACES = ("U", "D", "F", "B", "R", "L")
_AXIS = {"U": "y", "D": "y", "F": "z", "B": "z", "R": "x", "L": "x"}
_SUFFIX = ("", "'", "2")
# 每阶步数区间：阶数越大需要的步数越多，否则中心/内层搅不动。
_LENGTH = {2: (9, 11), 3: (20, 25), 4: (40, 45), 5: (60, 70)}


def _layers_for(n: int) -> Tuple[int, ...]:
    if n <= 3:
        return (1,)
    if n == 4:
        return (1, 2)
    return (1, 2, 3)


def _token(face: str, layers: int, suffix: str) -> str:
    """按内部记号生成 token（层数 2 用小写宽层，3+ 用数字前缀）。"""
    if layers == 1:
        return face + suffix
    if layers == 2:
        return face.lower() + suffix
    return f"{layers}{face}{suffix}"


def random_scramble(n: int, rng=None) -> List[str]:
    """生成一个较彻底的随机打乱（避免相邻同轴，减少自抵消）。

    返回 apply_move 可直接应用的动作字符串列表。``rng`` 可传入
    ``random.Random(seed)`` 以获得确定性结果。
    """
    rng = rng or random
    lo, hi = _LENGTH.get(n, (20, 25))
    layer_choices = _layers_for(n)
    moves: List[str] = []
    prev_axis = None
    for _ in range(rng.randint(lo, hi)):
        while True:
            face = rng.choice(_FACES)
            if _AXIS[face] != prev_axis:
                break
        prev_axis = _AXIS[face]
        layers = rng.choice(layer_choices)
        moves.append(_token(face, layers, rng.choice(_SUFFIX)))
    return moves


def _strip_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text or "")


def _normalize_wide(tok: str) -> str:
    """`Rw`/`3Rw'` -> `r`/`3r'`（内部用小写表示宽层）。"""
    m = _WIDE_RE.match(tok)
    if not m:
        return tok
    digits, face, suffix = m.groups()
    return (digits or "") + face.lower() + (suffix or "")


def _is_wide(tok: str) -> bool:
    """判断 token 是否为宽层转动（小写面或 Rw 记号）。"""
    if _WIDE_RE.match(tok):
        return True
    try:
        _, layers, _ = parse_move_full(tok)
    except ValueError:
        return False
    return layers > 1


def text_to_moves(text: str, n: int = 3,
                  skip_rotations: bool = True) -> Tuple[List[str], int]:
    """解析打乱字符串。

    返回 ``(moves, skipped_rotations)``。无法识别或该阶不支持的动作抛 ValueError，
    错误信息里带出问题 token，便于 UI 提示。
    """
    tokens = [t for t in _SEP_RE.split(_strip_prefix(text)) if t]
    moves: List[str] = []
    skipped = 0
    for tok in tokens:
        if tok[0] in _WHOLE:
            if skip_rotations:
                skipped += 1
                continue
            raise ValueError(tok)
        if tok[0] in _SLICE:
            try:
                from cube.middle_slice import slice_turns
                slice_turns(tok)
            except Exception:
                raise ValueError(tok)
            moves.append(tok)
            continue
        norm = _normalize_wide(tok)
        if n == 2 and _is_wide(norm):
            raise ValueError(tok)
        try:
            parse_move_full(norm)  # 触发合法性校验
        except ValueError:
            raise ValueError(tok)
        moves.append(norm)
    return moves, skipped
