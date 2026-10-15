"""把逐面识别结果拼装成应用的 facelets 结构。

facelets: Dict[face, grid]，grid[r][c] 为颜色编码，行 0 在面内"上方"。
每张照片的方向由用户在预览里旋转校正；本模块提供旋转与拼装工具，
以及奇数阶按中心色自动分配面名的便捷函数。
"""

from typing import Dict, List, Optional

from cube.colors import DEFAULT_COLORS, VALID_COLORS

# 应用使用的六个面与默认配色
FACES = ("U", "D", "F", "B", "R", "L")
CAPTURE_ORDER = ("F", "R", "U", "B", "L", "D")

# 颜色 -> 面（默认配色逆映射）
COLOR_TO_FACE = {c: f for f, c in DEFAULT_COLORS.items()}


def rotate_grid(grid: List[List[str]], quarter_turns: int) -> List[List[str]]:
    """顺时针旋转 90° × k（k 可负，取模 4）。"""
    k = int(quarter_turns) % 4
    out = [list(row) for row in grid]
    for _ in range(k):
        n = len(out)
        out = [[out[n - 1 - c][r] for c in range(n)] for r in range(n)]
    return out


def empty_grid(n: int) -> List[List[str]]:
    return [[""] * n for _ in range(n)]


def orient_grid(grid, orientation, to_face=True):
    """在照片行列与魔方固定面的行列之间转换，跟随导航的整体翻转。"""
    from cube.coordinates import get_d_maxc, pos_from_rc
    n = len(grid)
    if n < 2:
        return [list(row) for row in grid]
    d, maxc = get_d_maxc(n)
    out = empty_grid(n)
    for r in range(n):
        for c in range(n):
            x, y, _ = orientation.world.transform(*pos_from_rc(n, orientation.current_face(), r, c))
            sr, sc = round((maxc-y)/d), round((maxc+x)/d)
            if to_face:
                out[r][c] = grid[sr][sc]
            else:
                out[sr][sc] = grid[r][c]
    return out


def assemble_facelets(face_grids: Dict[str, List[List[str]]], n: int) -> Dict[str, List[List[str]]]:
    """按面拼装 facelets；缺失面用空网格占位。"""
    out: Dict[str, List[List[str]]] = {}
    for face in FACES:
        grid = face_grids.get(face)
        if grid is None:
            out[face] = empty_grid(n)
        else:
            out[face] = [[grid[r][c] for c in range(n)] for r in range(n)]
    return out


def center_color(grid: List[List[str]]) -> Optional[str]:
    n = len(grid)
    if n == 0 or n % 2 == 0:
        return None
    m = n // 2
    return grid[m][m] or None


def label_by_center(face_grids: List[List[List[str]]], n: int) -> Optional[Dict[str, List[List[str]]]]:
    """奇数阶：按每个面中心色分配面名（默认配色）。

    输入为若干已识别的网格（顺序任意）。若中心色正好是六种且互不重复，
    返回 {face: grid}；否则返回 None（需用户手动分配）。
    """
    if n % 2 == 0:
        return None
    assigned: Dict[str, List[List[str]]] = {}
    for grid in face_grids:
        col = center_color(grid)
        face = COLOR_TO_FACE.get(col) if col else None
        if face is None or face in assigned:
            return None
        assigned[face] = grid
    if set(assigned.keys()) != set(FACES):
        return None
    return assigned


def color_counts(facelets: Dict[str, List[List[str]]]) -> Dict[str, int]:
    counts = {c: 0 for c in VALID_COLORS}
    for grid in facelets.values():
        for row in grid:
            for cell in row:
                if cell in counts:
                    counts[cell] += 1
    return counts


def missing_faces(face_grids: Dict[str, List[List[str]]]) -> List[str]:
    return [f for f in FACES if not face_grids.get(f)]
