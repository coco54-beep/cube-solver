"""摄像头识别参数。

阈值参考 Kociemba 原版 vision_params（OpenCV 的 HSV 约定：H 0-179，
S/V 0-255），并针对「逐面拍照」场景做了保守化处理。所有值集中在
VisionParams 里，便于按不同魔方配色 / 光照微调。
"""

from dataclasses import dataclass


@dataclass
class VisionParams:
    # ---- 前景（贴纸）判定 ----
    val_min: int = 60            # V 低于此值视为黑框 / 背景
    sat_white: int = 65          # S<=此值且 V>=val_white 视为白色贴纸
    val_white: int = 150
    sat_color: int = 90          # S>=此值视为彩色贴纸
    # ---- 颜色分类（H 阈值，OpenCV 0-179）----
    hue_red_end: int = 6         # H<red_end 或 H>=hue_blue_h -> 红
    hue_orange_h: float = 23
    hue_yellow_h: int = 50
    hue_green_h: int = 100
    hue_blue_h: int = 160
    hue_gb_min_sat: int = 150    # 绿/蓝在低饱和时更可能是白（反光）
    # ---- 检测 ----
    work_max_dim: int = 360      # 检测前把图像缩到此最长边（速度）
    component_dilate_max: int = 24  # 自适应膨胀上限（桥接贴纸间黑框）
    mask_erode: int = 2          # 连通域前腐蚀次数（去噪点）
    min_fill_ratio: float = 0.55  # 前景像素 / 外接矩形面积 下限
    max_aspect_err: float = 0.28  # |w-h|/max(w,h) 上限
    cell_inset: float = 0.62     # 每格取样窗口占格宽比例
    color_reference_hsv: object = None  # 普通魔方六色实物校准参考（W/Y/R/O/B/G）
    hue_oy_margin: float = 0.75   # 黄/橙分界附近保留不确定，支持实物取色校准
    min_cell_confident: int = 1  # 每格至少多少个可用像素


DEFAULT = VisionParams()
