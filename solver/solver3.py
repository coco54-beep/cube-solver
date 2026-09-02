"""Bridge between our cube model and the hkociemba two-phase 3x3 solver.

The real solver lives in kociemba-src/package_src/twophase (GPL-3.0). We wrap
it behind solve_3x3() so the rest of the project only sees SolveResult.

Notes:
- The twophase package stores its ~63 MB lookup tables in a CWD-relative folder
  (defs.FOLDER). We pin it to an absolute path under the bundle root so the
  solver works regardless of where the APK is run from, and so it loads the
  pre-generated tables instead of regenerating them (which takes ~30 min).
"""
import os
import re
import sys
import time

from solver.result import SolveResult, SolveStage

# --- locate the bundled twophase package + its tables folder -----------------
_BUNDLE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KOCIEMBA_SRC = os.path.join(_BUNDLE_ROOT, "kociemba-src", "package_src")

sys.path.insert(0, _KOCIEMBA_SRC)

import twophase.defs as defs  # noqa: E402
defs.FOLDER = os.path.join(_BUNDLE_ROOT, "twophase")  # pre-generated tables dir
import twophase.solver as sv  # noqa: E402

# hkociemba reads faces in this order, 9 facelets each, row-major.
_FACES = ("U", "R", "F", "D", "L", "B")

# hkociemba emits "<face><count>" tokens (1=CW, 2=180, 3=CCW); map count to our suffix.
_MOVE_SUFFIX = {"1": "", "2": "2", "3": "'"}
_MOVE_RE = re.compile(r"^([URFDLB])([123])$")


def _build_cubestring(facelets):
    """Flatten our facelets dict into hkociemba's 54-char facelet string.

    Order is U, R, F, D, L, B; within each face, row-major [r][c]. This matches
    hkociemba's Facelet reading order exactly (verified against the core model).

    颜色→面映射以录入的实际中心色为准动态建立：用户把哪种颜色放在哪个面
    中心，就以它作为该面的基准色，从而任意摆放中心色都能正确求解。
    """
    color_to_face = {}
    for face in _FACES:
        center = facelets[face][1][1]
        color_to_face[center] = face
    out = []
    for face in _FACES:
        grid = facelets[face]
        for r in range(3):
            for c in range(3):
                out.append(color_to_face[grid[r][c]])
    return "".join(out)


def _parse_solution(raw):
    """Convert hkociemba's 'U1 R3 F2 (19f)' into (success, our_moves).

    An error string (from bad input / unsolvable) has no valid move tokens and
    is reported as a failure. A solved cube returns a 0-move success.
    """
    if raw.startswith(("Error", "first cube", "second cube")):
        return False, []
    body = raw.split("(", 1)[0].strip()
    moves = []
    for tok in body.split():
        m = _MOVE_RE.match(tok)
        if not m:
            return False, []
        moves.append(m.group(1) + _MOVE_SUFFIX[m.group(2)])
    return True, moves


def solve_3x3(facelets, max_length=20, timeout=3.0, minimize=False):
    """Solve a 3x3 cube given as a facelets dict; return a SolveResult.

    facelets: {face: [[color, color, color], ... 3 rows]} for faces U,R,F,D,L,B.

    hkociemba 在找到「第一个 <= max_length 的解」后即返回，不做最小化，因此
    max_length=20 时常见输出正好 20、且同一状态多次求解长度有抖动。minimize=True
    时改用目标递减 (18 -> 19 -> max_length) 试探：在更小目标下若能命中（长度
    <= 目标），输出更短且更稳定；命中不了的低目标会耗尽短超时后自动升档。
    """
    t0 = time.perf_counter()
    cubestring = _build_cubestring(facelets)

    def _result(raw, success, moves):
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return SolveResult(
            success=success,
            moves=moves,
            message=raw,
            elapsed_ms=elapsed_ms,
            move_count=len(moves),
            stages=[SolveStage("twophase", "hkociemba two-phase solver", moves)]
            if success else [],
        )

    if minimize:
        for target in (18, 19):
            if target >= max_length:
                break
            raw = sv.solve(cubestring, target, min(timeout, 1.0))
            success, moves = _parse_solution(raw)
            if success and len(moves) <= target:
                return _result(raw, success, moves)
    raw = sv.solve(cubestring, max_length, timeout)
    success, moves = _parse_solution(raw)
    return _result(raw, success, moves)
