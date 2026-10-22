"""Metallic shell views for the mirror shape modifications."""
from renderer.mirror_view import MirrorView
from renderer.shape_cube_view import _geometry


class MirrorShapeView(MirrorView):
    shape_kind = None

    def _piece_geometry(self, home, frame, subdivisions, n):
        return tuple((points, normal, 0, 'sticker' if _finish == 'sticker' else 'cut', edges)
                     for points, normal, _color, _finish, edges
                     in _geometry(self.shape_kind, home, frame, n))


class MirrorWindmillView(MirrorShapeView):
    shape_kind = 'windmill'


class MirrorAxisView(MirrorShapeView):
    shape_kind = 'axis'


class MirrorFisherView(MirrorShapeView):
    shape_kind = 'fisher'


class MirrorUnequalWindmillView(MirrorShapeView):
    shape_kind = 'windmill_unequal'


class MirrorUnequalFisherView(MirrorShapeView):
    shape_kind = 'fisher_unequal'


class MirrorOffsetWindmillView(MirrorShapeView):
    shape_kind = 'windmill_offset'


class MirrorOffsetFisherView(MirrorShapeView):
    shape_kind = 'fisher_offset'
