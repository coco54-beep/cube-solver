"""Validation of higher order facelets, independent of scramble history."""
from collections import Counter
from cube.colors import VALID_COLORS
from cube.cube_n import CubeN
from cube.conversion import facelets_to_cubies


def validate_nxn(facelets, n, lang="zh"):
    from app.i18n import tr
    faces = ("U", "R", "F", "D", "L", "B")
    if any(face not in facelets or len(facelets[face]) != n
           or any(len(row) != n for row in facelets[face]) for face in faces):
        return [tr("nxn.error.shape", n=n)]
    counts = Counter(color for face in faces for row in facelets[face] for color in row)
    if any(color not in VALID_COLORS for color in counts):
        return [tr("nxn.error.colors")]
    if any(counts[color] != n * n for color in VALID_COLORS):
        return [tr("nxn.error.count", count=n * n)]
    try:
        from solver.solver_n import inspect_state
        inspect_state(CubeN(facelets_to_cubies(facelets, n), n))
    except Exception as exc:
        key = str(exc)
        return [tr(key) if key.startswith("nxn.") else tr("nxn.error.state")]
    return []
