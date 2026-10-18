"""Synthetic irregular-face recognition with known guide corners."""
import numpy as np
import pytest
from PIL import Image, ImageDraw

from vision.scan_profiles import SUPPORTED, ScanProfile, detect_surface


@pytest.mark.parametrize('size', [4, 6, 8, 12, 20, 32])
def test_exact_palette_colors_remain_distinguishable(size):
    from vision.scan_profiles import DEFAULT_PALETTES, _read_color
    palette = DEFAULT_PALETTES[size]
    for index, rgba in enumerate(palette):
        rgb = np.asarray([round(v * 255) for v in rgba[:3]], dtype=np.uint8)
        assert _read_color(np.tile(rgb, (25, 1)), palette) == index


def test_dark_samples_are_not_classified_as_a_sticker():
    from vision.scan_profiles import DEFAULT_PALETTES, _read_color
    assert _read_color(np.full((25, 3), 10, dtype=np.uint8), DEFAULT_PALETTES[32]) == -1


def test_identical_references_remain_uncertain():
    from vision.scan_profiles import _read_color
    palette = ((.87, .66, .97, 1), (.87, .66, .97, 1))
    assert _read_color(np.tile((222, 168, 247), (25, 1)), palette) == -1


@pytest.mark.parametrize('kind,n', [(kind, max(orders)) for kind, orders in SUPPORTED.items()])
def test_irregular_face_reads_rendered_stickers(kind, n):
    profile = ScanProfile(kind, n)
    face = profile.face_keys[0]
    world = profile.face_world(face)
    canonical, templates = profile.templates(face, world)
    image = Image.new('RGB', (520, 520), (12, 12, 12))
    draw = ImageDraw.Draw(image)
    expected = {}
    for position, (index, _, patches, _) in enumerate(templates):
        color = position % len(profile.palette)
        rgb = tuple(round(v * 255) for v in profile.palette[color][:3])
        for patch in patches:
            points = patch * 440 + 40
            draw.polygon([tuple(point) for point in points], fill=rgb)
        expected[index] = color
    result = detect_surface(np.asarray(image), profile, face, world,
                            controls=canonical * 440 + 40)
    assert result.ok, {key: (expected[key], value) for key, value in result.values.items()
                       if value != expected[key]}
    assert result.values == expected
    assert set(result.samples) == set(expected)


@pytest.mark.parametrize('kind,n', [(kind, min(orders)) for kind, orders in SUPPORTED.items()])
def test_irregular_navigation_visits_every_face_once(kind, n):
    profile = ScanProfile(kind, n)
    orientation = profile.new_orientation()
    start = orientation.current_face()
    seen = []
    for _ in profile.face_keys:
        seen.append(orientation.current_face())
        orientation.turn_next()
    assert len(set(seen)) == len(profile.face_keys)
    assert set(seen) == set(profile.face_keys)
    assert orientation.current_face() == start
