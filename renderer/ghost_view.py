"""Ghost shell surfaces, including the physical horizontal-layer offsets."""
from cube.ghost import piece_faces, _rotate_y
from cube.mastermorphix import transform
from cube.coordinates import coord_values
from cube.polyhedral import add, cross, dot, unit
from renderer.mirror_view import MirrorView


class GhostView(MirrorView):
    def reset_camera(self):
        super().reset_camera()
        if self.cube is not None and self.cube.n == 1:
            self.camera.azimuth = 15.
            self.camera.elevation = 10.
            self._redraw()

    def start_turn(self, axis, layer_pos, angle_deg, duration, on_done=None,
                   layer_positions=None, include_fixed_centers=False):
        if self.cube is None or self.cube.n != 1:
            return super().start_turn(axis, layer_pos, angle_deg, duration, on_done,
                                      layer_positions, include_fixed_centers)
        from cube.ghost_floppy import AXES, moving_positions
        from kivy.clock import Clock
        if axis not in range(3, 8):
            raise ValueError('Invalid Floppy Ghost axis')
        self._cancel_animation()
        side = axis-3
        self._anim = dict(axis=axis, axis_vector=AXES[side], positions=set(moving_positions(side)),
                          angle_total=float(angle_deg), angle_current=0., duration=max(0., duration),
                          elapsed=0., on_done=on_done)
        if duration <= 0:
            self._finish_turn()
        else:
            self._anim_event = Clock.schedule_interval(self._anim_tick, 0)

    def resolve_floppy_twist(self, hit, drag):
        from cube.ghost_floppy import AXES, moving_positions
        from renderer.gesture import choose_turn
        from renderer.twist import TwistSpec
        pos, point = hit
        right, up, _, _, _, _ = self._mm_proj
        candidates = []
        for side, normal in enumerate(AXES):
            if pos not in moving_positions(side):
                continue
            if self._whole_world is not None:
                normal = self._whole_world.transform(*normal)
            velocity = cross(normal, point)
            candidates.append((side+3, (dot(velocity, right), dot(velocity, up))))
        selected = choose_turn(drag, candidates)
        return TwistSpec(selected[0], (0,), selected[1]) if selected else None

    def _draw_mesh(self):
        super()._draw_mesh()
        floppy = self.cube is not None and self.cube.n == 1
        if floppy:
            for label in getattr(self, '_axis_labels', {}).values():
                label.opacity = 0
        labels = getattr(self, '_floppy_labels', None)
        if floppy and self.show_axes and labels is None:
            from kivy.uix.label import Label
            labels = self._floppy_labels = [Label(text=str(i+1), font_size='14sp', bold=True,
                                                size_hint=(None,None), size=(26,26), color=(.1,.8,.95,1))
                                           for i in range(5)]
            for label in labels:
                self.add_widget(label)
        if labels:
            from cube.ghost_floppy import EDGES
            for pos, label in zip(EDGES, labels):
                polygons = [polygon for polygon, p, _ in self._polygons if p == pos]
                label.opacity = int(floppy and self.show_axes and bool(polygons))
                if polygons:
                    polygon = max(polygons, key=lambda p: abs(sum(a[0]*b[1]-b[0]*a[1]
                                                                  for a,b in zip(p,p[1:]+p[:1]))))
                    label.center = (sum(p[0] for p in polygon)/len(polygon),
                                    sum(p[1] for p in polygon)/len(polygon))

    def _piece_geometry(self, home, frame, subdivisions, n):
        phase = 0. if n == 1 else self.cube.phases[coord_values(n).index(transform(frame, home)[1])]
        result = []
        for vertices, color in piece_faces(n, home):
            points = tuple(_rotate_y(transform(frame, p), phase) for p in vertices)
            normal = (0., 0., 0.)
            for a, b in zip(points, points[1:]+points[:1]):
                normal = add(normal, cross(a, b))
            if dot(normal, normal) < 1e-14:
                continue
            result.append((points, unit(normal), 0, 'cut' if color < 0 else 'sticker',
                           tuple((i, (i+1) % len(points)) for i in range(len(points)))))
        return tuple(result)
