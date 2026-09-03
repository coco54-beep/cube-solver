"""CubeView：基于 Kivy 图形指令渲染 3D 魔方。

主要特性：
- 顶点由 renderer.scene.build_scene() 生成。
- 使用相机基向量手动完成透视投影，避免矩阵乘法顺序造成变形。
- 使用统一的 X/Y 像素缩放，保证三阶、四阶魔方均保持正确立方体比例。
- 使用 Color + Triangle 绘制四边形。
- 使用相机空间深度执行画家算法排序。
- 拖拽旋转视角，滚轮缩放。
- 支持单层转动动画。
"""

import math

from kivy.clock import Clock
from kivy.graphics import Color, InstructionGroup, Line, Triangle
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from renderer import scene as scene_mod
from renderer.geometry import OrbitCamera
from renderer.mat4 import Mat4


_EPSILON = 1e-8


class CubeView(Widget):
	"""3D 魔方视图组件。"""

	cube = ObjectProperty(None, allownone=True)

	def __init__(self, **kwargs):
		# 渲染外形："cube"（标准立方体）或 "mastermorphix"（粽子/四角锥）。
		self.kind = kwargs.pop("kind", "cube")
		super().__init__(**kwargs)

		self.camera = OrbitCamera()

		# 当前层转动动画信息
		self._anim = None
		self._anim_event = None

		# 当前拖拽触摸
		self._touch0 = None
		self._touch0_pos = None

		# 屏幕显示缩放。
		# 不直接依赖 camera.zoom()，避免自适应取景抵消相机缩放。
		self._display_zoom = 1.0

		# 使用独立指令组，只清除魔方网格，
		# 不会误删该 Widget 在 KV 中定义的背景等其他 canvas 指令。
		self._mesh_group = InstructionGroup()
		self.canvas.add(self._mesh_group)

		self.bind(
			pos=self._redraw,
			size=self._redraw,
		)

	# ------------------------------------------------------------------
	# 状态设置
	# ------------------------------------------------------------------

	def set_cube(self, cube, highlight=None):
		"""设置需要显示的魔方逻辑对象。

		highlight: 若给定（可迭代的 cubie.home 集合），只对这些身份标记的块
		显示真实颜色（并按身份跟踪，转动中持续高亮同一批块）；其余块淡化，
		中心块始终保留颜色作方向参照。
		"""
		self._cancel_animation()
		self.cube = cube
		self._highlight = highlight
		self._redraw()

	def reset_camera(self):
		"""把相机视角还原到默认（仰角/方位角/距离/缩放）。"""
		self.camera.elevation = 22.0
		self.camera.azimuth = 35.0
		self.camera.distance = 9.0
		self.camera.target = (0, 0, 0)
		self._display_zoom = 1.0
		self._redraw()

	# ------------------------------------------------------------------
	# 绘制
	# ------------------------------------------------------------------

	def _redraw(self, *args):
		"""重新绘制魔方。"""
		self._draw_mesh()

	def _draw_mesh(self):
		"""生成场景并绘制魔方网格。"""
		self._mesh_group.clear()

		if self.cube is None:
			return

		if self.width <= 1 or self.height <= 1:
			return

		moving_positions = None
		rotation = None

		if self._anim is not None:
			moving_positions = self._anim["positions"]
			rotation = _rotation_matrix_for(self._anim)

		# vertices：
		# 每7个浮点表示一个顶点：
		# x, y, z, r, g, b, a
		#
		# build_scene 应保证每4个连续顶点表示一个四边形。
		vertices, _indices = scene_mod.build_scene(
			self.cube,
			moving_positions=moving_positions,
			rotation=rotation,
			highlight=getattr(self, "_highlight", None),
			kind=self.kind,
		)

		if not vertices:
			return

		if len(vertices) < 28:
			return

		# --------------------------------------------------------------
		# 使用未执行层转动的模型计算包围盒。
		#
		# 如果直接使用动画中的顶点计算包围盒，转动过程中模型包围盒
		# 会发生变化，从而导致相机距离和画面缩放出现轻微抖动。
		# --------------------------------------------------------------
		if self._anim is not None:
			reference_vertices, _reference_indices = scene_mod.build_scene(
				self.cube,
				moving_positions=None,
				rotation=None,
				highlight=getattr(self, "_highlight", None),
				kind=self.kind,
			)
		else:
			reference_vertices = vertices

		bounds = _get_vertex_bounds(reference_vertices)

		if bounds is None:
			return

		model_center, model_size, axis_sizes = bounds

		if model_size <= _EPSILON:
			return

		size_x, size_y, size_z = axis_sizes

		# 正常魔方在 X、Y、Z 三个方向上的尺寸应该基本相同。
		#
		# 如果这里输出警告，说明问题来自 build_scene() 的几何坐标，
		# 而不是投影或 Widget 的宽高比。
		size_difference = max(axis_sizes) - min(axis_sizes)

		if size_difference > model_size * 0.01:
			print(
				"警告：魔方模型三轴尺寸不一致："
				f"x={size_x:.4f}, "
				f"y={size_y:.4f}, "
				f"z={size_z:.4f}"
			)

		# --------------------------------------------------------------
		# 构造相机坐标系。
		# --------------------------------------------------------------
		camera_basis = self._get_camera_basis()

		if camera_basis is None:
			return

		original_eye, right, camera_up, forward = camera_basis

		# --------------------------------------------------------------
		# 根据模型尺寸调整相机距离。
		#
		# 四阶魔方的世界空间尺寸通常大于三阶魔方。如果继续使用
		# OrbitCamera 中固定的相机距离，四阶魔方会产生更强烈的
		# 近大远小效果，看起来容易不像正方体。
		#
		# camera_distance_factor 越大：
		#	 透视效果越弱，越接近正投影。
		#
		# camera_distance_factor 越小：
		#	 透视效果越强，近大远小越明显。
		# --------------------------------------------------------------
		camera_distance_factor = 3.5
		camera_distance = model_size * camera_distance_factor

		# 保留 OrbitCamera 当前观察方向，只把相机放置到距离
		# 模型中心合适的位置。
		eye = (
			model_center[0] - forward[0] * camera_distance,
			model_center[1] - forward[1] * camera_distance,
			model_center[2] - forward[2] * camera_distance,
		)

		# original_eye 当前不再直接参与投影，但保留变量便于调试。
		del original_eye

		# --------------------------------------------------------------
		# 将所有世界坐标转换到相机空间。
		#
		# camera_x：相机右方向
		# camera_y：相机上方向
		# camera_z：相机前方向；位于相机前方时为正数
		# --------------------------------------------------------------
		camera_vertices = []

		for index in range(0, len(vertices) - 6, 7):
			world_x = float(vertices[index])
			world_y = float(vertices[index + 1])
			world_z = float(vertices[index + 2])

			r = float(vertices[index + 3])
			g = float(vertices[index + 4])
			b = float(vertices[index + 5])
			a = float(vertices[index + 6])

			relative = (
				world_x - eye[0],
				world_y - eye[1],
				world_z - eye[2],
			)

			camera_x = _dot(relative, right)
			camera_y = _dot(relative, camera_up)
			camera_z = _dot(relative, forward)

			camera_vertices.append({
				"camera_x": camera_x,
				"camera_y": camera_y,
				"camera_z": camera_z,
				"color": (r, g, b, a),
			})

		# --------------------------------------------------------------
		# 手动执行透视除法。
		#
		# qx = camera_x / camera_z
		# qy = camera_y / camera_z
		#
		# X/Y 使用完全相同的 pixel_scale，防止因 Widget 的宽高比
		# 将魔方拉伸成长方体。
		# --------------------------------------------------------------
		projected_vertices = []

		for vertex in camera_vertices:
			camera_z = vertex["camera_z"]

			# 位于相机平面或者相机后方的点不能执行正常透视投影。
			if camera_z <= _EPSILON:
				projected_vertices.append(None)
				continue

			projected_vertices.append({
				"qx": vertex["camera_x"] / camera_z,
				"qy": vertex["camera_y"] / camera_z,
				"depth": camera_z,
				"color": vertex["color"],
			})

		valid_vertices = [
			vertex
			for vertex in projected_vertices
			if vertex is not None
		]

		if not valid_vertices:
			return

		# 取景参考：始终用“未执行转动动画”的静态模型顶点投影计算
		# 包围盒。这样转动动画过程中，画面缩放和中心保持稳定，
		# 不会随着层转动来回缩放。
		fit_points = _project_points_to_q(
			reference_vertices,
			eye,
			right,
			camera_up,
			forward,
		)

		if not fit_points:
			return

		fit_qx_values = [point[0] for point in fit_points]
		fit_qy_values = [point[1] for point in fit_points]

		min_qx = min(fit_qx_values)
		max_qx = max(fit_qx_values)
		min_qy = min(fit_qy_values)
		max_qy = max(fit_qy_values)

		span_x = max_qx - min_qx
		span_y = max_qy - min_qy

		# 使用 X/Y 中较大的跨度进行统一缩放。
		span = max(span_x, span_y, _EPSILON)

		# 投影包围盒中心。
		projected_center_x = (min_qx + max_qx) * 0.5
		projected_center_y = (min_qy + max_qy) * 0.5

		# 魔方默认占据 Widget 短边的约 88%。
		#
		# X/Y 必须共用同一个 pixel_scale，这是防止魔方被拉伸的关键。
		pixel_scale = (
				min(self.width, self.height)
				* 0.88
				/ span
				* self._display_zoom
		)

		# canvas 使用父级坐标，因此使用 Widget 的实际中心坐标。
		widget_center_x = self.center_x
		widget_center_y = self.center_y

		# --------------------------------------------------------------
		# 每4个连续顶点组成一个四边形。
		# --------------------------------------------------------------
		quads = []

		for index in range(0, len(projected_vertices) - 3, 4):
			group = projected_vertices[index:index + 4]

			if len(group) < 4:
				break

			# 任一顶点位于相机后方或相机平面上时，不绘制该面。
			if any(vertex is None for vertex in group):
				continue

			# camera_z 越大，表示沿相机前方向距离越远。
			# 使用四个顶点的平均相机深度执行画家算法排序。
			average_depth = sum(
				vertex["depth"]
				for vertex in group
			) / 4.0

			screen_group = []

			for vertex in group:
				screen_x = widget_center_x + (
						vertex["qx"] - projected_center_x
				) * pixel_scale

				screen_y = widget_center_y + (
						vertex["qy"] - projected_center_y
				) * pixel_scale

				screen_group.append({
					"x": screen_x,
					"y": screen_y,
					"color": vertex["color"],
				})

			quads.append((
				average_depth,
				screen_group,
			))

		# 远处的面先绘制，近处的面后绘制。
		quads.sort(
			key=lambda item: item[0],
			reverse=True,
		)

		line_width = max(
			1.0,
			1.5 * self._display_zoom,
		)

		# --------------------------------------------------------------
		# 绔制四边形。
		#
		# Kivy 没有直接使用四个点填充任意四边形，因此将每个面拆成：
		#
		# 三角形1：0、1、2
		# 三角形2：0、2、3
		# --------------------------------------------------------------
		for _depth, group in quads:
			color = group[0]["color"]

			self._mesh_group.add(
				Color(
					color[0],
					color[1],
					color[2],
					color[3],
				)
			)

			# 第一个三角形：0、1、2
			self._mesh_group.add(
				Triangle(
					points=[
						group[0]["x"],
						group[0]["y"],

						group[1]["x"],
						group[1]["y"],

						group[2]["x"],
						group[2]["y"],
					]
				)
			)

			# 第二个三角形：0、2、3
			self._mesh_group.add(
				Triangle(
					points=[
						group[0]["x"],
						group[0]["y"],

						group[2]["x"],
						group[2]["y"],

						group[3]["x"],
						group[3]["y"],
					]
				)
			)

			# 紧跟当前面绘制边线。
			#
			# 这样近处面的填充会覆盖远处面的边线，避免背面线框透出。
			self._mesh_group.add(
				Color(
					0.0,
					0.0,
					0.0,
					1.0,
				)
			)

			self._mesh_group.add(
				Line(
					points=[
						group[0]["x"],
						group[0]["y"],

						group[1]["x"],
						group[1]["y"],

						group[2]["x"],
						group[2]["y"],

						group[3]["x"],
						group[3]["y"],
					],
					close=True,
					width=line_width,
				)
			)

	def _get_camera_basis(self):
		"""根据 OrbitCamera 的 eye 和 target 构造相机坐标系。

		返回：
			eye, right, camera_up, forward

		其中：
		- forward：由相机指向目标
		- right：相机右方向
		- camera_up：相机上方向
		"""
		eye = tuple(float(value) for value in self.camera.eye)
		target = tuple(float(value) for value in self.camera.target)

		forward = _normalize((
			target[0] - eye[0],
			target[1] - eye[1],
			target[2] - eye[2],
		))

		if forward is None:
			return None

		# 一般以 Y 轴作为世界上方向。
		world_up = (0.0, 1.0, 0.0)

		# 当观察方向接近 Y 轴时，改用 Z 轴作为临时上方向，
		# 防止叉积接近零。
		if abs(_dot(forward, world_up)) > 0.999:
			world_up = (0.0, 0.0, 1.0)

		right = _normalize(_cross(forward, world_up))
		if right is None:
			return None

		camera_up = _normalize(_cross(right, forward))
		if camera_up is None:
			return None

		return eye, right, camera_up, forward

	# ------------------------------------------------------------------
	# 转动动画
	# ------------------------------------------------------------------

	def start_turn(
		self,
		axis,
		layer_pos,
		angle_deg,
		duration,
		on_done=None,
		layer_positions=None,
	):
		"""播放单层/多层转动动画。

		参数：
			axis: 0、1、2，对应 X、Y、Z 轴。
			layer_pos: 该轴上主层坐标（如 y=1）。
			angle_deg: 总转动角度（度）。
			duration: 动画持续时间（秒）。
			on_done: 动画完成回调（通常应修改逻辑状态）。
			layer_positions: 可选的层坐标列表（宽层转动时含内层）。
		"""
		if self.cube is None:
			return

		if axis not in (0, 1, 2):
			raise ValueError("axis 必须是 0、1 或 2")

		self._cancel_animation()

		if layer_positions is None:
			layer_positions = [layer_pos]
		positions = {
			position
			for position in self.cube.cubies
			if any(position[axis] == lp for lp in layer_positions)
		}

		self._anim = {
			"axis": axis,
			"layer_pos": layer_pos,
			"layer_positions": list(layer_positions),
			"positions": positions,
			"angle_total": float(angle_deg),
			"angle_current": 0.0,
			"duration": max(0.0, float(duration)),
			"elapsed": 0.0,
			"on_done": on_done,
		}

		if self._anim["duration"] <= 0.0:
			self._anim["angle_current"] = self._anim["angle_total"]
			self._draw_mesh()
			self._finish_turn()
			return

		self._anim_event = Clock.schedule_interval(
			self._anim_tick,
			0,
		)

	def _anim_tick(self, dt):
		"""更新动画帧。"""
		if self._anim is None:
			return False

		animation = self._anim
		animation["elapsed"] += max(0.0, dt)

		duration = max(animation["duration"], _EPSILON)
		t = min(1.0, animation["elapsed"] / duration)

		# 平滑缓入缓出。
		eased_t = t * t * (3.0 - 2.0 * t)

		animation["angle_current"] = (
			animation["angle_total"] * eased_t
		)

		self._draw_mesh()

		if t >= 1.0:
			self._finish_turn()
			return False

		return True

	def _finish_turn(self):
		"""结束当前动画并调用完成回调。"""
		animation = self._anim

		self._anim = None

		if self._anim_event is not None:
			self._anim_event.cancel()
			self._anim_event = None

		callback = None

		if animation is not None:
			callback = animation.get("on_done")

		# 先调用回调，让外部提交逻辑魔方状态，
		# 再使用新的逻辑状态重绘，避免短暂跳回旧状态。
		if callback is not None:
			callback()

		self._draw_mesh()

	def _cancel_animation(self):
		"""取消当前动画。"""
		self._anim = None

		if self._anim_event is not None:
			self._anim_event.cancel()
			self._anim_event = None

	# ------------------------------------------------------------------
	# 鼠标和触摸手势
	# ------------------------------------------------------------------

	def on_touch_down(self, touch):
		if not self.collide_point(*touch.pos):
			return super().on_touch_down(touch)

		if getattr(touch, "is_mouse_scrolling", False):
			button = getattr(touch, "button", "")
			scroll_y = getattr(touch, "scroll_y", 0)

			if button == "scrollup":
				factor = 1.1
			elif button == "scrolldown":
				factor = 0.9
			elif scroll_y > 0:
				factor = 1.1
			else:
				factor = 0.9

			self._display_zoom *= factor
			self._display_zoom = max(
				0.25,
				min(4.0, self._display_zoom),
			)

			self._draw_mesh()
			return True

		self._touch0 = touch
		self._touch0_pos = touch.pos

		# 抓取触摸，防止鼠标移出 Widget 后丢失抬起事件。
		try:
			touch.grab(self)
		except Exception:
			pass

		return True

	def on_touch_move(self, touch):
		is_current_touch = (
			self._touch0 is not None
			and touch is self._touch0
		)

		if not is_current_touch:
			return super().on_touch_move(touch)

		if self._touch0_pos is None:
			self._touch0_pos = touch.pos
			return True

		dx = touch.x - self._touch0_pos[0]
		dy = touch.y - self._touch0_pos[1]

		self._touch0_pos = touch.pos

		# 取反：让魔方跟随手指方向旋转（上滑魔方朝上，左滑魔方朝左）。
		self.camera.rotate(
			-dx * 0.4,
			-dy * 0.4,
		)

		self._draw_mesh()
		return True

	def on_touch_up(self, touch):
		is_current_touch = (
			self._touch0 is not None
			and touch is self._touch0
		)

		if not is_current_touch:
			return super().on_touch_up(touch)

		try:
			touch.ungrab(self)
		except Exception:
			pass

		self._touch0 = None
		self._touch0_pos = None

		return True


def _rotation_matrix_for(animation):
	"""根据动画状态生成当前层的旋转矩阵。"""
	angle_deg = animation["angle_current"]
	axis = animation["axis"]

	if axis == 0:
		return Mat4.rotation_axis(
			angle_deg,
			(1.0, 0.0, 0.0),
		)

	if axis == 1:
		return Mat4.rotation_axis(
			angle_deg,
			(0.0, 1.0, 0.0),
		)

	return Mat4.rotation_axis(
		angle_deg,
		(0.0, 0.0, 1.0),
	)


def _dot(a, b):
	"""三维向量点积。"""
	return (
		a[0] * b[0]
		+ a[1] * b[1]
		+ a[2] * b[2]
	)


def _cross(a, b):
	"""三维向量叉积。"""
	return (
		a[1] * b[2] - a[2] * b[1],
		a[2] * b[0] - a[0] * b[2],
		a[0] * b[1] - a[1] * b[0],
	)


def _length(vector):
	"""三维向量长度。"""
	return math.sqrt(_dot(vector, vector))


def _normalize(vector):
	"""归一化三维向量。"""
	length = _length(vector)

	if length <= _EPSILON:
		return None

	return (
		vector[0] / length,
		vector[1] / length,
		vector[2] / length,
	)

def _get_vertex_bounds(vertices):
    """计算场景顶点的三维包围盒。

    vertices 中每7个浮点表示一个顶点：

        x, y, z, r, g, b, a

    返回：
        model_center:
            模型包围盒中心，格式为 (x, y, z)。

        model_size:
            X、Y、Z 三个轴向尺寸中的最大值。

        axis_sizes:
            三轴实际尺寸，格式为
            (size_x, size_y, size_z)。

    如果没有有效顶点，则返回 None。
    """
    if not vertices:
        return None

    if len(vertices) < 7:
        return None

    min_x = math.inf
    min_y = math.inf
    min_z = math.inf

    max_x = -math.inf
    max_y = -math.inf
    max_z = -math.inf

    vertex_count = 0

    for index in range(0, len(vertices) - 6, 7):
        x = float(vertices[index])
        y = float(vertices[index + 1])
        z = float(vertices[index + 2])

        # 忽略非有限坐标，防止 NaN 或 inf 污染整个包围盒。
        if not (
            math.isfinite(x)
            and math.isfinite(y)
            and math.isfinite(z)
        ):
            continue

        min_x = min(min_x, x)
        min_y = min(min_y, y)
        min_z = min(min_z, z)

        max_x = max(max_x, x)
        max_y = max(max_y, y)
        max_z = max(max_z, z)

        vertex_count += 1

    if vertex_count == 0:
        return None

    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z

    model_center = (
        (min_x + max_x) * 0.5,
        (min_y + max_y) * 0.5,
        (min_z + max_z) * 0.5,
    )

    axis_sizes = (
        size_x,
        size_y,
        size_z,
    )

    model_size = max(axis_sizes)

    return (
        model_center,
        model_size,
        axis_sizes,
    )


def _project_points_to_q(vertices, eye, right, camera_up, forward):
    """把一组顶点（每7个浮点：x,y,z,r,g,b,a）投影到相机 q 空间。

    返回：
        [(qx, qy), ...]

    跳过位于相机平面或后方的顶点。
    """
    points = []

    if not vertices:
        return points

    for index in range(0, len(vertices) - 6, 7):
        world_x = float(vertices[index])
        world_y = float(vertices[index + 1])
        world_z = float(vertices[index + 2])

        relative = (
            world_x - eye[0],
            world_y - eye[1],
            world_z - eye[2],
        )

        camera_z = _dot(relative, forward)

        if camera_z <= _EPSILON:
            continue

        points.append((
            _dot(relative, right) / camera_z,
            _dot(relative, camera_up) / camera_z,
        ))

    return points