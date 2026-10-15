"""从单张照片识别一个魔方面的 n×n 贴纸颜色（纯 numpy）。

思路（面向「逐面拍照」：一次只拍一个正对相机的面）：
    1. 缩放到工作尺寸。
    2. 用 HSV 找"贴纸像素"（彩色或白色）作为前景。
    3. 逐步桥接贴纸切缝，分别评估候选区域，避免并入背景控件。
    4. 检查双向网格分隔线，并把四角透视校正为正方形。
    5. 在 n×n 网格中心逐像素投票，不能确认的颜色保留为空。
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from vision import imageops
from vision.colors import COLOR_CODES, classify_hsv, rgb_to_hsv
from vision.params import DEFAULT as _P, VisionParams


@dataclass
class FaceDetection:
    n: int
    cells: List[List[Optional[str]]]      # n×n，None 表示该格无法判定
    ok: bool
    reason: str = ""
    rect: Optional[dict] = None
    confidence: float = 0.0
    image_quad: Optional[list] = None

    def grid(self) -> List[List[str]]:
        """未确认的格子保留为空，供用户校正。"""
        return [[c or "" for c in row] for row in self.cells]

    def dominant_color(self) -> Optional[str]:
        counts = {c: 0 for c in COLOR_CODES}
        for row in self.cells:
            for c in row:
                if c:
                    counts[c] += 1
        best = max(counts, key=counts.get)
        return best if counts[best] else None


def _foreground_mask(hsv_h, hsv_s, hsv_v, params: VisionParams) -> np.ndarray:
    black = hsv_v < params.val_min
    color = (hsv_s >= params.sat_color) & (hsv_v >= params.val_min)
    white = (hsv_s <= params.sat_white) & (hsv_v >= params.val_white)
    return (~black) & (color | white)


def _cell_color(hs, ss, vs, params: VisionParams) -> Optional[str]:
    """逐像素投票，避免红色色相跨越 0/179 时被中位数误判。"""
    votes = [classify_hsv(int(h), int(s), int(v), params)
             for h, s, v in zip(hs.flat, ss.flat, vs.flat)]
    valid = [v for v in votes if v]
    if len(valid) < max(params.min_cell_confident, len(votes) * .4):
        return None
    winner = max(COLOR_CODES, key=valid.count)
    return winner if valid.count(winner) / len(valid) >= .7 else None


def _axis_bands(mask: np.ndarray, rect: dict, axis: int, n: int,
                params: VisionParams) -> Optional[List[float]]:
    """沿某个轴找 n 条贴纸条带中心（局部坐标，相对矩形中心）。

    黑框在投影上是低前景区，据此定位条带，抵消"黑框较粗导致均匀网格
    内缩"的误差。找不到正好 n 条时返回 None，交由均匀网格兜底。
    """
    cx, cy = rect["center"]
    ux, uy = rect["axes"]
    w_, h_ = rect["size"]
    length = w_ if axis == 0 else h_
    other = h_ if axis == 0 else w_
    m = int(mask.shape[0])
    ww = int(mask.shape[1])

    steps = max(80, int(length))
    a = np.linspace(-length / 2.0, length / 2.0, steps)
    cross = np.linspace(-other * 0.3, other * 0.3, 9)
    A, B = np.meshgrid(a, cross)
    if axis == 0:
        xs = cx + A * ux[0] + B * uy[0]
        ys = cy + A * ux[1] + B * uy[1]
    else:
        xs = cx + B * ux[0] + A * uy[0]
        ys = cy + B * ux[1] + A * uy[1]
    xi = np.clip(np.round(xs).astype(np.int64), 0, ww - 1)
    yi = np.clip(np.round(ys).astype(np.int64), 0, m - 1)
    prof = mask[yi, xi].mean(axis=0)

    on = prof >= 0.5
    bands = []
    i = 0
    while i < steps:
        if on[i]:
            j = i
            while j < steps and on[j]:
                j += 1
            bands.append([i, j - 1])
            i = j
        else:
            i += 1
    # 合并被细小噪点切开的条带
    gap_min = int(length / n * 0.18)
    merged = []
    for b in bands:
        if merged and (b[0] - merged[-1][1]) <= gap_min:
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    min_len = length / n * 0.3
    merged = [b for b in merged if (b[1] - b[0]) >= min_len]
    if len(merged) != n:
        return None
    return [float((a[s] + a[e]) / 2.0) for s, e in merged]


def _sample_grid(hsv, mask, rect: dict, n: int, params: VisionParams):
    cx, cy = rect["center"]
    ux, uy = rect["axes"]
    w_, h_ = rect["size"]
    H, S, V = hsv

    cols = _axis_bands(mask, rect, 0, n, params)
    rows = _axis_bands(mask, rect, 1, n, params)
    if cols is None:
        cols = [((c + 0.5) / n - 0.5) * w_ for c in range(n)]
        col_step = w_ / n
    else:
        col_step = (cols[-1] - cols[0]) / max(1, n - 1)
    if rows is None:
        rows = [((r + 0.5) / n - 0.5) * h_ for r in range(n)]
        row_step = h_ / n
    else:
        row_step = (rows[-1] - rows[0]) / max(1, n - 1)

    steps = 5
    offs = np.linspace(-0.5, 0.5, steps) * params.cell_inset
    half_a = col_step * 0.5
    half_b = row_step * 0.5
    cells: List[List[Optional[str]]] = []
    for r in range(n):
        row = []
        for c in range(n):
            xs = np.array([cx + (cols[c] + da * half_a) * ux[0]
                           + (rows[r] + db * half_b) * uy[0]
                           for da in offs for db in offs])
            ys = np.array([cy + (cols[c] + da * half_a) * ux[1]
                           + (rows[r] + db * half_b) * uy[1]
                           for da in offs for db in offs])
            xi = np.clip(np.round(xs).astype(np.int64), 0, H.shape[1] - 1)
            yi = np.clip(np.round(ys).astype(np.int64), 0, H.shape[0] - 1)
            row.append(_cell_color(H[yi, xi], S[yi, xi], V[yi, xi], params))
        cells.append(row)
    return cells


def _canonical_rect(rect):
    # 宽轴始终指向右侧，高轴指向下侧，避免凸包起点改变照片行列顺序。
    angle = (rect["angle"] + np.pi / 4) % (np.pi / 2) - np.pi / 4
    ux = np.array([np.cos(angle), np.sin(angle)])
    uy = np.array([-ux[1], ux[0]])
    points = np.asarray(rect["corners"])
    px, py = points @ ux, points @ uy
    center = np.asarray(rect["center"])
    w, h = px.max() - px.min(), py.max() - py.min()
    corners = np.array([center - ux*w/2 - uy*h/2,
                        center + ux*w/2 - uy*h/2,
                        center + ux*w/2 + uy*h/2,
                        center - ux*w/2 + uy*h/2])
    return dict(center=tuple(center), axes=(ux, uy), size=(w, h),
                corners=corners, angle=float(angle))


def _candidate_quad(points, rect):
    hull = imageops.convex_hull(points)
    # 去掉圆角/采样造成的小边，保留面外轮廓四角。
    while len(hull) > 4:
        prev = np.roll(hull, 1, axis=0) - hull
        nxt = np.roll(hull, -1, axis=0) - hull
        areas = np.abs(prev[:, 0]*nxt[:, 1] - prev[:, 1]*nxt[:, 0])
        hull = np.delete(hull, np.argmin(areas), axis=0)
    if len(hull) != 4:
        return rect["corners"]
    ref = rect["corners"]
    hull = np.roll(hull, -np.argmin(np.sum((hull-ref[0])**2, axis=1)), axis=0)
    return hull


def _grid_evidence(rgb, n):
    # 一块大色板同样能填满 n×n 采样点，必须同时找到横向和纵向分隔线。
    h, w = rgb.shape[:2]
    lum = rgb.max(axis=2).astype(float)
    scores = []
    for axis, length in ((0, h), (1, w)):
        lo, hi = int(length*.08), int(length*.92)
        band = lum[:, lo:hi] if axis == 0 else lum[lo:hi, :]
        profile = np.median(band, axis=1-axis)
        contrasts = []
        step = length / n
        for i in range(1, n):
            mid = i*step
            a, b = max(0, int(mid-step*.14)), min(length, int(mid+step*.14)+1)
            level = max(profile[max(0, int(mid-step*.4))],
                        profile[min(length-1, int(mid+step*.4))], 1)
            contrasts.append(max(0, (level-profile[a:b].min())/level))
        scores.append(float(np.mean(contrasts)) if contrasts else 0)
    return min(scores)


def _read_quad(img, n, quad, params, rect=None):
    try:
        q = np.asarray(quad, dtype=float)
        if np.min(np.linalg.norm(np.roll(q, -1, axis=0)-q, axis=1)) < n*3:
            return FaceDetection(n, [], False, reason="region too small")
        patch = imageops.warp_quad(img, quad, max(96, n*32))
    except (ValueError, np.linalg.LinAlgError):
        return FaceDetection(n, [], False, reason="invalid corners")
    side = patch.shape[0] - 1
    sampling = dict(center=(side/2, side/2), axes=(np.array([1, 0]), np.array([0, 1])),
                    size=(side, side))
    hsv = rgb_to_hsv(patch)
    cells = _sample_grid(hsv, _foreground_mask(*hsv, params), sampling, n, params)
    known = sum(bool(c) for row in cells for c in row)
    return FaceDetection(n, cells, known == n*n,
                         "" if known == n*n else "partial", rect=rect,
                         confidence=known/(n*n), image_quad=np.asarray(quad).tolist())


def detect_face_grid(image_rgb, n: int, params: VisionParams = _P, quad=None) -> FaceDetection:
    """自动定位一个面，或按用户给出的 TL/TR/BR/BL 四角识别。"""
    if n < 2 or n > 17:
        return FaceDetection(n, [], False, reason="invalid order")
    try:
        img = imageops.as_uint8_rgb(image_rgb)
        if not img.size:
            raise ValueError("empty image")
    except Exception:
        return FaceDetection(n, [], False, reason="bad image")
    if quad is not None:
        q = np.asarray(quad, dtype=float)
        if q.shape != (4, 2) or not np.isfinite(q).all():
            return FaceDetection(n, [], False, reason="invalid corners")
        if np.any(q < 0) or np.any(q[:, 0] > img.shape[1]-1) or np.any(q[:, 1] > img.shape[0]-1):
            return FaceDetection(n, [], False, reason="invalid corners")
        return _read_quad(img, n, q, params)

    work, _ = imageops.fit_max_dim(img, params.work_max_dim)
    hsv = rgb_to_hsv(work)
    mask = _foreground_mask(*hsv, params)
    clean = imageops.erode(mask, params.mask_erode)
    scale_xy = np.array([(img.shape[1]-1) / max(1, work.shape[1]-1),
                         (img.shape[0]-1) / max(1, work.shape[0]-1)])
    best = None
    seen = set()
    # 先桥接细切缝，逐步扩大，避免一次膨胀把界面按钮和背景并进魔方面。
    radii = sorted(set(min(params.component_dilate_max, r) for r in (2, 4, 7, 12, 18, 24)))
    for radius in radii:
        candidates = []
        for comp in imageops.component_masks(imageops.dilate(clean, radius)):
            ys, xs = np.nonzero(comp & mask)
            if len(xs) < 80:
                continue
            signature = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), len(xs))
            if signature in seen:
                continue
            seen.add(signature)
            pts = np.stack([xs, ys], axis=1).astype(float)
            try:
                rect = _canonical_rect(imageops.min_area_rect(pts))
                w, h = rect["size"]
                if min(w, h) < 12 or abs(w-h)/max(w, h) > params.max_aspect_err:
                    continue
                if len(xs) / max(w*h, 1) < params.min_fill_ratio:
                    continue
                q = _candidate_quad(pts, rect)
                patch = imageops.warp_quad(work, q, max(96, n*32))
            except (ValueError, np.linalg.LinAlgError):
                continue
            evidence = _grid_evidence(patch, n)
            if evidence < .08:
                continue
            det = _read_quad(img, n, q*scale_xy, params, rect)
            candidates.append((det.confidence, w*h, det))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            current = candidates[0][2]
            if current.ok:
                return current
            if best is None or current.confidence > best.confidence:
                best = current
    return best or FaceDetection(n, [], False, reason="no grid")


def detect_face_from_rgb_bytes(data, width: int, height: int, n: int,
                               channels: int = 4,
                               params: VisionParams = _P) -> FaceDetection:
    """从原始像素字节（如 Kivy Texture.pixels）识别。"""
    arr = np.frombuffer(data, dtype=np.uint8)
    expected = width * height * channels
    if arr.size < expected:
        return FaceDetection(n, [], False, reason="short buffer")
    arr = arr[:expected].reshape(height, width, channels)
    return detect_face_grid(arr[:, :, :3], n, params)
