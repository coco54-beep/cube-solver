"""纯 numpy 的 RGB -> HSV 与贴纸颜色分类。

采用 OpenCV 的 HSV 约定：H 为 0-179（角度/2），S/V 为 0-255。
颜色编码与应用一致：W/Y/R/O/B/G（见 cube.colors）。
"""

from typing import Optional, Tuple

import numpy as np

from vision.params import DEFAULT as _P

COLOR_CODES = ("W", "Y", "R", "O", "B", "G")


def rgb_to_hsv(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RGB(uint8 或 float) -> (H, S, V)。

    H: int32, 0-179; S: int32, 0-255; V: int32, 0-255。
    输入形状 (..., 3)。
    """
    arr = np.asarray(rgb)
    if arr.dtype == np.uint8:
        arr = arr.astype(np.float64) / 255.0
    else:
        arr = arr.astype(np.float64)
        if arr.size and arr.max() > 1.5:
            arr = arr / 255.0
    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc

    v = maxc
    s = np.where(maxc > 1e-12, delta / np.maximum(maxc, 1e-12), 0.0)

    h = np.zeros_like(maxc)
    nz = delta > 1e-12
    rmax = nz & (maxc == r)
    gmax = nz & (maxc == g) & ~rmax
    bmax = nz & (maxc == b) & ~rmax & ~gmax

    with np.errstate(invalid="ignore", divide="ignore"):
        hr = ((g - b) / delta) % 6.0
        hg = ((b - r) / delta) + 2.0
        hb = ((r - g) / delta) + 4.0
    h = np.where(rmax, hr, h)
    h = np.where(gmax, hg, h)
    h = np.where(bmax, hb, h)
    h = (h / 6.0) * 360.0          # 角度 0-360
    h = h / 2.0                    # OpenCV 0-179

    H = np.clip(np.round(h), 0, 179).astype(np.int32)
    S = np.clip(np.round(s * 255.0), 0, 255).astype(np.int32)
    V = np.clip(np.round(v * 255.0), 0, 255).astype(np.int32)
    return H, S, V


def _classify_reference(h, s, v, params):
    refs = params.color_reference_hsv
    _, white_s, white_v = refs[0]
    if s <= max(params.sat_white, min(params.sat_color-1, white_s+15)):
        return "W" if v >= max(params.val_min, white_v*.5) else None
    if s < min(params.sat_color, max(50, min(ref[1] for ref in refs[1:])*.65)):
        return None
    scores = []
    hue_distances = {}
    for i, (rh, rs, rv) in enumerate(refs[1:], 1):
        dh = abs(h-rh)
        dh = min(dh, 180-dh)
        hue_distances[i] = dh
        score = 4*(dh/90)**2 + .10*((s-rs)/255)**2 + .05*((v-rv)/255)**2
        scores.append((score, i))
    scores.sort()
    best, index = scores[0]
    if best > .5 or scores[1][0]-best < .004:
        return None
    if {index, scores[1][1]} == {1, 3} and abs(hue_distances[1]-hue_distances[3]) <= 2*params.hue_oy_margin:
        return None
    return COLOR_CODES[index]


def classify_hsv(h: int, s: int, v: int, params=_P) -> Optional[str]:
    """单个像素 HSV -> 颜色编码；返回 None 表示黑框/背景。"""
    if v < params.val_min:
        return None
    if params.color_reference_hsv is not None:
        return _classify_reference(h, s, v, params)
    if s <= params.sat_white and v >= params.val_white:
        return "W"
    if s < params.sat_color:
        return None
    if abs(h - params.hue_orange_h) <= params.hue_oy_margin:
        return None
    if params.hue_red_end <= h < params.hue_orange_h:
        return "O"
    if params.hue_orange_h <= h < params.hue_yellow_h:
        return "Y"
    if params.hue_yellow_h <= h < params.hue_green_h:
        return "G"
    if params.hue_green_h <= h < params.hue_blue_h:
        return "B"
    return "R"
