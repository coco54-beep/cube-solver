"""逐面拍照 / 导入图片，按普通或异形模型的色块轮廓识别并转入录入。

面的顺序与录入页「>」键一致（F→R→U→B→L→D，见 renderer.cube_orientation）。
按 < / > 切换当前要拍的面时，会提示需要把魔方往哪个方向翻转。

流程：
    1. 把魔方的当前面正对取景框的方框拍照（或导入照片）。
    2. 识别结果显示在下方，可用 < / > 切换到下一面继续拍。
    3. 「应用到录入」把已识别的面填进录入页（未拍完也可用）。

识别核心见 vision 包（纯 numpy，无 OpenCV 依赖）。
"""

import threading
from copy import deepcopy
from dataclasses import replace
from time import perf_counter

import numpy as np
from kivy.graphics import Color, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.constants import COLOR_INFO
from app.i18n import tr
from renderer.cube_orientation import CubeOrientation
from ui.widgets.scan_cube import ScanCubeView
from ui.widgets import metrics as m
from ui.widgets.buttons import ArrowButton, PrimaryButton, UIButton

from vision.assemble import assemble_facelets, empty_grid, orient_grid
from vision.capture import (
    Cv2CameraSession,
    KivyCameraSession,
    cv2_available,
    load_image_file_rgb,
    make_kivy_camera_widget,
)
from vision.detect import detect_face_grid, _cell_color
from vision.params import DEFAULT as VISION_DEFAULT
from vision.colors import COLOR_CODES, rgb_to_hsv
from vision.imageops import project_quad
from vision.scan_profiles import ScanProfile, detect_surface, project_controls, _read_color

_EMPTY = (0.20, 0.23, 0.30, 1)
_BORDER = (0.05, 0.05, 0.05, 1)

class _CalibrationSwatch(UIButton):
    def __init__(self, rgba, **kwargs):
        self.rgba = tuple(rgba)
        super().__init__(**kwargs)
        luminance = .2126*rgba[0] + .7152*rgba[1] + .0722*rgba[2]
        self.color = (.03, .03, .03, 1) if luminance > .48 else (1, 1, 1, 1)

    def _button_color(self):
        return self.rgba

    def _pressed_color(self):
        return tuple(c*.8 for c in self.rgba[:3])+(1,)


class _GuideOverlay(Widget):
    """顶点始终相对实际照片定位，框线与取色共用同一映射。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_size = None
        self.quad = np.array([[.14, .14], [.86, .14], [.86, .86], [.14, .86]])
        self.n = 2
        self.editable = False
        self.on_adjust = None
        self.on_sample = None
        self.frame = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
        self.lines = None
        self.aspect = 1.
        self._drag = None
        self.bind(pos=self._redraw, size=self._redraw)

    def _image_rect(self):
        iw, ih = self.image_size or (1, 1)
        scale = min(self.width/max(iw, 1), self.height/max(ih, 1))
        w, h = iw*scale, ih*scale
        # pos 回调可能早于 Kivy 对 center 的缓存失效；直接按位置计算，
        # 防止旋转屏幕后边框仍留在旧的纵向位置。
        return self.x+(self.width-w)/2, self.y+(self.height-h)/2, w, h

    def _screen_points(self):
        x, y, w, h = self._image_rect()
        return [(x+u*w, y+(1-v)*h) for u, v in self.quad]

    def image_quad(self):
        if self.image_size is None:
            return None
        return self.quad * np.array([self.image_size[0]-1, self.image_size[1]-1])

    def set_image(self, size, quad=None):
        self.image_size = size
        if quad is None:
            w, h = size or (1, 1)
            span = .72*min(w, h)/max(1., self.aspect)
            sx, sy = span/2/max(w, 1), span*self.aspect/2/max(h, 1)
            self.quad = .5 + (self.frame-.5)*[2*sx, 2*sy]
        else:
            self.quad = np.asarray(quad) / np.maximum(np.array(size)-1, 1)
        self._redraw()

    def set_template(self, frame=None, lines=None, aspect=1.):
        frame = np.asarray(frame if frame is not None else [[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
        changed = len(frame) != len(self.frame) or abs(aspect-self.aspect)>1e-6
        self.aspect = aspect
        self.frame, self.lines = frame, lines
        if changed:
            self.set_image(self.image_size)
        else:
            self._redraw()

    def on_touch_down(self, touch):
        if not self.editable or not self.collide_point(*touch.pos):
            return False
        distances = [np.hypot(touch.x-x, touch.y-y) for x, y in self._screen_points()]
        closest = int(np.argmin(distances))
        if distances[closest] > m.h(24):
            if self.on_sample and self.image_size:
                x, y, w, h = self._image_rect()
                u, v = (touch.x-x)/max(w, 1), 1-(touch.y-y)/max(h, 1)
                if 0 <= u <= 1 and 0 <= v <= 1:
                    return bool(self.on_sample(u*(self.image_size[0]-1), v*(self.image_size[1]-1)))
            return False
        self._drag = closest
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        x, y, w, h = self._image_rect()
        self.quad[self._drag] = (np.clip((touch.x-x)/max(w, 1), 0, 1),
                                 np.clip(1-(touch.y-y)/max(h, 1), 0, 1))
        self._redraw()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self._drag = None
        if self.on_adjust:
            self.on_adjust()
        return True

    def _redraw(self, *args):
        self.canvas.clear()
        if min(self.width, self.height) < 20:
            return
        points = np.asarray(self._screen_points())
        theme = _app().theme
        with self.canvas:
            Color(*theme.accent)
            Line(points=points.flatten().tolist(), close=True, width=1.5)
            Color(*theme.accent_dim)
            for i in range(1, self.n) if self.lines is None else ():
                t = i/self.n
                try:
                    u, v = project_quad(self.quad, [t, t, 0, 1], [0, 1, t, t])
                    x, y, w, h = self._image_rect()
                    lines = np.column_stack((x+u*w, y+(1-v)*h))
                    Line(points=lines[:2].flatten().tolist(), width=1)
                    Line(points=lines[2:].flatten().tolist(), width=1)
                except (ValueError, np.linalg.LinAlgError):
                    # 拖动中四角交叉时仅保留外框，等待用户重新对齐。
                    pass
            for outline in self.lines or ():
                try:
                    uv = project_controls(self.frame, self.quad, outline)
                    x, y, w, h = self._image_rect()
                    xy = np.column_stack((x+uv[:,0]*w, y+(1-uv[:,1])*h))
                    Line(points=xy.flatten().tolist(), close=True, width=1)
                except (ValueError, np.linalg.LinAlgError):
                    pass
            Color(*theme.accent)
            for x, y in points:
                Line(circle=(x, y, m.h(6)), width=2)


class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ori = CubeOrientation(4)
        self._data = {}
        self._source_image = None
        import os
        self._parked_image_path = os.path.join(_app().user_data_dir, 'camera-last.npy')
        self._parked_quad = None
        self._parked_face = None
        self._parked_digest = None
        self._photo_dirty = False
        self._session = None
        self._camera_widget = None
        self._preview_image = None
        self._preview_event = None
        self._permission_pending = False
        self._active = False
        self._suspended = False
        self._turning = False
        self._picker_pending = False
        self._photo_picker = None
        self._sensor_info = None
        self._initialized = False
        self._n_for_screen = None
        self._cube_for_screen = None
        self._profile = None
        self._standard_params = replace(VISION_DEFAULT)
        self._standard_palette = tuple(COLOR_INFO[c][1] for c in COLOR_CODES)
        self._calibrated_codes = set()
        self._color_samples = {}
        self._manual_cells = set()
        self._calibration_slot = None
        self._recognizing = False
        self._scan_job = None
        self.build_ui()

    # ---- UI ----
    def build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=m.h(6),
                         padding=[m.h(8), m.h(6), m.h(8), m.h(8)])
        self._root_layout = root

        top = BoxLayout(size_hint_y=None, height=m.h(48), spacing=8)
        self.btn_back = UIButton(text="", icon_name="back", size_hint_x=0.22)
        self.btn_back.bind(on_release=lambda *a: self.go_back())
        self.title = Label(text=tr("camera.title", n=self._n()),
                           halign="center", valign="middle", font_size="16sp", bold=True)
        self.title.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        top.add_widget(self.btn_back)
        top.add_widget(self.title)
        top.add_widget(Widget(size_hint_x=0.22))
        root.add_widget(top)

        self.tip = Label(text=tr("camera.tip"), size_hint_y=None, height=m.h(30),
                         font_size="12sp", color=_app().theme.text_muted,
                         halign="center", valign="middle")
        self.tip.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        root.add_widget(self.tip)

        # 相机预览（占据剩余空间）+ 取景框
        self.preview = FloatLayout(size_hint=(1, 1))
        self.guide = _GuideOverlay(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.guide.on_adjust = self.recheck
        self.guide.on_sample = self.sample_color
        self.preview.add_widget(self.guide)
        root.add_widget(self.preview)

        # 识别结果可点选改色；照片操作和结果放在同一行。
        self.grid_box = BoxLayout(size_hint_y=None, height=m.h(112), spacing=m.h(10))
        self.grid = ScanCubeView(size_hint=(None, None), size=(m.h(108), m.h(108)))
        self.grid.on_cell = self.edit_cell
        self.grid_box.add_widget(self.grid)
        tools = BoxLayout(orientation="vertical", spacing=m.h(4))
        self.edit_tip = Label(text=tr("camera.edit_tip"), font_size="12sp", halign="center")
        self.edit_tip.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        tools.add_widget(self.edit_tip)
        controls = BoxLayout(spacing=m.h(8))
        self.btn_rotate = UIButton(text=tr("camera.rotate"), disabled=True)
        self.btn_rotate.bind(on_release=lambda *_: self.rotate_photo())
        self.btn_recheck = UIButton(text=tr("camera.recheck"), disabled=True)
        self.btn_recheck.bind(on_release=lambda *_: self.recheck())
        self.btn_calibrate = UIButton(text=tr('camera.calibrate'), disabled=True)
        self.btn_calibrate.bind(on_release=lambda *_: self.calibrate())
        controls.add_widget(self.btn_rotate)
        controls.add_widget(self.btn_recheck)
        controls.add_widget(self.btn_calibrate)
        self.btn_reset_calibration = UIButton(text=tr("camera.reset_calibration"))
        self.btn_reset_calibration.bind(on_release=lambda *_: self.reset_calibration())
        controls.add_widget(self.btn_reset_calibration)
        for button in (self.btn_rotate, self.btn_recheck, self.btn_calibrate, self.btn_reset_calibration):
            button.font_size='12sp'
            button.halign='center'
            button.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        tools.add_widget(controls)
        self.grid_box.add_widget(tools)
        root.add_widget(self.grid_box)

        from kivy.uix.progressbar import ProgressBar
        self.scan_progress = ProgressBar(max=1, value=0)
        self.scan_cancel = UIButton(text=tr('camera.cancel_scan'), size_hint_x=.22)
        self.scan_cancel.bind(on_release=lambda *_: self.cancel_recognition())
        self.scan_progress_row = BoxLayout(size_hint_y=None, height=0, opacity=0, spacing=m.h(8))
        self.scan_progress_row.add_widget(self.scan_progress)
        self.scan_progress_row.add_widget(self.scan_cancel)
        root.add_widget(self.scan_progress_row)

        # 面导航：< 当前面 >
        nav = BoxLayout(size_hint_y=None, height=m.h(48), spacing=m.h(10))
        self.btn_prev = ArrowButton(direction="left", font_size="20sp", size_hint_x=0.22)
        self.btn_prev.bind(on_release=lambda *a: self.navigate("prev"))
        self.btn_next = ArrowButton(direction="right", font_size="20sp", size_hint_x=0.22)
        self.btn_next.bind(on_release=lambda *a: self.navigate("next"))
        self.face_label = Label(text=tr("camera.face_progress", face="", code="", done=0),
                                halign="center", valign="middle", font_size="16sp", bold=True)
        nav.add_widget(self.btn_prev)
        nav.add_widget(self.face_label)
        nav.add_widget(self.btn_next)
        root.add_widget(nav)

        # 拍照 / 导入 / 应用（未拍完也可用）
        actions = BoxLayout(size_hint_y=None, height=m.h(52), spacing=m.h(8))
        self.btn_capture = PrimaryButton(text="", icon_name="camera")
        self.btn_capture.bind(on_release=lambda *a: self.capture())
        self.btn_import = UIButton(text="", icon_name="image")
        self.btn_import.bind(on_release=lambda *a: self.open_import())
        self.btn_apply = PrimaryButton(text="", icon_name="check")
        self.btn_apply.bind(on_release=lambda *a: self.apply_to_input())
        for b in (self.btn_capture, self.btn_import, self.btn_apply):
            actions.add_widget(b)
        root.add_widget(actions)

        self.msg = Label(text="", size_hint_y=None, height=m.h(40),
                         color=_app().theme.text_muted, halign="center",
                         valign="middle", font_size="13sp")
        self.msg.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        root.add_widget(self.msg)

        self._responsive_height_specs = [
            (top, 48), (self.tip, 30), (self.grid_box, 112),
            (nav, 48), (actions, 52), (self.msg, 40),
        ]
        self.add_widget(root)
        self.bind(size=lambda *_: self._apply_heights())
        from kivy.clock import Clock
        Clock.schedule_once(lambda *_: self._apply_heights(), 0)

    def _apply_heights(self):
        for widget, spec in self._responsive_height_specs:
            if spec is not None:
                widget.height = m.h(spec)
        self.grid.size = (m.h(108), m.h(108))

    # ---- 生命周期 ----
    def on_enter(self):
        self._active = True
        self._suspended = False
        self.msg.text = ""
        n = self._n()
        cube = getattr(_app(), "cube", None)
        if not self._initialized or self._n_for_screen != n or self._cube_for_screen is not cube:
            self._reset_for_n(n)
            self._n_for_screen = n
            self._cube_for_screen = cube
            self._initialized = True
        elif self._profile and getattr(_app(), 'input_from_camera', False):
            # Keep corrections made on the full-size input model when returning.
            if self._profile.kind=='pandora' and getattr(_app(),'facelets_input',None) is not None:
                from vision.scan_profiles import CUBE_CODES
                entered=_app().facelets_input
                updated=self._profile.blank()
                for surface in self._profile.surfaces:
                    face,r,c=surface.cell
                    code=entered[face][r][c]
                    updated[face][surface.index]=CUBE_CODES.index(code) if code in CUBE_CODES else -1
            else:
                updated = self._profile.from_cube(cube)
            for face, values in updated.items():
                self._manual_cells.update((face, i) for i, color in values.items()
                                          if color != self._data[face].get(i, -1))
            self._data = updated
        self.retranslate()
        self._apply_heights()
        self._restore_parked_photo()
        if self._source_image is None:
            self._ensure_source()
        else:
            self._set_preview(self._source_image)
        self._update_face_ui()

    def on_leave(self, *args):
        self._active = False
        self._scan_job = None
        self._set_recognizing(False)
        self.pause_camera()

    def pause_camera(self):
        self._suspended = True
        self._scan_job = None
        self._set_recognizing(False)
        self._cancel_turn()
        self._release_source()
        self._park_photo(drop=True)
        if hasattr(self.grid, '_textures'): self.grid._textures.clear()

    def resume_camera(self):
        self._suspended = False
        # Android dispatches App.on_resume before SDL has finished restoring
        # its GL context. Creating the photo texture there can block resume.
        from kivy.clock import Clock
        def restore(_dt):
            if self._suspended or not self._active or self._picker_pending:
                return
            self._restore_parked_photo()
            if self._source_image is None:
                self._ensure_source()
        Clock.schedule_once(restore, .2)

    def _cancel_turn(self):
        if self._turning:
            if self._profile:
                self.grid.cancel_turn()
            else:
                self.grid._cancel_whole_anim()
            self.grid.set_whole_world(self._ori.world)
            self._set_turning(False)

    def _set_turning(self, busy):
        self._turning = busy
        if busy:
            self._guide_editable = self.guide.editable
            self.guide.editable = False
            self._button_states = {b: b.disabled for b in (self.btn_prev, self.btn_next, self.btn_capture,
                                  self.btn_import, self.btn_apply, self.btn_rotate, self.btn_recheck, self.btn_calibrate, self.btn_reset_calibration)}
            for button in self._button_states:
                button.disabled = True
        else:
            self.guide.editable = getattr(self, '_guide_editable', False)
            for button, disabled in getattr(self, "_button_states", {}).items():
                button.disabled = disabled
            self._button_states = {}

    def _release_source(self):
        if self._preview_event is not None:
            self._preview_event.cancel()
            self._preview_event = None
        if self._session is not None:
            try:
                self._session.release()
            except Exception:
                pass
            self._session = None
        if self._camera_widget is not None and self._camera_widget.parent:
            self._camera_widget.parent.remove_widget(self._camera_widget)
        self._camera_widget = None

    def retranslate(self):
        if not hasattr(self, "title"):
            return
        self.title.text = tr("camera.title", n=self._n())
        if self._profile:
            kind = self._profile.kind
            name = 'dinosaur' if kind == 'dino' and self._n() == 2 else 'lattice' if kind == 'dino' else kind
            self.title.text = tr('camera.shape_title', name=tr('directory.'+name), n=self._n())
        self.tip.text = tr("camera.tip")
        self.edit_tip.text = tr("camera.edit_tip")
        if self._profile:
            self.edit_tip.text = tr('camera.surface_tip')
        self.btn_rotate.text = tr("camera.rotate")
        self.btn_recheck.text = tr("camera.recheck")
        self.btn_calibrate.text = tr('camera.calibrate')
        self.btn_reset_calibration.text = tr("camera.reset_calibration")
        self.scan_cancel.text = tr("camera.cancel_scan")
        self._update_face_ui()

    def refresh_theme(self):
        self.tip.color = _app().theme.text_muted
        self.msg.color = _app().theme.text_muted
        if hasattr(self, "guide"):
            self.guide._redraw()

    def _reset_for_n(self, n):
        self._cancel_turn()
        self._release_source()
        self.preview.clear_widgets()
        self.preview.add_widget(self.guide)
        self._preview_image = None
        self._source_image = None
        self._parked_quad = self._parked_face = self._parked_digest = None
        kind = getattr(_app(), 'puzzle_kind', 'cube')
        self._profile = None
        if kind != 'cube':
            from app.prefs import get as pref_get
            palette = pref_get(('shape_palette_' if kind == 'pandora' else 'poly_palette_')+kind, None)
            if not (isinstance(palette, list) and palette and all(
                    isinstance(c, list) and len(c) == 4 and all(isinstance(v, (float, int)) and 0 <= v <= 1 for v in c)
                    for c in palette)):
                palette = None
            self._profile = ScanProfile(kind, n)
            if palette and len(palette) == len(self._profile.palette):
                self._profile.palette = tuple(tuple(c) for c in palette)
        self.grid_box.remove_widget(self.grid)
        if self._profile:
            from ui.widgets.scan_surface import ScanSurfaceView
            self.grid = ScanSurfaceView(size_hint=(None, None), size=(m.h(108), m.h(108)))
            self._ori = self._profile.new_orientation()
            self._data = self._profile.from_cube(_app().cube, getattr(_app(), 'camera_recorded', None))
        else:
            self.grid = ScanCubeView(size_hint=(None, None), size=(m.h(108), m.h(108)))
            self._ori = CubeOrientation(n)
            self._data = {}
        self.grid.on_cell = self.edit_cell
        self.grid_box.add_widget(self.grid, index=len(self.grid_box.children))
        self._color_samples = {}
        self._standard_params = replace(VISION_DEFAULT)
        self._standard_palette = tuple(COLOR_INFO[c][1] for c in COLOR_CODES)
        self._calibrated_codes = set()
        self._manual_cells = set()
        self._calibration_slot = None
        self.guide.set_template()
        self.guide.editable = False
        self.guide.set_image(None)
        self.btn_rotate.disabled = self.btn_recheck.disabled = self.btn_calibrate.disabled = True
        self.btn_calibrate.opacity = 1
        self.btn_calibrate.size_hint_x = 1
        self._load_calibration()
        self._update_face_ui()

    # ---- 取帧来源 ----
    def _ensure_source(self):
        if not self._active or self._suspended or self._picker_pending:
            return
        from kivy.utils import platform
        from kivy.clock import Clock
        if platform == "android":
            from android.permissions import Permission, check_permission, request_permissions
            if not check_permission(Permission.CAMERA):
                self.msg.text = tr("camera.permission")
                self.btn_capture.disabled = True
                if not self._permission_pending:
                    self._permission_pending = True
                    def granted(_permissions, grants):
                        def resume(_dt):
                            self._permission_pending = False
                            if self._active and grants and all(grants):
                                self._ensure_source()
                        Clock.schedule_once(resume, 0)
                    request_permissions([Permission.CAMERA], granted)
                return
        if self._session is None and platform != "android" and cv2_available():
            self._session = Cv2CameraSession(0)
            if not self._session.is_available():
                self._session.release()
                self._session = None
        if self._session is None:
            cam = make_kivy_camera_widget()
            if cam is not None:
                self._camera_widget = cam
                self._session = KivyCameraSession(cam)
                self._add_camera(cam)
        if self._preview_event is None and self._session is not None:
            self._preview_event = Clock.schedule_interval(self._poll_preview, 1/12)
        self.btn_capture.disabled = self._session is None
        if self._source_image is not None:
            self._set_preview(self._source_image)
        elif self._session is None:
            self.msg.text = tr("camera.no_camera")

    def _camera_angle(self):
        from kivy.utils import platform
        if platform != "android":
            return 0
        try:
            from jnius import autoclass
            if self._sensor_info is None:
                Camera = autoclass('android.hardware.Camera')
                info = autoclass('android.hardware.Camera$CameraInfo')()
                Camera.getCameraInfo(int(self._camera_widget.index), info)
                self._sensor_info = (int(info.orientation), int(info.facing))
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            rotation = int(activity.getWindowManager().getDefaultDisplay().getRotation())*90
            sensor, facing = self._sensor_info
            return -((sensor+rotation) % 360) if facing == 1 else -((sensor-rotation) % 360)
        except Exception:
            return -90

    def _add_camera(self, cam):
        """相机先按传感器比例放大，再整体旋转，框与实际可见区域共用尺寸。"""
        from kivy.graphics import PopMatrix, PushMatrix, Rotate
        cam.size_hint = (None, None)
        cam.fit_mode = "contain"
        with cam.canvas.before:
            PushMatrix()
            self._cam_rot = Rotate(angle=0)
        with cam.canvas.after:
            PopMatrix()
        self.preview.add_widget(cam, index=len(self.preview.children))
        self._sensor_info = None
        if not getattr(self, "_cam_bound", False):
            self.preview.bind(pos=self._layout_camera, size=self._layout_camera)
            self._cam_bound = True
        self._layout_camera()

    def _layout_camera(self, *args):
        cam = self._camera_widget
        if cam is None or self._source_image is not None:
            return
        tex = getattr(cam, "texture", None)
        if tex is None or not tex.width or not tex.height:
            return
        angle = self._camera_angle()
        k = round(angle/90) % 4
        tw, th = tex.size
        rw, rh = (th, tw) if k % 2 else (tw, th)
        pw, ph = self.preview.size
        if min(pw, ph) <= 0:
            return
        scale = min(pw/rw, ph/rh)
        # contain 允许把 640×480 纹理放大到控件大小，避免预览小于取景框。
        cam.size = (tw*scale, th*scale)
        cx, cy = self.preview.x+pw/2, self.preview.y+ph/2
        cam.pos = (cx-cam.width/2, cy-cam.height/2)
        self._cam_rot.origin = (cx, cy)
        self._cam_rot.angle = angle
        if self.guide.image_size != (rw, rh):
            self.guide.set_image((rw, rh))
        self.guide._redraw()

    def _orient_frame(self, img):
        if img is None or self._camera_widget is None:
            return img
        k = round(self._camera_angle()/90) % 4
        return np.ascontiguousarray(np.rot90(img, k)) if k else img

    def _poll_preview(self, _dt):
        if self._session is None:
            return
        ready = self._session.is_available()
        self.btn_capture.disabled = not ready or self._turning or self._recognizing
        if self._camera_widget is not None:
            self._camera_widget.opacity = 0 if self._source_image is not None else 1
            if ready and self._source_image is None:
                if self._preview_image is not None:
                    self._preview_image.opacity = 0
                self._layout_camera()
            return
        frame = self._session.grab()
        if frame is not None and self._source_image is None:
            self._set_preview(frame)

    def _set_preview(self, rgb):
        from kivy.graphics.texture import Texture
        if self._preview_image is None:
            from kivy.uix.image import Image as KvImage
            self._preview_image = KvImage(fit_mode="contain",
                                          size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
            self.preview.add_widget(self._preview_image)
            self.preview.remove_widget(self.guide)
            self.preview.add_widget(self.guide)
        if self._camera_widget is not None:
            self._camera_widget.opacity = 0
        h, w = rgb.shape[:2]
        # Only the displayed preview is bounded; recognition keeps original pixels.
        shown = rgb
        if max(w, h) > 1280:
            scale = 1280 / max(w, h)
            pw, ph = max(1, round(w*scale)), max(1, round(h*scale))
            xs = np.rint(np.linspace(0, w-1, pw)).astype(int)
            ys = np.rint(np.linspace(0, h-1, ph)).astype(int)
            shown = rgb[ys[:, None], xs[None, :]]
        tex = Texture.create(size=(shown.shape[1], shown.shape[0]), colorfmt="rgb")
        tex.blit_buffer(np.ascontiguousarray(shown).tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        tex.flip_vertical()
        self._preview_image.texture = tex
        self._preview_image.opacity = 1
        if self.guide.image_size != (w, h):
            self.guide.set_image((w, h))
        self.guide._redraw()

    def _show_photo(self, img, search_quad=None):
        self._source_image = img
        self._photo_dirty = True
        self.guide.n = self._n()
        self.guide.set_image((img.shape[1], img.shape[0]))
        self.guide.editable = True
        self.btn_rotate.disabled = False
        self.btn_recheck.disabled = False
        self.btn_calibrate.disabled = False
        self._set_preview(img)
        self.btn_capture.disabled = False
        self._detect_into_current(img, search_quad=search_quad)

    def rotate_photo(self):
        if self._recognizing:
            return
        self._photo_dirty = True
        if self._source_image is not None:
            height = self._source_image.shape[0]
            quad = self.guide.image_quad()
            if self._profile:
                # Rotate the photograph under the upright model template.
                self._source_image = np.rot90(self._source_image, -1).copy()
                self._set_preview(self._source_image)
                self.guide.set_image((self._source_image.shape[1], self._source_image.shape[0]))
                self._detect_into_current(self._source_image)
                return
            rotated = np.column_stack((height-1-quad[:, 1], quad[:, 0]))[[3, 0, 1, 2]]
            self._source_image = np.rot90(self._source_image, -1).copy()
            self._set_preview(self._source_image)
            self._detect_into_current(self._source_image, quad=rotated)

    def recheck(self):
        if self._recognizing:
            return
        if self._source_image is not None:
            self._detect_into_current(self._source_image, quad=self.guide.image_quad())

    # ---- 面导航 ----
    def _resume_live(self):
        self._parked_quad = self._parked_face = self._parked_digest = None
        self._source_image = None
        self._calibration_slot = None
        self.guide.editable = False
        self.guide.set_image(self.guide.image_size)
        self.btn_rotate.disabled = self.btn_recheck.disabled = self.btn_calibrate.disabled = True
        if self._preview_image is not None:
            self._preview_image.opacity = 0
        if self._camera_widget is not None:
            self._camera_widget.opacity = 1
        if self._session is None:
            self._ensure_source()

    def navigate(self, direction):
        if self._turning or self._recognizing or self._picker_pending:
            return
        previous = direction == "prev"
        d = self._ori.prev_dir() if previous else self._ori.next_dir()
        target = self._ori.prev_face() if previous else self._ori.next_face()
        angle, axis = self._ori.prev_axis_deg() if previous else self._ori.next_axis_deg()
        self.msg.text = (tr('camera.surface_turn', face=self._face_name(target)) if self._profile and not self._profile.cubic
                         else tr("camera.rot_hint", dir=tr("camera.dir."+d), face=tr("face."+target)))
        self.msg.color = _app().theme.accent
        self._set_turning(True)
        def finished():
            if not self._turning:
                return
            if previous:
                self._ori.turn_prev()
            else:
                self._ori.turn_next()
            self._set_turning(False)
            self._resume_live()
            self._update_face_ui()
        self.grid.animate_whole_turn(axis, angle, .65, on_done=finished)

    def _update_face_ui(self):
        face = self._ori.current_face()
        if self._profile:
            done = sum(self._profile.complete(self._data, f) for f in self._profile.face_keys)
            self.face_label.text = tr('camera.surface_progress', face=self._face_name(face), done=done, total=len(self._profile.face_keys))
            self.grid.set_scan(self._profile, self._data, self._ori.world, face)
            controls, templates = self._profile.templates(face, self._ori.world)
            self.guide.set_template(controls, [p for _, p, _, _ in templates], self._profile.face_aspect(face, self._ori.world))
            return
        done = sum(1 for g in self._data.values() if len(g) == self._n() and all(c for row in g for c in row))
        self.face_label.text = tr("camera.face_progress", face=tr("face." + face),
                                  code=face, done=done)
        self.grid.set_faces(self._data, self._n(), self._ori.world, face)
        self.guide.n = self._n()
        self.guide._redraw()

    def _face_name(self, face):
        return tr('face.'+face) if not self._profile or self._profile.cubic else tr('camera.face_number', number=face)

    # ---- 采集 ----
    def capture(self):
        if self._turning or self._recognizing or self._picker_pending:
            return
        if self._source_image is not None:
            self._resume_live()
            self.msg.text = tr("camera.tip")
            self.msg.color = _app().theme.text_muted
            return
        if self._session is None or not self._session.is_available():
            self.msg.text = tr("camera.no_camera")
            return
        img = self._orient_frame(self._session.grab())
        if img is None:
            self.msg.text = tr("camera.no_image")
            return
        # 拍照时优先在屏幕取景框附近找面，导入整张截图时则自动定位整张图。
        q = self.guide.quad * np.array([img.shape[1]-1, img.shape[0]-1])
        self._show_photo(img, search_quad=q)

    def open_import(self):
        if self._turning or self._recognizing or self._picker_pending:
            return
        from kivy.utils import platform
        if platform == "android":
            import os
            from vision.android_picker import AndroidPhotoPicker
            self._picker_pending = True
            self._release_source()
            cube, face = self._cube_for_screen, self._ori.current_face()
            def selected(path, error):
                self._picker_pending = False
                self._photo_picker = None
                if not self._active or cube is not self._cube_for_screen or face != self._ori.current_face():
                    return
                if path:
                    self.load_image(path)
                else:
                    if error:
                        self.msg.text = tr("camera.import_failed")
                        self.msg.color = _app().theme.danger
                        from kivy.logger import Logger
                        Logger.warning("PhotoPicker: %s", error)
                    if not self._suspended and self._source_image is None:
                        self._ensure_source()
            self._photo_picker = AndroidPhotoPicker(os.path.join(_app().user_data_dir, "photo-cache"), selected)
            try:
                self._photo_picker.open()
            except Exception as exc:
                selected(None, str(exc))
            return
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        content = BoxLayout(orientation="vertical", spacing=8, padding=8)
        chooser = FileChooserListView(path=_default_dir(),
                                      filters=["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.PNG", "*.JPG", "*.JPEG"])
        content.add_widget(chooser)
        btns = BoxLayout(size_hint_y=None, height=m.h(48), spacing=8)
        cancel = UIButton(text="", icon_name="cancel")
        ok = PrimaryButton(text="", icon_name="done")
        btns.add_widget(cancel)
        btns.add_widget(ok)
        content.add_widget(btns)
        from ui.widgets.dialogs import theme_popup
        popup = Popup(title=tr("camera.pick_file"), content=content, size_hint=(0.9, 0.8))
        theme_popup(popup, _app().theme)
        cancel.bind(on_release=lambda *a: popup.dismiss())

        def _choose(*_a):
            sel = chooser.selection
            if not sel:
                return
            popup.dismiss()
            self.load_image(sel[0])
        ok.bind(on_release=_choose)
        popup.open()

    def load_image(self, path):
        img = load_image_file_rgb(path)
        if img is None:
            self.msg.text = tr("camera.no_image")
            return
        self._show_photo(img)

    def _set_recognizing(self, busy):
        if busy == self._recognizing:
            return
        self._recognizing = busy
        self.scan_progress_row.height = m.h(30) if busy else 0
        self.scan_progress_row.opacity = 1 if busy else 0
        self.scan_cancel.disabled = not busy
        self.btn_reset_calibration.disabled = busy
        if busy:
            self.scan_progress.value = 0
            self._scan_editable = self.guide.editable
            self.guide.editable = False
            buttons = (self.btn_prev, self.btn_next, self.btn_capture, self.btn_import,
                       self.btn_apply, self.btn_rotate, self.btn_recheck, self.btn_calibrate)
            self._scan_buttons = {button: button.disabled for button in buttons}
            for button in buttons:
                button.disabled = True
        else:
            self.guide.editable = getattr(self, '_scan_editable', False)
            for button, disabled in getattr(self, '_scan_buttons', {}).items():
                button.disabled = disabled
            self._scan_buttons = {}

    def _start_recognition(self, compute, apply):
        if self._recognizing:
            return
        from kivy.clock import Clock
        job = self._scan_job = object()
        self._set_recognizing(True)
        self.msg.text = tr('camera.processing')
        self.msg.color = _app().theme.accent
        def finish(result, error):
            if self._scan_job is not job or not self._active:
                return
            self._scan_job = None
            self._set_recognizing(False)
            if error is not None:
                self.msg.text = tr('camera.processing_failed')
                self.msg.color = _app().theme.danger
                return
            apply(result)
        def report(stage, done, total):
            if self._scan_job is not job:
                raise InterruptedError()
            def update(_dt):
                if self._scan_job is job:
                    self.msg.text = tr(stage)+" "+str(done)+"/"+str(total)
                    self.scan_progress.value = max(0, min(1, done/max(1,total)))
            Clock.schedule_once(update, 0)
        def worker():
            started = perf_counter()
            try:
                result = compute(report)
            except InterruptedError:
                return
            except Exception as exc:
                from kivy.logger import Logger
                Logger.exception('PhotoScan: recognition failed')
                Clock.schedule_once(lambda dt, error=str(exc): finish(None, error), 0)
            else:
                Clock.schedule_once(lambda dt: finish(result, None), 0)
            finally:
                from kivy.logger import Logger
                Logger.info('PhotoScan: recognition %.0f ms', (perf_counter()-started)*1000)
        # Give the processing message a frame before starting CPU work.
        def start(_dt):
            if self._scan_job is job and self._active:
                threading.Thread(target=worker, daemon=True).start()
        Clock.schedule_once(start, 0)

    def _detect_into_current(self, img, quad=None, search_quad=None):
        if self._recognizing:
            return
        profile, face, world = self._profile, self._ori.current_face(), self._ori.world
        n = self._n()
        params, orientation = self._standard_params, None if profile else deepcopy(self._ori)
        self._calibration_slot = None
        def compute(progress):
            if profile:
                controls = quad if quad is not None else search_quad
                det = detect_surface(img, profile, face, world, controls=controls, progress=progress)
                return det
            if search_quad is not None:
                q = np.asarray(search_quad)
                pad = .12 * max(np.ptp(q[:, 0]), np.ptp(q[:, 1]))
                x0, y0 = np.maximum(0, np.floor(q.min(axis=0)-pad)).astype(int)
                x1, y1 = np.minimum([img.shape[1], img.shape[0]], np.ceil(q.max(axis=0)+pad+1)).astype(int)
                det = detect_face_grid(img[y0:y1, x0:x1], n, params=params, progress=progress)
                if det.image_quad is not None:
                    det.image_quad = (np.asarray(det.image_quad)+[x0, y0]).tolist()
            else:
                det = detect_face_grid(img, n, params=params, quad=quad, progress=progress)
            return det
        def apply(det):
            if det.samples is not None:
                self._color_samples[face] = (det.samples, orientation)
            if profile:
                previous = self._data.get(face, {})
                if det.samples is not None:
                    self._data[face] = {i: previous.get(i, v) if (face,i) in self._manual_cells else v for i,v in det.values.items()}
                if det.image_quad is not None:
                    self.guide.set_image((img.shape[1], img.shape[0]), det.image_quad)

                self.msg.text = (tr('camera.detected', face=self._face_name(face)) if det.ok else
                                 tr('camera.detect_failed', reason=tr('camera.surface_partial')))
            else:
                view_grid = det.grid() if det.cells else empty_grid(n)
                if det.cells:
                    grid = orient_grid(view_grid, orientation)
                    previous = self._data.get(face, empty_grid(n))
                    self._data[face] = [[previous[r][c] if (face,r,c) in self._manual_cells else grid[r][c]
                                        for c in range(n)] for r in range(n)]
                if det.image_quad is not None:
                    self.guide.set_image((img.shape[1], img.shape[0]), det.image_quad)
                reason = tr('camera.reason.partial' if det.cells else 'camera.reason.adjust')
                self.msg.text = (tr('camera.detected', face=tr('face.'+face)) if det.ok else
                                 tr('camera.detect_failed', reason=reason))
            self._update_face_ui()
            self._show_uncertain(det.ok)
            self.msg.color = _app().theme.accent if det.ok else _app().theme.danger
        self._start_recognition(compute, apply)

    def edit_cell(self, r, c):
        if self._turning or self._recognizing:
            return
        if self._profile:
            face = self._ori.current_face()
            def choose(value):
                if face != self._ori.current_face():
                    return
                self._data[face][r] = value
                self._manual_cells.add((face, r))
                self._update_face_ui()
                self.msg.text = tr('camera.corrected')
                self._show_uncertain(True)
                self.msg.color = _app().theme.accent
            self._palette_popup(tr('camera.edit_color'), choose, allow_unknown=True)
            return
        from kivy.uix.button import Button
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        choices = GridLayout(cols=3, spacing=m.h(8), padding=m.h(8))
        popup = Popup(title=tr("camera.edit_color"), content=choices, size_hint=(.85, .45))
        theme_popup(popup, _app().theme)
        face = self._ori.current_face()
        orientation = self._ori.world
        def choose(code):
            # 在照片坐标改色，再转换为求解器使用的固定面坐标。
            if self._ori.current_face() != face or self._ori.world is not orientation:
                popup.dismiss()
                return
            grid = [row[:] for row in self._data.get(face, empty_grid(self._n()))]
            grid[r][c] = code
            self._manual_cells.add((face, r, c))
            self._data[face] = grid
            self._update_face_ui()
            complete = all(value for row in grid for value in row)
            self.msg.text = tr("camera.corrected" if complete else "camera.reason.partial")
            self.msg.color = _app().theme.accent if complete else _app().theme.text_muted
            self._show_uncertain(True)
            popup.dismiss()
        for code in ("W", "Y", "R", "O", "B", "G"):
            rgba = COLOR_INFO[code][1]
            light = sum(rgba[:3]) > 1.7
            button = Button(text=code, background_normal="", background_color=rgba,
                            color=(0, 0, 0, 1) if light else (1, 1, 1, 1), font_size="20sp")
            button.bind(on_release=lambda _, value=code: choose(value))
            choices.add_widget(button)
        popup.open()

    def _palette_popup(self, title, callback, allow_unknown=False, indices=None):
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.popup import Popup
        from ui.widgets.dialogs import theme_popup
        palette = self._profile.palette if self._profile else self._standard_palette
        choices = GridLayout(cols=4 if len(palette)>8 else 3, spacing=m.h(8),
                             padding=m.h(8), size_hint_y=None)
        choices.bind(minimum_height=choices.setter('height'))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(choices)
        content = BoxLayout(orientation='vertical', spacing=m.h(8), padding=m.h(6))
        hint = Label(text=tr('camera.palette_hint'), size_hint_y=None, height=m.h(42),
                     font_size='14sp', halign='center', valign='middle')
        hint.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        content.add_widget(hint)
        content.add_widget(scroll)
        popup = Popup(title=title, content=content, size_hint=(.9, .7))
        theme_popup(popup, _app().theme)
        def selected(value):
            popup.dismiss()
            callback(value)
        for i, rgba in enumerate(palette):
            if indices is not None and i not in indices:
                continue
            label = tr("camera.color_number", number=i+1) if self._profile else tr("camera.color_" + COLOR_CODES[i])
            button = _CalibrationSwatch(rgba, text=label, size_hint_y=None, height=m.h(64),
                                        font_size="18sp")
            button.bind(on_release=lambda _, value=i: selected(value))
            choices.add_widget(button)
        if allow_unknown:
            unknown = UIButton(text='?', size_hint_y=None, height=m.h(52))
            unknown.bind(on_release=lambda *_: selected(-1))
            choices.add_widget(unknown)
        popup.open()

    def calibrate(self):
        if self._recognizing:
            return
        if self._source_image is None or self._turning:
            return
        def selected(index):
            self._calibration_slot = index
            self.msg.text = (tr('camera.sample_prompt', number=index+1) if self._profile else
                             tr('camera.sample_color_prompt', color=tr('camera.color_' + COLOR_CODES[index])))
            self.msg.color = _app().theme.accent
        self._palette_popup(tr('camera.calibrate_choose'), selected)

    def sample_color(self, x, y):
        if self._recognizing or self._calibration_slot is None or self._source_image is None:
            return False
        x, y = int(round(x)), int(round(y))
        img = self._source_image
        rgb = np.median(img[max(0,y-3):y+4, max(0,x-3):x+4].reshape(-1,3), axis=0)
        if max(rgb) < 60:
            self.msg.text = tr('camera.sample_dark')
            return True
        if self._profile is None:
            return self._sample_standard_color(x, y)
        palette = list(self._profile.palette)
        palette[self._calibration_slot] = tuple(rgb/255)+(1,)
        self._profile.palette = tuple(palette)
        self._save_calibration()
        self._calibration_slot = None
        self._reclassify_samples()
        return True

    def _sample_standard_color(self, x, y):
        img = self._source_image
        patch = img[max(0,y-3):y+4, max(0,x-3):x+4]
        _, sat, val = rgb_to_hsv(patch)
        code = COLOR_CODES[self._calibration_slot]
        usable = (val >= VISION_DEFAULT.val_min)
        usable &= sat <= 120 if code == 'W' else sat >= 70
        if np.count_nonzero(usable) < max(1, sat.size*.6):
            self.msg.text = tr('camera.calibration_retry')
            self.msg.color = _app().theme.danger
            return True
        rgb = np.median(patch[usable], axis=0)/255
        palette = list(self._standard_palette)
        palette[self._calibration_slot] = tuple(rgb)+(1,)
        hsv = rgb_to_hsv(np.array(palette)[:, :3])
        refs = tuple(tuple(float(channel[i]) for channel in hsv) for i in range(len(COLOR_CODES)))
        calibrated = self._calibrated_codes | {code}
        # Reject indistinguishable learned color anchors; avoid forcing a wrong label.
        for i, first in enumerate(COLOR_CODES[1:], 1):
            for j in range(i+1, len(COLOR_CODES)):
                if first in calibrated and COLOR_CODES[j] in calibrated:
                    dh = abs(refs[i][0]-refs[j][0])
                    if min(dh, 180-dh) < 4:
                        self.msg.text = tr('camera.calibration_retry')
                        self.msg.color = _app().theme.danger
                        return True
        self._standard_palette = tuple(palette)
        self._calibrated_codes = calibrated
        self._calibration_slot = None
        params = replace(self._standard_params, color_reference_hsv=refs)
        self._standard_params = params
        self._save_calibration()
        self._reclassify_samples()
        return True

    def _reclassify_samples(self):
        samples, profile, params, n = tuple(self._color_samples.items()), self._profile, self._standard_params, self._n()
        if not samples:
            if self._source_image is not None: self.recheck()
            return
        def compute(progress):
            results = {}
            for index, (face, (pixels, ori)) in enumerate(samples):
                progress('camera.recalibrating', index, len(samples))
                if profile:
                    results[face] = {key: _read_color(rgb, profile.palette) for key,rgb in pixels.items()}
                else:
                    grid = [[_cell_color(*pixels[r,c], params) or '' for c in range(n)] for r in range(n)]
                    results[face] = orient_grid(grid, ori)
            return results
        def apply(results):
            for face, values in results.items():
                if profile:
                    for index, color in values.items():
                        if (face,index) not in self._manual_cells: self._data[face][index] = color
                else:
                    previous = self._data.get(face, empty_grid(n))
                    self._data[face] = [[previous[r][c] if (face,r,c) in self._manual_cells else values[r][c]
                                         for c in range(n)] for r in range(n)]
            self._update_face_ui()
            self.msg.text = tr('camera.calibrated')
            self._show_uncertain(True)
            self.msg.color = _app().theme.accent
        self._start_recognition(compute, apply)

    def _park_photo(self, drop=False):
        img = self._source_image
        if img is None: return
        try:
            import os
            if self._photo_dirty or not os.path.isfile(self._parked_image_path):
                h,w = img.shape[:2]
                scale = min(1.,1280/max(h,w))
                xs = np.rint(np.linspace(0,w-1,max(1,round(w*scale)))).astype(int)
                ys = np.rint(np.linspace(0,h-1,max(1,round(h*scale)))).astype(int)
                photo = np.ascontiguousarray(img[ys[:,None],xs[None,:]])
                with open(self._parked_image_path+'.tmp','wb') as stream:
                    np.save(stream,photo,allow_pickle=False)
                os.replace(self._parked_image_path+'.tmp',self._parked_image_path)
                import hashlib
                self._parked_digest = hashlib.sha256(photo).hexdigest()
                self._photo_dirty = False
            self._parked_quad = self.guide.quad.tolist()
            self._parked_face = self._ori.current_face()
            if drop:
                self._source_image = None
                if self._preview_image is not None:
                    self._preview_image.texture = None
        except Exception:
            from kivy.logger import Logger
            Logger.exception('PhotoScan: could not park photograph')

    def _restore_parked_photo(self):
        if self._source_image is not None or self._parked_quad is None or self._parked_face != self._ori.current_face():
            return
        try:
            img = np.load(self._parked_image_path,allow_pickle=False)
            if img.dtype != np.uint8 or img.ndim != 3 or img.shape[2] != 3 or max(img.shape[:2])>1280:
                raise ValueError('Invalid parked photograph')
            import hashlib
            if self._parked_digest and hashlib.sha256(np.ascontiguousarray(img)).hexdigest()!=self._parked_digest:
                raise ValueError('Photograph does not match checkpoint')
            self._release_source()
            self._source_image = img
            self._set_preview(img)
            quad = np.asarray(self._parked_quad)*[img.shape[1]-1,img.shape[0]-1]
            self.guide.set_image((img.shape[1],img.shape[0]),quad)
            self.guide.editable = True
            self.btn_rotate.disabled = self.btn_recheck.disabled = self.btn_calibrate.disabled = False
            self.btn_capture.disabled = False
        except Exception:
            self._parked_quad = self._parked_face = self._parked_digest = None
            from kivy.logger import Logger
            Logger.exception('PhotoScan: could not restore photograph')

    def _calibration_key(self):
        return 'photo_calibration_'+(self._profile.kind if self._profile else 'cube')

    def _save_calibration(self):
        from app.prefs import set as save_pref
        palette = self._profile.palette if self._profile else self._standard_palette
        save_pref(self._calibration_key(), {'palette': [list(c) for c in palette],
                  'codes': sorted(self._calibrated_codes) if not self._profile else []})

    def _load_calibration(self):
        from app.prefs import get
        saved = get(self._calibration_key(), {})
        if not isinstance(saved, dict): return
        palette = saved.get('palette')
        size = len(self._profile.palette) if self._profile else 6
        if not (isinstance(palette,list) and len(palette)==size and all(isinstance(c,list) and len(c)==4 and
                all(isinstance(v,(int,float)) and 0<=v<=1 for v in c) for c in palette)):
            return
        if self._profile:
            self._profile.palette = tuple(tuple(c) for c in palette)
        else:
            self._standard_palette = tuple(tuple(c) for c in palette)
            self._calibrated_codes = set(saved.get('codes', [])) & set(COLOR_CODES)
            hsv = rgb_to_hsv(np.asarray(palette)[:,:3])
            refs = tuple(tuple(float(channel[i]) for channel in hsv) for i in range(6))
            if self._calibrated_codes:
                self._standard_params = replace(VISION_DEFAULT, color_reference_hsv=refs)

    def reset_calibration(self):
        if self._recognizing or self._turning: return
        from app.prefs import set as save_pref
        save_pref(self._calibration_key(), {})
        if self._profile:
            self._profile.palette = ScanProfile(self._profile.kind, self._n()).palette
        else:
            self._standard_palette = tuple(COLOR_INFO[c][1] for c in COLOR_CODES)
            self._calibrated_codes = set()
            self._standard_params = replace(VISION_DEFAULT)
        self._calibration_slot = None
        if self._color_samples: self._reclassify_samples()
        elif self._source_image is not None: self.recheck()
        else: self.msg.text = tr('camera.calibration_reset')

    def cancel_recognition(self):
        self._scan_job = None
        self._set_recognizing(False)
        self.msg.text = tr('camera.scan_cancelled')

    def _show_uncertain(self, success=False):
        face = self._ori.current_face()
        if self._profile:
            count = sum(c<0 for c in self._data.get(face, {}).values())
        else:
            count = sum(not c for row in self._data.get(face, empty_grid(self._n())) for c in row)
        if count:
            self.msg.text = tr('camera.uncertain', count=count)
        elif not success:
            self.msg.text = tr('camera.processing_failed')

    # ---- 应用 ----
    def apply_to_input(self):
        if self._recognizing:
            return
        if self._profile:
            app = _app()
            try:
                cube = self._profile.apply(self._data, app.cube)
            except ValueError as exc:
                self.msg.text = tr(str(exc)) if str(exc).startswith('camera.') else tr('camera.invalid_input')
                self.msg.color = app.theme.danger
                return
            app.cube = cube
            self._cube_for_screen = cube
            app.input_from_camera = True
            app.polyhedral_solution = None
            app.solve_result = None
            if self._profile.kind == 'pandora':
                from cube.pandora_entry import to_facelets
                app.camera_shape_result = None
                app.facelets_input=to_facelets(cube)
                target = 'InputScreen'
            else:
                target = 'PolyhedralScreen'
            self.msg.text = tr('camera.applied')
            self.manager.current = target
            return
        n = self._n()
        facelets = assemble_facelets(
            {f: g for f, g in self._data.items() if g}, n)
        app = _app()
        app.facelets_input = facelets
        app.input_from_camera = True
        self.msg.text = tr("camera.applied")
        self.manager.current = "InputScreen"

    def go_back(self):
        _app().input_from_camera = False
        self.manager.current = getattr(_app(), 'camera_return_screen', 'HomeScreen')

    def _n(self):
        return _app().n


def _default_dir():
    import os
    for base in (os.path.expanduser("~"), os.getcwd()):
        if os.path.isdir(base):
            return base
    return "."


def _app():
    from kivy.app import App
    return App.get_running_app()
