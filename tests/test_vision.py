"""摄像头识别核心（纯 numpy）单元测试。

不依赖相机：用合成图像验证颜色分类、网格检测与六面拼装。
"""

import random

import numpy as np
import pytest

from vision import imageops
from vision.assemble import (
    assemble_facelets,
    label_by_center,
    rotate_grid,
)
from vision.colors import classify_hsv, rgb_to_hsv, COLOR_CODES
from vision.detect import detect_face_grid

# 贴近真实魔方贴纸的 RGB
STICKER_RGB = {
    "W": (240, 240, 240),
    "Y": (250, 210, 40),
    "R": (200, 30, 40),
    "O": (240, 130, 30),
    "G": (30, 180, 70),
    "B": (30, 80, 220),
}


def _render_face(colors, n, cell=48, border=6, angle=0.0, bg=(30, 30, 30)):
    """渲染一张合成"面"照片：n×n 贴纸 + 黑框 + 背景，可选旋转。"""
    side = n * cell
    face = np.full((side, side, 3), bg, dtype=np.uint8)
    for r in range(n):
        for c in range(n):
            y0 = r * cell + border
            y1 = (r + 1) * cell - border
            x0 = c * cell + border
            x1 = (c + 1) * cell - border
            face[y0:y1, x0:x1] = STICKER_RGB[colors[r][c]]

    if abs(angle) > 1e-6:
        # 旋转到更大的画布，避免裁边
        diag = int(np.ceil(side * 1.5))
        canvas = np.full((diag, diag, 3), bg, dtype=np.uint8)
        off = (diag - side) // 2
        canvas[off:off + side, off:off + side] = face
        yy, xx = np.mgrid[0:diag, 0:diag].astype(np.float64)
        c0 = (diag - 1) / 2.0
        rad = np.deg2rad(angle)
        cos_a, sin_a = np.cos(rad), np.sin(rad)
        xs = c0 + (xx - c0) * cos_a - (yy - c0) * sin_a
        ys = c0 + (xx - c0) * sin_a + (yy - c0) * cos_a
        face = imageops.sample_points(canvas, xs, ys).astype(np.uint8)

    # 放到带留白的背景上（模拟"拍到桌子/周围"）
    pad = 40
    h, w = face.shape[:2]
    out = np.full((h + 2 * pad, w + 2 * pad, 3), bg, dtype=np.uint8)
    out[pad:pad + h, pad:pad + w] = face
    return out


def _homography(src_pts, dst_pts):
    a = []
    b = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    h = np.linalg.solve(np.array(a, float), np.array(b, float))
    return np.append(h, 1.0).reshape(3, 3)


def _render_photo(grid, n, angle=0.0, persp=0.05, bg=(38, 40, 46), seed=1):
    """合成一张"照片"：面 + 旋转 + 透视 + 非均匀光照 + 噪点（纯 numpy）。"""
    cell, border = 62, 4
    side = n * cell
    face = np.full((side, side, 3), bg, np.uint8)
    for r in range(n):
        for c in range(n):
            y0, x0 = r * cell + border, c * cell + border
            face[y0:y0 + cell - 2 * border, x0:x0 + cell - 2 * border] = STICKER_RGB[grid[r][c]]

    canvas = 520
    rng = np.random.default_rng(seed)
    half = side / 2.0
    a = np.deg2rad(angle)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    corners = (np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], float) * half) @ rot.T
    corners += rng.uniform(-persp, persp, corners.shape) * side
    dst = corners + [canvas / 2.0, canvas / 2.0]
    src = np.array([[0, 0], [side, 0], [side, side], [0, side]], float)
    H = np.linalg.inv(_homography(src, dst))  # 输出像素 -> 源像素

    yy, xx = np.mgrid[0:canvas, 0:canvas].astype(np.float64)
    den = H[2, 0] * xx + H[2, 1] * yy + H[2, 2]
    sx = (H[0, 0] * xx + H[0, 1] * yy + H[0, 2]) / den
    sy = (H[1, 0] * xx + H[1, 1] * yy + H[1, 2]) / den
    inside = (sx >= 0) & (sx < side) & (sy >= 0) & (sy < side)
    photo = np.tile(np.array(bg, float), (canvas, canvas, 1))
    sampled = imageops.sample_points(face, sx, sy)
    photo[inside] = sampled[inside]
    grad = 0.72 + 0.5 * (xx / canvas) - 0.18 * (yy / canvas)
    # 亮度噪声（三通道相关，接近相机/JPEG 表现）
    lum = rng.normal(0, 6.0, (canvas, canvas, 1))
    photo = photo * grad[..., None] + lum
    return np.clip(photo, 0, 255).astype(np.uint8)


def _random_grid(n, seed):
    rng = random.Random(seed)
    return [[rng.choice(COLOR_CODES) for _ in range(n)] for _ in range(n)]


# ---------------- 颜色分类 ----------------

def test_rgb_to_hsv_known_colors():
    for name, rgb in STICKER_RGB.items():
        arr = np.array([[rgb]], dtype=np.uint8)
        H, S, V = rgb_to_hsv(arr)
        code = classify_hsv(int(H[0, 0]), int(S[0, 0]), int(V[0, 0]))
        assert code == name, (name, rgb, int(H[0, 0]), int(S[0, 0]), int(V[0, 0]))


def test_dark_pixel_is_background():
    arr = np.array([[[10, 10, 10]]], dtype=np.uint8)
    H, S, V = rgb_to_hsv(arr)
    assert classify_hsv(int(H[0, 0]), int(S[0, 0]), int(V[0, 0])) is None


# ---------------- 网格检测 ----------------

@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_detect_upright(n):
    grid = _random_grid(n, seed=n)
    img = _render_face(grid, n)
    det = detect_face_grid(img, n)
    assert det.ok, det.reason
    assert det.grid() == grid


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_detect_rotated_keeps_colors(n):
    grid = _random_grid(n, seed=100 + n)
    img = _render_face(grid, n, angle=13.0)
    det = detect_face_grid(img, n)
    assert det.ok, det.reason
    got = det.grid()
    from collections import Counter
    assert Counter(c for row in got for c in row) == \
        Counter(c for row in grid for c in row)


def _matches_upto_rotation(det_grid, grid, n):
    g = grid
    for _ in range(4):
        if det_grid == g:
            return True
        g = rotate_grid(g, 1)
    return False


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_detect_photo_perspective_rotation_lighting(n):
    """照片级合成图：透视 + 旋转 + 非均匀光照 + 噪点，识别应正确。"""
    grid = _random_grid(n, seed=500 + n)
    img = _render_photo(grid, n, angle=9.0, persp=0.05, seed=n)
    det = detect_face_grid(img, n)
    assert det.ok, det.reason
    assert _matches_upto_rotation(det.grid(), grid, n), det.grid()


def test_detect_rejects_non_square():
    # 长条状前景（不是正方形面）应判定失败
    img = np.full((300, 300, 3), 30, dtype=np.uint8)
    img[100:140, 40:260] = STICKER_RGB["G"]
    det = detect_face_grid(img, 3)
    assert not det.ok


def test_detect_rejects_blank():
    img = np.full((200, 200, 3), 30, dtype=np.uint8)
    det = detect_face_grid(img, 3)
    assert not det.ok


# ---------------- 拼装 ----------------

def test_rotate_grid():
    g = [["A", "B"], ["C", "D"]]
    assert rotate_grid(g, 1) == [["C", "A"], ["D", "B"]]
    assert rotate_grid(g, 2) == [["D", "C"], ["B", "A"]]
    assert rotate_grid(g, 4) == g


def test_label_by_center_odd():
    n = 3
    from cube.colors import DEFAULT_COLORS
    grids = []
    expected = {}
    for face, color in DEFAULT_COLORS.items():
        g = [[color] * n for _ in range(n)]
        g[1][1] = color
        grids.append(g)
        expected[face] = g
    assigned = label_by_center(grids, n)
    assert assigned is not None
    assert set(assigned) == set(DEFAULT_COLORS)


def test_label_by_center_even_is_none():
    n = 2
    grids = [[["W"] * n for _ in range(n)] for _ in range(6)]
    assert label_by_center(grids, n) is None


def test_end_to_end_solved_3x3_passes_validation():
    from cube.conversion import cubies_to_facelets
    from cube.cube3 import Cube3
    from cube.validation import validate_3x3

    facelets = cubies_to_facelets(Cube3.solved().cubies, 3)
    grids = {}
    for face, grid in facelets.items():
        det = detect_face_grid(_render_face(grid, 3), 3)
        assert det.ok, (face, det.reason)
        grids[face] = det.grid()
    assembled = assemble_facelets(grids, 3)
    assert validate_3x3(assembled) == []


def test_end_to_end_scrambled_3x3_passes_validation():
    from cube.conversion import cubies_to_facelets
    from cube.cube3 import Cube3
    from cube.scramble import random_scramble
    from cube.validation import validate_3x3

    cube = Cube3.solved()
    cube.apply_moves(random_scramble(3))
    facelets = cubies_to_facelets(cube.cubies, 3)
    grids = {}
    for face, grid in facelets.items():
        det = detect_face_grid(_render_face(grid, 3), 3)
        assert det.ok, (face, det.reason)
        grids[face] = det.grid()
    assembled = assemble_facelets(grids, 3)
    assert assembled == facelets
    assert validate_3x3(assembled) == []


def test_assemble_facelets_shape():
    n = 3
    grids = {f: [["W"] * n for _ in range(n)] for f in ("U", "D", "F", "B", "R", "L")}
    facelets = assemble_facelets(grids, n)
    assert set(facelets) == {"U", "D", "F", "B", "R", "L"}
    assert facelets["F"][0][0] == "W"
