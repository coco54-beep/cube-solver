"""Bridge visible Pandora face colours to the oriented physical model."""
from functools import lru_cache


@lru_cache(maxsize=1)
def profile():
    from vision.scan_profiles import ScanProfile
    return ScanProfile('pandora',3)


def from_facelets(facelets,reference):
    from vision.scan_profiles import CUBE_CODES
    p=profile();data=p.blank()
    for surface in p.surfaces:
        face,r,c=surface.cell
        code=facelets[face][r][c]
        if code not in CUBE_CODES:raise ValueError('camera.invalid_input')
        data[face][surface.index]=CUBE_CODES.index(code)
    return p.apply(data,reference)


def to_facelets(cube):
    from vision.scan_profiles import CUBE_CODES
    p=profile();data=p.from_cube(cube,set(cube.positions))
    result={f:[['']*3 for _ in range(3)] for f in p.face_keys}
    for surface in p.surfaces:
        face,r,c=surface.cell
        result[face][r][c]=CUBE_CODES[data[face][surface.index]]
    return result
