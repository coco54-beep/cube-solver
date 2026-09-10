"""应用级常量。"""

# 六面与颜色
FACES = ("U", "D", "F", "B", "R", "L")
FACE_LABEL = {"U": "上", "D": "下", "F": "前", "B": "后", "R": "右", "L": "左"}

# 颜色 -> 显示名 / RGB
COLOR_INFO = {
    "W": ("白", (1.0, 1.0, 1.0, 1.0)),
    "Y": ("黄", (1.0, 0.87, 0.0, 1.0)),
    "R": ("红", (0.85, 0.1, 0.1, 1.0)),
    "O": ("橙", (1.0, 0.55, 0.0, 1.0)),
    "B": ("蓝", (0.1, 0.25, 0.85, 1.0)),
    "G": ("绿", (0.0, 0.65, 0.2, 1.0)),
}

COLOR_ORDER = ("W", "Y", "R", "O", "B", "G")

# 应用名称与版本
APP_NAME = "3D魔方智能还原"
APP_VERSION = "1.2.1"

# 求解器阶段 -> i18n key（由 app.i18n.tr 翻译）
STAGE_LABEL = {
    "centers": "stage.centers",
    "edge_pairing": "stage.edge_pairing",
    "orient": "stage.orient",
    "parity": "stage.parity",
    "reduced_3x3": "stage.reduced_3x3",
}
