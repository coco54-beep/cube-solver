"""纯 numpy 的基础图像运算：缩放、双线性取样、凸包、最小外接矩形。

图像统一为 (H, W, 3) 的数组，索引 [y, x]。
"""

import math
from typing import List, Tuple

import numpy as np


def as_uint8_rgb(img) -> np.ndarray:
    """统一成 (H, W, 3) uint8。支持 RGBA 输入（丢弃 alpha）。"""
    arr = np.asarray(img)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError("expect image with 3 channels")
    arr = arr[:, :, :3]
    if arr.dtype != np.uint8:
        if arr.max() <= 1.5:
            arr = arr * 255.0
        arr = np.clip(np.round(arr), 0, 255).astype(np.uint8)
    return arr


def sample_points(img: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """在浮点坐标 (xs, ys) 处做双线性取样，返回与坐标同形状的像素值。"""
    h, w = img.shape[:2]
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    x = np.clip(x, 0, w - 1)
    y = np.clip(y, 0, h - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    x0 = np.clip(x0, 0, w - 1)
    y0 = np.clip(y0, 0, h - 1)
    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]
    Ia = img[y0, x0].astype(np.float64)
    Ib = img[y0, x1].astype(np.float64)
    Ic = img[y1, x0].astype(np.float64)
    Id = img[y1, x1].astype(np.float64)
    top = Ia * (1 - wx) + Ib * wx
    bot = Ic * (1 - wx) + Id * wx
    return top * (1 - wy) + bot * wy


def resize(img: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """双线性缩放到 (out_h, out_w)。"""
    h, w = img.shape[:2]
    out_w = max(1, int(out_w))
    out_h = max(1, int(out_h))
    if out_w == w and out_h == h:
        return img.copy()
    xs = (np.arange(out_w) + 0.5) * (w / out_w) - 0.5
    ys = (np.arange(out_h) + 0.5) * (h / out_h) - 0.5
    gx, gy = np.meshgrid(xs, ys)
    return sample_points(img, gx, gy)


def fit_max_dim(img: np.ndarray, max_dim: int) -> Tuple[np.ndarray, float]:
    """把最长边缩到 max_dim 以内，返回 (缩放后图像, 缩放系数)。"""
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_dim:
        return img, 1.0
    scale = max_dim / float(m)
    return resize(img, int(round(w * scale)), int(round(h * scale))), scale


def erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """4 连通二值腐蚀若干次（去掉零星噪点、细碎前景）。"""
    m = np.asarray(mask, dtype=bool)
    for _ in range(max(0, int(iterations))):
        p = np.pad(m, 1, mode="constant", constant_values=False)
        m = (p[1:-1, 1:-1] & p[1:-1, 0:-2] & p[1:-1, 2:] &
             p[0:-2, 1:-1] & p[2:, 1:-1])
    return m


def dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """8 连通二值膨胀若干次（用于把被黑框隔开的贴纸连成一整块）。"""
    m = np.asarray(mask, dtype=bool)
    for _ in range(max(0, int(iterations))):
        p = np.pad(m, 1, mode="constant", constant_values=False)
        m = (p[0:-2, 0:-2] | p[0:-2, 1:-1] | p[0:-2, 2:] |
             p[1:-1, 0:-2] | p[1:-1, 1:-1] | p[1:-1, 2:] |
             p[2:, 0:-2] | p[2:, 1:-1] | p[2:, 2:])
    return m


def component_masks(mask: np.ndarray, connect: int = 8, limit: int = 6):
    """按面积从大到小返回前 limit 个连通区域，跳过微小噪点。"""
    # Label horizontal runs instead of visiting every foreground pixel in Python.
    # Runs in adjacent rows overlap for 4-connectivity, or touch for 8-connectivity.
    mask = np.asarray(mask, dtype=bool)
    h, w = mask.shape
    parents, runs = [], []
    previous_starts = previous_ends = np.empty(0, dtype=int)
    previous_ids = []
    margin = 1 if connect == 8 else 0

    def root(label):
        while parents[label] != label:
            parents[label] = parents[parents[label]]
            label = parents[label]
        return label

    for y in range(h):
        changes = np.flatnonzero(np.diff(np.pad(mask[y].astype(np.int8), (1, 1))))
        starts, ends = changes[::2], changes[1::2]
        ids = []
        lower = np.searchsorted(previous_ends, starts-margin, side="right")
        upper = np.searchsorted(previous_starts, ends+margin, side="left")
        for start, end, lo, hi in zip(starts, ends, lower, upper):
            label = len(parents)
            parents.append(label)
            runs.append((y, int(start), int(end)))
            for prior in previous_ids[int(lo):int(hi)]:
                left, right = root(label), root(prior)
                if left != right:
                    parents[max(left, right)] = min(left, right)
            ids.append(label)
        previous_starts, previous_ends, previous_ids = starts, ends, ids
    groups = {}
    for label, (_, start, end) in enumerate(runs):
        group = groups.setdefault(root(label), [0, []])
        group[0] += end-start
        group[1].append(label)
    ranked = sorted(groups.values(), key=lambda group: group[0], reverse=True)
    for area, labels in ranked[:limit]:
        if area < 20:
            continue
        out = np.zeros((h, w), dtype=bool)
        for label in labels:
            y, start, end = runs[label]
            out[y, start:end] = True
        yield out


def largest_component_mask(mask: np.ndarray, connect: int = 8) -> np.ndarray:
    """返回最大连通区域，空图返回空掩膜。"""
    return next(component_masks(mask, connect, 1), np.zeros_like(mask, dtype=bool))


def project_quad(quad, u, v):
    """把单位正方形内的位置投影到 TL/TR/BR/BL 四角，供采样和取景网格共用。"""
    q = np.asarray(quad, dtype=float)
    if q.shape != (4, 2) or not np.isfinite(q).all():
        raise ValueError("invalid corners")
    edges = np.roll(q, -1, axis=0) - q
    turns = edges[:, 0] * np.roll(edges[:, 1], -1) - edges[:, 1] * np.roll(edges[:, 0], -1)
    if not np.all(turns > 1e-10):
        raise ValueError("invalid corners")
    rows, values = [], []
    for (cu, cv), (x, y) in zip(((0, 0), (1, 0), (1, 1), (0, 1)), q):
        rows.extend(((cu, cv, 1, 0, 0, 0, -x*cu, -x*cv),
                     (0, 0, 0, cu, cv, 1, -y*cu, -y*cv)))
        values.extend((x, y))
    matrix = np.append(np.linalg.solve(rows, values), 1).reshape(3, 3)
    u, v = np.asarray(u), np.asarray(v)
    den = matrix[2, 0]*u + matrix[2, 1]*v + 1
    if np.any(np.abs(den) < 1e-8):
        raise ValueError("invalid corners")
    x = (matrix[0, 0]*u + matrix[0, 1]*v + matrix[0, 2]) / den
    y = (matrix[1, 0]*u + matrix[1, 1]*v + matrix[1, 2]) / den
    return x, y


def warp_quad(img: np.ndarray, quad, side: int) -> np.ndarray:
    """把四角透视校正成正方形；输入/输出均从左上角计行。"""
    u, v = np.meshgrid(np.linspace(0, 1, side), np.linspace(0, 1, side))
    x, y = project_quad(quad, u, v)
    return np.clip(sample_points(img, x, y), 0, 255).astype(np.uint8)


def row_extrema_points(xs, ys):
    """Exact hull input for row-ordered nonzero pixels, at most two per row."""
    if not len(xs):
        return np.empty((0, 2), dtype=float)
    starts = np.r_[0, np.flatnonzero(np.diff(ys))+1]
    ends = np.r_[starts[1:]-1, len(xs)-1]
    indices = np.unique(np.concatenate((starts, ends)))
    return np.column_stack((xs[indices], ys[indices])).astype(float)


def convex_hull(points: np.ndarray) -> np.ndarray:
    """Andrew 单调链凸包。points: (N,2)，返回凸包顶点 (M,2)。"""
    pts = np.asarray(points, dtype=np.float64)
    if pts.shape[0] <= 2:
        return pts
    order = np.lexsort((pts[:, 1], pts[:, 0]))
    pts = pts[order]
    # 去重
    keep = np.ones(len(pts), dtype=bool)
    keep[1:] = np.any(np.diff(pts, axis=0) != 0, axis=1)
    pts = pts[keep]
    if pts.shape[0] <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: List[np.ndarray] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: List[np.ndarray] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1], dtype=np.float64)


def min_area_rect(points: np.ndarray) -> dict:
    """旋转卡壳求最小面积外接矩形。

    返回 dict:
        center: (cx, cy)
        axes:   (ex, ey) 两个单位方向（先"宽"后"高"）
        size:   (w, h) 沿两个方向的长度
        corners:(4,2) 顺序为 从 center-ex-ey 起逆时针
        angle:  宽度方向相对 x 轴的角度（弧度）
    """
    pts = np.asarray(points, dtype=np.float64)
    hull = convex_hull(pts)
    if hull.shape[0] == 0:
        raise ValueError("empty point set")

    best = None
    m = hull.shape[0]
    for i in range(m):
        p1 = hull[i]
        p2 = hull[(i + 1) % m]
        edge = p2 - p1
        norm = math.hypot(edge[0], edge[1])
        if norm < 1e-9:
            continue
        ux = edge / norm
        uy = np.array([-ux[1], ux[0]])
        px = hull @ ux
        py = hull @ uy
        w_ = px.max() - px.min()
        h_ = py.max() - py.min()
        area = w_ * h_
        if best is None or area < best[0]:
            best = (area, ux, uy, px.min(), px.max(), py.min(), py.max())

    if best is None:
        raise ValueError("degenerate point set")
    _area, ux, uy, x0, x1, y0, y1 = best
    w_ = x1 - x0
    h_ = y1 - y0
    c_local = np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0])
    # 局部坐标 (a,b) 满足 p = a*ux + b*uy；故 center = cx*ux + cy*uy
    center = c_local[0] * ux + c_local[1] * uy
    corners = np.array([
        (x0 * ux[0] + y0 * uy[0], x0 * ux[1] + y0 * uy[1]),
        (x1 * ux[0] + y0 * uy[0], x1 * ux[1] + y0 * uy[1]),
        (x1 * ux[0] + y1 * uy[0], x1 * ux[1] + y1 * uy[1]),
        (x0 * ux[0] + y1 * uy[0], x0 * ux[1] + y1 * uy[1]),
    ])
    return {
        "center": (float(center[0]), float(center[1])),
        "axes": (ux.copy(), uy.copy()),
        "size": (float(w_), float(h_)),
        "corners": corners,
        "angle": float(math.atan2(ux[1], ux[0])),
    }
