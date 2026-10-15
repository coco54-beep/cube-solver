"""摄像头识别（纯 numpy）。

模块：
    params    识别参数
    colors    RGB->HSV 与颜色分类
    imageops  缩放 / 取样 / 凸包 / 最小外接矩形
    detect    单面照片 -> n×n 颜色网格
    assemble  六面网格 -> 应用 facelets
"""

from vision.detect import FaceDetection, detect_face_grid  # noqa: F401
from vision.assemble import (  # noqa: F401
    FACES,
    CAPTURE_ORDER,
    assemble_facelets,
    rotate_grid,
    label_by_center,
)
