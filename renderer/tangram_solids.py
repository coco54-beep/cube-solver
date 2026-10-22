"""Physical Tangram housings shared with the playback renderer.

Unknown pieces are grey reference solids, never coloured invented panels.
Recorded panels keep their real depth and normal, including sloping skins.
"""
from functools import lru_cache

from cube.articulated import ArticulatedCube, overlap
from cube.articulated_observation import panels_for_outline, polygon_key
from cube.polyhedral import CUBE, dot
from renderer.articulated_view import ArticulatedView


@lru_cache(maxsize=12)
def _pose_cube(kind, pose):
    cube = ArticulatedCube(kind)
    cube.colors = (pose,) * len(cube.solids)
    return cube


@lru_cache(maxsize=512)
def _body(kind, home, pose):
    cube = _pose_cube(kind, pose)
    faces = cube.placed_faces(home)
    key = tuple(sorted(polygon_key(p) for p, _ in faces))
    skins = {slot: polygon_key(points) for slot, points in zip(cube.geometry.pieces[home],
             (points for points, color in faces if color >= 0))}
    return faces, key, ArticulatedView.piece_surfaces(cube, home), skins


@lru_cache(maxsize=8192)
def _bodies_overlap(kind, left, right):
    return overlap(_body(kind, *left)[0], _body(kind, *right)[0])


def rigid_piece_surfaces(kind, home, pose):
    return _body(kind, home, pose)[2]


class TangramSolidPreview:
    def __init__(self, cube, state, matched=False):
        self.kind = cube.puzzle_kind
        self.recorded = {}
        observed_bodies = {}
        for face, items in enumerate(state['views']):
            for index, item in enumerate(items):
                world_key = polygon_key(item['preview'])
                self.recorded.setdefault(world_key, []).append((face, index, item['color']))
                if matched:continue
                candidates = panels_for_outline(self.kind, face, polygon_key(item['outline']))
                panel = next((p for p in candidates if p.color == item['color']
                              and polygon_key(p.world) == world_key
                              and (not item.get('body_key') or _body(self.kind, p.home, p.pose)[1] == item['body_key'])), None)
                if panel is None:continue
                identity = panel.home, panel.pose
                observed_bodies.setdefault(_body(self.kind, *identity)[1], identity)
        bodies = dict(observed_bodies)
        for home, pose in enumerate(cube.frames):
            identity = home, pose
            key = _body(self.kind, *identity)[1]
            if key in bodies:continue
            # A replacement body occupies real space. Do not leave the grey
            # source body inside it or show an opaque, fixed cube shell.
            if not matched and any(_bodies_overlap(self.kind, identity, other)
                                   for other in observed_bodies.values()):continue
            bodies[key] = identity
        self.bodies = tuple(bodies.values())

    def surfaces(self, active_face, guide_offset):
        surfaces = []
        for ordinal, identity in enumerate(self.bodies):
            _, _, body_surfaces, skins = _body(self.kind, *identity)
            for points, normal, color, original_slot, layer, home, width in body_surfaces:
                face = active_face if dot(normal, CUBE[active_face]) > 1e-7 else max(range(6), key=lambda f: dot(normal, CUBE[f]))
                slot = face * 1024 + guide_offset + ordinal
                if color < 0:
                    current = next((p for p in self.recorded.get(polygon_key(points), ()) if p[0] == face), None)
                    if current is not None:slot = face * 1024 + current[1]
                if color >= 0:
                    entries = self.recorded.get(skins[original_slot], ())
                    current = next((p for p in entries if p[0] == face), None)
                    color = (current or entries[0])[2] if entries else -2
                    if current is not None:slot = face * 1024 + current[1]
                surfaces.append((points, normal, color, slot, layer, home, width))
        return tuple(surfaces)
