"""合法性校验。

3x3 校验（经典充要条件，基于面贴颜色，不依赖 home）：
    1. 结构: 6面 x 9格，均为合法颜色。
    2. 每种颜色恰好出现 9 次。
    3. 6 个中心块颜色互不相同。
    4. 8 个角块位置的颜色三元组多重集 == 8 个角槽（由中心决定）多重集。
    5. 12 个棱块位置的颜色二元组多重集 == 12 个棱槽多重集。
    6. 角块扭转总和 ≡ 0 (mod 3)。
    7. 棱块翻转总和 ≡ 0 (mod 2)。
    8. 置换奇偶: (角置换) + (棱置换) ≡ 0 (mod 2)。

4x4 校验（结构性检查）：
    1. 结构: 6面 x 16格，均为合法颜色。
    2. 每种颜色恰好出现 16 次。
    3. 24 个中心块（单色），每种颜色恰好 4 个。
    4. 8 个角块（三色）。
    5. 24 个棱翼（双色）。
"""

from collections import Counter
from typing import Dict, List, Tuple

from cube.colors import DEFAULT_COLORS, is_valid_color, VALID_COLORS
from cube.coordinates import (
    FACE_NORMALS,
    coord_values,
    get_d_maxc,
    rc_from_pos,
)

# (axis, sign) -> face
AXIS_SIGN_TO_FACE = {
    (0, +1): "R",
    (0, -1): "L",
    (1, +1): "U",
    (1, -1): "D",
    (2, +1): "F",
    (2, -1): "B",
}

# 全局颜色排序（用于棱块翻转约定的确定性比较）已弃用：翻转约定改为与
# hkociemba 的 edgeFacelet 一致（见 _edge_flip）。


def _faces_at(pos: Tuple[int, int, int], n: int) -> List[str]:
    """返回 pos 处可见的面列表（按轴排序）。"""
    d, maxc = get_d_maxc(n)
    faces = []
    for axis in (0, 1, 2):
        v = pos[axis]
        if v == maxc:
            faces.append(AXIS_SIGN_TO_FACE[(axis, +1)])
        elif v == -maxc:
            faces.append(AXIS_SIGN_TO_FACE[(axis, -1)])
    return faces


def _face_color_at(facelets: Dict[str, List[List[str]]], face: str, pos, n: int) -> str:
    r, c = rc_from_pos(n, face, pos)
    return facelets[face][r][c]


def _extract_pieces(facelets: Dict[str, List[List[str]]], n: int):
    """从 facelet 提取所有块的 (pos, [colors]) 与中心色。

    返回:
        centers: dict[face -> center_color]
        corners: list[(pos, [3 colors])]
        edges:   list[(pos, [2 colors])]
        centers_blocks: list[(pos, [1 color])]
    """
    d, maxc = get_d_maxc(n)
    vals = coord_values(n)

    center_of = {}
    for face in ("U", "D", "F", "B", "R", "L"):
        m = n // 2
        center_of[face] = facelets[face][m][m]

    corners = []
    edges = []
    centers_blocks = []
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                faces = _faces_at(pos, n)
                if len(faces) == 3:
                    colors = [_face_color_at(facelets, f, pos, n) for f in faces]
                    corners.append((pos, colors))
                elif len(faces) == 2:
                    colors = [_face_color_at(facelets, f, pos, n) for f in faces]
                    edges.append((pos, colors))
                elif len(faces) == 1:
                    color = _face_color_at(facelets, faces[0], pos, n)
                    centers_blocks.append((pos, [color]))
    return center_of, corners, edges, centers_blocks


def _corner_twist(pos: Tuple[int, int, int], ud_color: str, colors: List[str]) -> int:
    """角块扭转 (mod 3)。

    ud_color 是该角块的 U/D 颜色。colors 对应该位置 3 个面（按轴排序）的颜色。
    """
    # 3 个 sticker 方向: ex, ey, ez
    sx = 1 if pos[0] > 0 else -1
    sy = 1 if pos[1] > 0 else -1
    sz = 1 if pos[2] > 0 else -1
    ex = (sx, 0, 0)
    ey = (0, sy, 0)
    ez = (0, 0, sz)

    det = sx * sy * sz
    # CCW 顺序（从外观察）:
    #   det=+1: (ex, ey, ez)   -> i(ey)=1
    #   det=-1: (ex, ez, ey)   -> i(ey)=2
    if det > 0:
        ccw = [ex, ey, ez]
    else:
        ccw = [ex, ez, ey]

    # UD sticker 的方向: colors[i] 在 faces[i]，faces 按轴排序 [x,y,z]
    # colors 来自 _faces_at 的顺序: axis0, axis1, axis2 -> 方向 ex, ey, ez
    ud_idx = colors.index(ud_color)
    dir_ud = [ex, ey, ez][ud_idx]
    i_ud = ccw.index(dir_ud)
    i_ey = ccw.index(ey)
    return (i_ud - i_ey) % 3


# 棱块位置的 (第一面, 第二面)，与 hkociemba 的 edgeFacelet/edgeColor 约定一致：
#   翻转 = 0 当且仅当该棱当前贴在第一面上的颜色 == 其 home 槽的第一面颜色。
# 12 个棱位（3x3 离散坐标）：
_EDGE_FACES = {
    (1, 1, 0): ("U", "R"), (0, 1, 1): ("U", "F"), (-1, 1, 0): ("U", "L"), (0, 1, -1): ("U", "B"),
    (1, -1, 0): ("D", "R"), (0, -1, 1): ("D", "F"), (-1, -1, 0): ("D", "L"), (0, -1, -1): ("D", "B"),
    (1, 0, 1): ("F", "R"), (-1, 0, 1): ("F", "L"), (-1, 0, -1): ("B", "L"), (1, 0, -1): ("B", "R"),
}


def _edge_flip(pos: Tuple[int, int, int], colors: List[str],
               home_face_by_color: Dict[str, str]) -> int:
    """棱块翻转 (mod 2)，与 hkociemba 的 edgeFacelet 约定一致。

    约定：对棱位 pos，edgeFacelet 定义的"第一面" f1 上的颜色必须等于该棱
    home 槽第一面（由两个颜色所属面确定）的颜色，否则视为翻转。
    """
    f1, _f2 = _EDGE_FACES[pos]
    # 当前位置 2 个方向（按轴 0=X,1=Y,2=Z 排序），colors 同序对应
    dirs = []
    for axis in (0, 1, 2):
        if pos[axis] != 0:
            d = [0, 0, 0]
            d[axis] = 1 if pos[axis] > 0 else -1
            dirs.append(tuple(d))
    n1 = FACE_NORMALS[f1]
    col_at_f1 = colors[dirs.index(n1)]
    # 该棱的 home 槽：两个颜色所属面确定的棱位
    hf1 = home_face_by_color[colors[0]]
    hf2 = home_face_by_color[colors[1]]
    home_first_face = None
    for _pos, (_a, _b) in _EDGE_FACES.items():
        if {hf1, hf2} == {_a, _b}:
            home_first_face = _a
            break
    if home_first_face is None:
        return 0  # 颜色组合异常（前面的多重集检查会报错）
    home_first_color = colors[0] if hf1 == home_first_face else colors[1]
    return 0 if col_at_f1 == home_first_color else 1


def validate_3x3(facelets: Dict[str, List[List[str]]]) -> List[str]:
    """校验 3x3 facelet 是否可达。返回错误列表（空=合法）。"""
    errors: List[str] = []

    # 1. 结构
    n = 3
    for face in ("U", "D", "F", "B", "R", "L"):
        if face not in facelets:
            errors.append(f"缺少面 {face}")
            continue
        grid = facelets[face]
        if len(grid) != 3:
            errors.append(f"面 {face} 行数错误")
            continue
        for row in grid:
            if len(row) != 3:
                errors.append(f"面 {face} 存在非3列行")
                break
        for row in grid:
            for cell in row:
                if not is_valid_color(cell):
                    errors.append(f"面 {face} 存在非法颜色 {cell}")
                    break

    if errors:
        return errors

    # 2. 颜色计数: 每种恰好 9 次
    total = Counter()
    for face in facelets:
        for row in facelets[face]:
            for cell in row:
                total[cell] += 1
    for c in VALID_COLORS:
        if total[c] != 9:
            errors.append(f"颜色 {c} 出现 {total[c]} 次（应为9）")

    if errors:
        return errors

    # 3. 中心块互异
    center_of, corners, edges, centers_blocks = _extract_pieces(facelets, n)
    center_colors = list(center_of.values())
    if len(set(center_colors)) != 6:
        errors.append("6个中心块颜色必须互不相同")
        return errors

    # color -> face（中心色唯一，故映射确定）
    face_by_color = {col: f for f, col in center_of.items()}

    # 4/5. 角/棱槽多重集
    # 角槽: 每个角位置的 3 个面中心色
    corner_slots = []
    for pos, _ in corners:
        faces = _faces_at(pos, n)
        slot = tuple(sorted([center_of[f] for f in faces]))
        corner_slots.append(slot)
    piece_corner_triples = []
    for pos, colors in corners:
        piece_corner_triples.append(tuple(sorted(colors)))
    if sorted(corner_slots) != sorted(piece_corner_triples):
        errors.append("角块颜色组合与槽位不匹配")

    edge_slots = []
    for pos, _ in edges:
        faces = _faces_at(pos, n)
        slot = tuple(sorted([center_of[f] for f in faces]))
        edge_slots.append(slot)
    piece_edge_pairs = []
    for pos, colors in edges:
        piece_edge_pairs.append(tuple(sorted(colors)))
    if sorted(edge_slots) != sorted(piece_edge_pairs):
        errors.append("棱块颜色组合与槽位不匹配")

    if errors:
        return errors

    # 6. 角块扭转
    twist_sum = 0
    for pos, colors in corners:
        ud = None
        for c in colors:
            if face_by_color.get(c) in ("U", "D"):
                ud = c
                break
        if ud is None:
            # 理论上不可能（中心色已覆盖）
            continue
        twist_sum += _corner_twist(pos, ud, colors)
    if twist_sum % 3 != 0:
        errors.append(f"角块扭转和 {twist_sum} 不≡0 (mod 3)")

    # 7. 棱块翻转
    flip_sum = 0
    for pos, colors in edges:
        flip_sum += _edge_flip(pos, colors, face_by_color)
    if flip_sum % 2 != 0:
        errors.append(f"棱块翻转和 {flip_sum} 不≡0 (mod 2)")

    # 8. 置换奇偶
    def perm_parity(pieces):
        # pieces: list[(pos, colors)]; 计算 pos -> home 的置换符号
        # home = 唯一槽（按颜色多重集匹配）
        slots = {}
        for pos, _ in pieces:
            faces = _faces_at(pos, n)
            slot = tuple(sorted([center_of[f] for f in faces]))
            slots[pos] = slot
        # 为每个 piece 找 home slot
        slot_to_pos = {}
        for pos, sl in slots.items():
            slot_to_pos[sl] = pos
        # 置换: piece 在 pos, home 是 slot_to_pos[sorted(piece colors)]
        perm = []
        for pos, colors in pieces:
            key = tuple(sorted(colors))
            home = slot_to_pos[key]
            perm.append((pos, home))
        # 计算符号
        # 把 pos/home 映射为索引
        all_positions = [p for p, _ in pieces]
        idx = {p: i for i, p in enumerate(all_positions)}
        m = len(all_positions)
        sigma = [None] * m
        for pos, home in perm:
            sigma[idx[pos]] = idx[home]
        # 符号 = (-1)^(m - cycles)
        visited = [False] * m
        cycles = 0
        for i in range(m):
            if not visited[i]:
                cycles += 1
                j = i
                while not visited[j]:
                    visited[j] = True
                    j = sigma[j]
        return (m - cycles) % 2

    corner_par = perm_parity(corners)
    edge_par = perm_parity(edges)
    if (corner_par + edge_par) % 2 != 0:
        errors.append("置换奇偶性错误（角+棱置换必须为偶）")

    return errors


def validate_2x2(facelets: Dict[str, List[List[str]]]) -> List[str]:
    """校验 2x2 facelet 是否可达。返回错误列表（空=合法）。

    2 阶无棱块、无中心块，只有 8 个角块。可达性条件（2x2 的置换奇偶不受限，
    单次面转即产生奇置换，故无角块置换奇偶约束）：
        1. 结构: 6面 x 4格，均为合法颜色。
        2. 每种颜色恰好出现 4 次（8角 x 3色 / 6色）。
        3. 8 个角块的三色多重集 == 8 个角槽多重集（由命名面默认色确定）。
        4. 角块扭转总和 ≡ 0 (mod 3)。
    """
    errors: List[str] = []
    n = 2

    # 1. 结构
    for face in ("U", "D", "F", "B", "R", "L"):
        if face not in facelets:
            errors.append(f"缺少面 {face}")
            continue
        grid = facelets[face]
        if len(grid) != 2:
            errors.append(f"面 {face} 行数错误")
            continue
        for row in grid:
            if len(row) != 2:
                errors.append(f"面 {face} 存在非2列行")
                break
        for row in grid:
            for cell in row:
                if not is_valid_color(cell):
                    errors.append(f"面 {face} 存在非法颜色 {cell}")
                    break

    if errors:
        return errors

    # 2. 每种颜色恰好 4 次
    total = Counter()
    for face in facelets:
        for row in facelets[face]:
            for cell in row:
                total[cell] += 1
    for c in VALID_COLORS:
        if total[c] != 4:
            errors.append(f"颜色 {c} 出现 {total[c]} 次（应为4）")

    if errors:
        return errors

    # 3/4/5. 角块检查
    center_of, corners, edges, centers_blocks = _extract_pieces(facelets, n)
    if edges:
        errors.append("2x2 不应存在棱块")
    if centers_blocks:
        errors.append("2x2 不应存在中心块")
    if len(corners) != 8:
        errors.append(f"角块数 {len(corners)} 应为8")

    if errors:
        return errors

    # 3. 角槽三重集匹配：用命名面 -> 默认颜色确定每个槽位的三色
    corner_slots = []
    for pos, _ in corners:
        faces = _faces_at(pos, n)
        slot = tuple(sorted(DEFAULT_COLORS[f] for f in faces))
        corner_slots.append(slot)
    piece_corner_triples = []
    for pos, colors in corners:
        piece_corner_triples.append(tuple(sorted(colors)))
    if sorted(corner_slots) != sorted(piece_corner_triples):
        errors.append("角块颜色组合与槽位不匹配")
        return errors

    # 4. 角块扭转（用命名面 U/D 作为 ud 轴）
    twist_sum = 0
    for pos, colors in corners:
        # colors 按轴序 [x,y,z]，y 轴面为 U 或 D
        ud = colors[1]  # y 轴面颜色，必须是 U 或 D 之一
        twist_sum += _corner_twist(pos, ud, colors)
    if twist_sum % 3 != 0:
        errors.append(f"角块扭转和 {twist_sum} 不≡0 (mod 3)")

    return errors


def validate_4x4(facelets: Dict[str, List[List[str]]]) -> List[str]:
    """校验 4x4 facelet 结构性合法性。返回错误列表（空=合法）。"""
    errors: List[str] = []
    n = 4

    # 1. 结构
    for face in ("U", "D", "F", "B", "R", "L"):
        if face not in facelets:
            errors.append(f"缺少面 {face}")
            continue
        grid = facelets[face]
        if len(grid) != 4:
            errors.append(f"面 {face} 行数错误")
            continue
        for row in grid:
            if len(row) != 4:
                errors.append(f"面 {face} 存在非4列行")
                break
        for row in grid:
            for cell in row:
                if not is_valid_color(cell):
                    errors.append(f"面 {face} 存在非法颜色 {cell}")
                    break

    if errors:
        return errors

    # 2. 每种颜色恰好 16 次
    total = Counter()
    for face in facelets:
        for row in facelets[face]:
            for cell in row:
                total[cell] += 1
    for c in VALID_COLORS:
        if total[c] != 16:
            errors.append(f"颜色 {c} 出现 {total[c]} 次（应为16）")

    if errors:
        return errors

    # 3. 中心块: 24 个单色块，每色恰好 4 个
    # 4. 角块 8 个三色, 棱翼 24 个双色
    d, maxc = get_d_maxc(n)
    vals = coord_values(n)
    corner_count = 0
    edge_count = 0
    center_colors = Counter()
    for x in vals:
        for y in vals:
            for z in vals:
                pos = (x, y, z)
                faces = _faces_at(pos, n)
                k = len(faces)
                if k == 3:
                    corner_count += 1
                elif k == 2:
                    edge_count += 1
                elif k == 1:
                    for f in faces:
                        r, c = rc_from_pos(n, f, pos)
                        center_colors[facelets[f][r][c]] += 1

    if corner_count != 8:
        errors.append(f"角块数 {corner_count} 应为8")
    if edge_count != 24:
        errors.append(f"棱翼数 {edge_count} 应为24")
    for c in VALID_COLORS:
        if center_colors[c] != 4:
            errors.append(f"中心色 {c} 出现 {center_colors[c]} 次（应为4）")

    return errors
