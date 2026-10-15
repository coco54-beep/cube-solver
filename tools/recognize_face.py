"""无相机时的单面识别命令行工具（用于拿截图/照片快速自测）。

用法：
    python tools/recognize_face.py <图片路径> <阶数>
    python tools/recognize_face.py demo.jpg 3

打印识别到的 n×n 颜色网格，并在原图旁写出 <图片>.scan.png：
把每个格子的取样中心标出来，方便目视核对识别是否对准。

颜色编码：W 白 / Y 黄 / R 红 / O 橙 / B 蓝 / G 绿；? 表示该格无法判定。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.capture import load_image_file_rgb  # noqa: E402
from vision.detect import detect_face_grid  # noqa: E402
from vision.params import DEFAULT as _P  # noqa: E402

COLOR_CN = {"W": "白", "Y": "黄", "R": "红", "O": "橙", "B": "蓝", "G": "绿"}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    path, order = argv[1], argv[2]
    if not order.isdigit():
        print("阶数必须是整数")
        return 2
    n = int(order)

    img = load_image_file_rgb(path)
    if img is None:
        print("无法读取图片：%s" % path)
        return 1

    det = detect_face_grid(img, n)
    print("识别成功=%s  原因=%s  置信度=%.2f" % (det.ok, det.reason or "-", det.confidence))
    if det.cells:
        for row in det.cells:
            print("  " + " ".join((c or "?") for c in row))
        print("  中文：" + " / ".join(
            "".join(COLOR_CN.get(c or "?", "?") for c in row) for row in det.cells))

    _write_overlay(img, det, n, path)
    return 0


def _write_overlay(img, det, n, path):
    if det.rect is None:
        return
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover
        print("跳过叠加图（需要 Pillow）：%s" % exc)
        return
    h, w = img.shape[:2]
    sc = 1.0
    m = max(h, w)
    if m > _P.work_max_dim:
        sc = _P.work_max_dim / float(m)
    inv = 1.0 / sc if sc else 1.0
    cx, cy = det.rect["center"]
    ux, uy = det.rect["axes"]
    w_, h_ = det.rect["size"]

    vis = Image.fromarray(img.copy())
    d = ImageDraw.Draw(vis)
    for r in range(n):
        for c in range(n):
            a = ((c + 0.5) / n - 0.5) * w_
            b = ((r + 0.5) / n - 0.5) * h_
            x = (cx + a * ux[0] + b * uy[0]) * inv
            y = (cy + a * ux[1] + b * uy[1]) * inv
            d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 0, 255), width=2)
    out = path + ".scan.png"
    vis.save(out)
    print("叠加图 -> %s" % out)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
