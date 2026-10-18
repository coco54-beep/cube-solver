"""图像来源：文件导入、Kivy 相机快照、可选 OpenCV 相机。

识别核心只吃 numpy 数组，本模块负责把各平台的图像统一成 (H,W,3) uint8。
OpenCV 完全可选：仅作为桌面端取帧/读图的加速后端，缺失时自动回退。
"""

import os
from typing import Optional

import numpy as np


def cv2_available() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except Exception:
        return False


def _reorder_channels(buf: bytes, width: int, height: int, colorfmt: str) -> np.ndarray:
    arr = np.frombuffer(buf, dtype=np.uint8)
    cf = (colorfmt or "rgba").lower()
    if cf in ("rgba", "bgra"):
        arr = arr[: width * height * 4].reshape(height, width, 4)
        if cf == "bgra":
            arr = arr[:, :, [2, 1, 0, 3]]
        return arr[:, :, :3]
    if cf in ("rgb", "bgr"):
        arr = arr[: width * height * 3].reshape(height, width, 3)
        if cf == "bgr":
            arr = arr[:, :, ::-1]
        return arr
    # 未知格式：按 RGBA 尝试
    arr = arr[: width * height * 4].reshape(height, width, 4)
    return arr[:, :, :3]


def texture_to_rgb(texture) -> Optional[np.ndarray]:
    """Kivy Texture -> RGB numpy（供相机快照用）。"""
    if texture is None:
        return None
    try:
        width, height = int(texture.width), int(texture.height)
        buf = texture.pixels
        # Kivy 的 pixels 读取接口始终返回 RGBA，与纹理存储的 colorfmt 无关。
        rgb = _reorder_channels(buf, width, height, "rgba")
        # Texture UV 顺序为 BL/BR/TR/TL，像素缓冲行序不一定等同屏幕行序。
        uv = np.asarray(getattr(texture, "tex_coords", (0, 0, 1, 0, 1, 1, 0, 1))).reshape(4, 2)
        tl, tr, bl = uv[3], uv[2], uv[0]
        # Camera/image textures normally use only flips or quarter turns.
        # These are array views, avoiding several full-resolution float grids.
        rounded = np.rint(np.array([tl, tr, bl])).astype(int)
        if np.allclose([tl, tr, bl], rounded, atol=1e-7) and np.all((rounded >= 0) & (rounded <= 1)):
            origin, right, down = rounded
            du, dv = right-origin, down-origin
            if np.sum(abs(du)) == 1 and np.sum(abs(dv)) == 1 and np.dot(du, dv) == 0:
                if du[0]:
                    return rgb[::int(dv[1]), ::int(du[0])].copy()
                # Match the existing output dimensions for non-square textures.
                xs = np.rint(np.linspace(0, width-1, height)).astype(int)
                ys = np.rint(np.linspace(0, height-1, width)).astype(int)
                if dv[0] < 0: xs = width-1-xs
                if du[1] < 0: ys = height-1-ys
                return rgb[ys[None, :], xs[:, None]].copy()
        u, v = np.meshgrid(np.linspace(0, 1, width), np.linspace(0, 1, height))
        coords = tl + u[..., None]*(tr-tl) + v[..., None]*(bl-tl)
        xs = np.clip(np.rint(coords[..., 0]*(width-1)).astype(int), 0, width-1)
        ys = np.clip(np.rint(coords[..., 1]*(height-1)).astype(int), 0, height-1)
        return rgb[ys, xs].copy()
    except Exception:
        return None


def load_image_file_rgb(path: str) -> Optional[np.ndarray]:
    """读取图片并按 EXIF 校正方向；Pillow/OpenCV 均为可选。"""
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image, ImageOps
        with Image.open(path) as image:
            return np.asarray(ImageOps.exif_transpose(image).convert("RGB")).copy()
    except Exception:
        pass
    if cv2_available():
        try:
            import cv2
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                return img[:, :, ::-1]  # BGR -> RGB
        except Exception:
            pass
    try:
        from kivy.core.image import Image as CoreImage
        core = CoreImage(path, nocache=True)
        return texture_to_rgb(core.texture)
    except Exception:
        return None


class CameraSession:
    """相机取帧会话接口。"""

    def is_available(self) -> bool:
        raise NotImplementedError

    def grab(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    def release(self):
        pass


class KivyCameraSession(CameraSession):
    """包装 kivy.uix.camera.Camera 部件，从其实时纹理取帧。"""

    def __init__(self, widget):
        self.widget = widget

    def is_available(self) -> bool:
        return self.widget is not None and getattr(self.widget, "texture", None) is not None

    def grab(self) -> Optional[np.ndarray]:
        if self.widget is None:
            return None
        return texture_to_rgb(getattr(self.widget, "texture", None))

    def release(self):
        if self.widget is not None:
            self.widget.play = False
            provider = getattr(self.widget, "_camera", None)
            release = getattr(provider, "_release_camera", None)
            if release:
                release()
            self.widget = None


class Cv2CameraSession(CameraSession):
    """OpenCV 相机（桌面端，可选）。"""

    def __init__(self, index: int = 0):
        self.index = index
        self._cap = None
        if cv2_available():
            try:
                import cv2
                self._cap = cv2.VideoCapture(index)
                if not self._cap.isOpened():
                    self._cap.release()
                    self._cap = None
            except Exception:
                self._cap = None

    def is_available(self) -> bool:
        return self._cap is not None

    def grab(self) -> Optional[np.ndarray]:
        if self._cap is None:
            return None
        try:
            import cv2
            ok, frame = self._cap.read()
            if not ok or frame is None:
                return None
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            return None

    def release(self):
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


def make_kivy_camera_widget(index: int = 0, resolution=(640, 480)):
    """尽力创建一个 Kivy Camera 部件；无可用 provider 时返回 None。"""
    try:
        from kivy.uix.camera import Camera
        cam = Camera(index=index, resolution=resolution, play=True)
        return cam
    except Exception:
        return None
