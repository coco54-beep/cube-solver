"""未填格（空字符串贴纸）不得被判为已还原的回归测试。

历史 bug：is_solved() 只判断 `col is not None`，把录入页未填的 "" 当成一种
颜色，导致全空 / 部分填色的魔方被误判为已还原。
"""

from cube.conversion import cubies_to_facelets, facelets_to_cubies
from cube.coordinates import FACE_NORMALS
from cube.cube3 import Cube3


def _empty_facelets(n=3, fill=""):
    return {face: [[fill] * n for _ in range(n)] for face in FACE_NORMALS}


def test_all_empty_cube_not_solved():
    cubies = facelets_to_cubies(_empty_facelets(3), 3)
    assert not Cube3(cubies).is_solved()


def test_partly_filled_cube_not_solved():
    solved = Cube3.solved()
    facelets = cubies_to_facelets(solved.cubies, 3)
    facelets["U"] = [[""] * 3 for _ in range(3)]
    cubies = facelets_to_cubies(facelets, 3)
    assert not Cube3(cubies).is_solved()


def test_solved_roundtrip_still_solved():
    solved = Cube3.solved()
    facelets = cubies_to_facelets(solved.cubies, 3)
    cubies = facelets_to_cubies(facelets, 3)
    assert Cube3(cubies).is_solved()
