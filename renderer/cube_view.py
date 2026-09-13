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
		super().__init__(**kwargs)

		self.camera = OrbitCamera()

		# 当前层转动动画信息
		self._anim = None
		self._anim_event = None

		# 显示整体旋转（输入界面用于把某面转到正对相机）。
		# 逻辑魔方状态不随其变化；渲染时对顶点额外施加该变换。
		self._whole_world = None

		# 最近一次 _draw_mesh 的取景参数，供拾取（world -> screen）复用。
		self._last_proj = None

		# 最近一次绘制生成的面片屏幕四角 + cubie 位置 + 面名，
		# 供 pick_facelet 把屏幕触摸点还原成"接触的小面"。
		self._last_quads = []

		# 当前整体翻转动画信息
		self._whole_anim = None
		self._whole_anim_event = None

		# 当前拖拽触摸
		self._touch0 = None
		self._touch0_pos = None

		# 屏幕显示缩放。
		# 不直接依赖 camera.zoom()，避免自适应取景抵消相机缩放。
		self._display_zoom = 1.0

		# 视角固定：为 True 时忽略拖拽旋转（滚轮/双指缩放仍可用）。
		self.lock_rotation = False

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
		self._cancel_whole_anim()
		self._whole_world = None
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

	def set_whole_world(self, world):
		"""设置显示整体旋转矩阵（把某面转到正对相机）。None 表示无整体旋转。"""
		self._whole_world = world
		self._redraw()

	def animate_whole_turn(self, axis, angle_deg, duration, on_done=None):
		"""播放一次整体旋转动画（把整块魔方绕 axis 转到 angle_deg）。"""
		self._cancel_whole_anim()
		self._whole_anim = {
			"axis": axis,
			"angle_total": float(angle_deg),
			"angle_current": 0.0,
			"duration": max(0.0, float(duration)),
			"elapsed": 0.0,
			"base_world": self._whole_world,
			"on_done": on_done,
		}
		if self._whole_anim["duration"] <= 0.0:
			self._whole_anim["angle_current"] = self._whole_anim["angle_total"]
			self._apply_whole_anim()
			self._finish_whole_anim()
			return
		self._whole_anim_event = Clock.schedule_interval(self._whole_anim_tick, 0)

	def _whole_anim_tick(self, dt):
		if self._whole_anim is None:
			return False
		anim = self._whole_anim
		anim["elapsed"] += max(0.0, dt)
		duration = max(anim["duration"], _EPSILON)
		t = min(1.0, anim["elapsed"] / duration)
		eased_t = t * t * (3.0 - 2.0 * t)
		anim["angle_current"] = anim["angle_total"] * eased_t
		self._apply_whole_anim()
		if t >= 1.0:
			self._finish_whole_anim()
			return False
		return True

	def _apply_whole_anim(self):
		anim = self._whole_anim
		if anim is None:
			return
		base = anim["base_world"]
		if base is not None:
			delta = _rotation_matrix_for_whole(anim["angle_current"], anim["axis"])
			self._whole_world = delta * base
		else:
			self._whole_world = None
		self._draw_mesh()

	def _finish_whole_anim(self):
		anim = self._whole_anim
		self._whole_anim = None
		if self._whole_anim_event is not None:
			self._whole_anim_event.cancel()
			self._whole_anim_event = None
		if anim is not None and anim.get("on_done") is not None:
			anim["on_done"]()
		self._draw_mesh()

	def _cancel_whole_anim(self):
		self._whole_anim = None
		if self._whole_anim_event is not None:
			self._whole_anim_event.cancel()
			self._whole_anim_event = None

	# ------------------------------------------------------------------
	# 拾取：屏幕坐标 -> 当前正对面的格子 (r, c)
	# ------------------------------------------------------------------

	def pick_cell(self, face, n, px, py):
		"""把屏幕坐标 (px, py) 映射到 face 面上的格子 (r, c)。

		使用与 _draw_mesh 相同的取景参数。正对面的 n x n 格子中心点
		被投影到屏幕，选距离点击点最近且落在容忍距离内的格子。
		无匹配时返回 None。
		"""
		if self._last_proj is None:
			return None
		proj = self._last_proj
		eye, right, camera_up, forward = proj["basis"]
		pixel_scale = proj["pixel_scale"]
		pcx = proj["center_x"]
		pcy = proj["center_y"]
		wcx = proj["widget_center_x"]
		wcy = proj["widget_center_y"]

		from cube.coordinates import pos_from_rc

		# 先把每个格子中心投影到屏幕坐标。
		pts = {}
		for r in range(n):
			for c in range(n):
				pos = pos_from_rc(n, face, r, c)
				world = self._whole_world
				if world is not None:
					pos = world.transform(*pos)
				rel = (
					pos[0] - eye[0],
					pos[1] - eye[1],
					pos[2] - eye[2],
				)
				z = _dot(rel, forward)
				if z <= _EPSILON:
					continue
				qx = _dot(rel, right) / z
				qy = _dot(rel, camera_up) / z
				sx = wcx + (qx - pcx) * pixel_scale
				sy = wcy + (qy - pcy) * pixel_scale
				pts[(r, c)] = (sx, sy)

		if not pts:
			return None

		# 最近格。
		best = None
		best_dist = None
		for key, (sx, sy) in pts.items():
			dist = ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5
			if best_dist is None or dist < best_dist:
				best_dist = dist
				best = key
		if best is None:
			return None

		# 容忍距离：用相邻格中心间距衡量（约 1 格宽）。
		r, c = best
		spacing = None
		for dr, dc in ((0, 1), (1, 0)):
			nb = (r + dr, c + dc)
			if nb in pts:
				sx, sy = pts[best]
				nsx, nsy = pts[nb]
				d = ((sx - nsx) ** 2 + (sy - nsy) ** 2) ** 0.5
				spacing = d if spacing is None else max(spacing, d)
		if spacing is None:
			spacing = max(1.0, pixel_scale)
		if best_dist is not None and best_dist > spacing:
			return None
		return best

	def pick_facelet(self, px, py):
		"""把屏幕坐标 (px, py) 还原成"接触的小面"。

		返回 (pos, face_name) 或 None：
			pos: 被点中面片所属 cubie 的当前空间位置（即该 cubie 的层坐标）。
			face_name: 该面片的朝向面（如 "U"、"R"）。

		在最近一次绘制保存的面片（self._last_quads）中，从近到远
		找到第一个包含该点的面片。四边形成两个三角形做点在三角内测试。
		"""
		quads = getattr(self, "_last_quads", None)
		if not quads:
			return None
		# quads 按 depth 从大到小排序（远处在前），因此逆序 = 近处优先。
		for group, pos, fname in reversed(quads):
			if _point_in_quad(px, py, group):
				return (pos, fname)
		return None

	# ------------------------------------------------------------------
	# 绘制
	# ------------------------------------------------------------------

	def _redraw(self, *args):
		"""重新绘制魔方。"""
		self._draw_mesh()

	def _draw_mesh(self):
		"""生成场景并绘制魔方网格。"""
		self._mesh_group.clear()
		self._last_proj = None
		self._last_quads = []

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
		vertices, _indices, face_info = scene_mod.build_scene(
			self.cube,
			moving_positions=moving_positions,
			rotation=rotation,
			highlight=getattr(self, "_highlight", None),
		)

		# 取景包围盒用「未执行层转动、未施加整体旋转」的模型顶点。否则整体旋转
		# 动画（输入页切面）期间旋转后的包围盒会变化，导致画面缩放抖动，并误报
		# 「三轴尺寸不一致」。
		if self._anim is not None:
			reference_vertices, _reference_indices, _reference_face_info = scene_mod.build_scene(
				self.cube,
				moving_positions=None,
				rotation=None,
				highlight=getattr(self, "_highlight", None),
			)
		else:
			reference_vertices = list(vertices)

		# 施加显示整体旋转（输入界面用于把某面转到正对相机）。
		if self._whole_world is not None and len(vertices) >= 7:
			w = self._whole_world
			for i in range(0, len(vertices) - 6, 7):
				p = w.transform(
					float(vertices[i]),
					float(vertices[i + 1]),
					float(vertices[i + 2]),
				)
				vertices[i] = p[0]
				vertices[i + 1] = p[1]
				vertices[i + 2] = p[2]

		if not vertices:
			return

		if len(vertices) < 28:
			return

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

		# 保存取景参数，供 pick_cell 把世界点投影回屏幕坐标。
		self._last_proj = {
			"basis": (eye, right, camera_up, forward),
			"pixel_scale": pixel_scale,
			"center_x": projected_center_x,
			"center_y": projected_center_y,
			"widget_center_x": widget_center_x,
			"widget_center_y": widget_center_y,
		}

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

			# 该面片对应的 cubie 位置与面名（与 build_scene 的顶点段对齐）。
			quad_no = index // 4
			fpos, fname = face_info[quad_no]

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
				fpos,
				fname,
			))

		# 远处的面先绘制，近处的面后绘制。
		quads.sort(
			key=lambda item: item[0],
			reverse=True,
		)
		# 保存每个面片的屏幕坐标 + cubie 位置 + 面名，供小面拾取使用。
		self._last_quads = [
			(group, fpos, fname)
			for (_depth, group, fpos, fname) in quads
		]

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
		for _depth, group, _fpos, _fname in quads:
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
		include_fixed_centers=False,
	):
		"""播放单层/多层转动动画。

		参数：
			axis: 0、1、2，对应 X、Y、Z 轴。
			layer_pos: 该轴上主层坐标（如 y=1）。
			angle_deg: 总转动角度（度）。
			duration: 动画持续时间（秒）。
			on_done: 动画完成回调（通常应修改逻辑状态）。
			layer_positions: 可选的层坐标列表（宽层转动时含内层）。
			include_fixed_centers: True 时固定面心也随层转动（自由拧层的
				物理转动），与 apply_layer_turn 一致；False 时保持面心不动
				（标准记法 M/E/S），与 apply_inner_slice 一致。
			无论该参数取值，位于旋转轴上的固定面心（整面转的轴心）都会
				原地自转，使整面转动时轴心可见地旋转。
		"""
		if self.cube is None:
			return

		if axis not in (0, 1, 2):
			raise ValueError("axis 必须是 0、1 或 2")

		self._cancel_animation()

		if layer_positions is None:
			layer_positions = [layer_pos]
		from cube.cubie_model import is_fixed_face_center
		other_axes = [i for i in (0, 1, 2) if i != axis]
		positions = set()
		for position, cubie in self.cube.cubies.items():
			if not any(position[axis] == lp for lp in layer_positions):
				continue
			if not is_fixed_face_center(cubie):
				positions.add(position)
				continue
			# 固定面心：位于旋转轴上时只原地自转（整面转的轴心可见），
			# 任何情况下都包含；偏离旋转轴时（M/E/S 切片）标准记法保持
			# 不动，仅自由拧层（物理转动）才随层移动。
			on_axis = all(position[i] == 0 for i in other_axes)
			if on_axis or include_fixed_centers:
				positions.add(position)

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

		# 视角固定：不响应拖拽旋转（滚轮缩放已在上方处理）。
		if getattr(self, "lock_rotation", False):
			return False

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


def _rotation_matrix_for_whole(angle_deg, axis):
	"""根据整体翻转动画状态生成旋转矩阵（axis 为三维向量）。"""
	return Mat4.rotation_axis(angle_deg, axis)


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


def _point_in_quad(px, py, group):
    """判断屏幕点 (px, py) 是否落在四边形 group（4 个 {x,y} 点）内。

    把四边形拆成两个三角形 (0,1,2) 与 (0,2,3)，任一点在三角形内即命中。
    """
    if len(group) < 4:
        return False
    pts = [(float(p["x"]), float(p["y"])) for p in group]
    return (
        _point_in_triangle(px, py, pts[0], pts[1], pts[2])
        or _point_in_triangle(px, py, pts[0], pts[2], pts[3])
    )


def _point_in_triangle(px, py, a, b, c):
    """屏幕点是否在三角形 (a,b,c) 内（含边界，采用符号一致法）。"""
    d1 = _tri_sign(px, py, a, b)
    d2 = _tri_sign(px, py, b, c)
    d3 = _tri_sign(px, py, c, a)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def _tri_sign(px, py, a, b):
    return (px - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (py - b[1])