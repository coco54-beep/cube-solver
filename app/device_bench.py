"""On-device polyhedral benchmark triggered by an adb extra or environment variable.

Usage:
    adb shell am start -n com.example.cubesolver/org.kivy.android.PythonActivity \
        --es bench "megaminx:13:12345,football:5:12345"

Each item is ``kind:order[:seed]``. Results are written to logcat with the
``device_bench`` tag and the app exits afterwards.
"""
import json
import os
import time


def _bench_file():
    for base in (os.environ.get("ANDROID_PRIVATE"),
                 os.environ.get("ANDROID_APP_PATH")):
        if base:
            path = os.path.join(base, "device_bench.txt")
            if os.path.exists(path):
                return path
    return None


def requested():
    spec = os.environ.get("CUBESOLVER_BENCH")
    if spec:
        return spec
    path = _bench_file()
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                return value
        except OSError:
            pass
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        intent = activity.getIntent()
        extras = intent.getExtras() if intent is not None else None
        if extras is not None:
            value = extras.getString("bench")
            if value:
                return value
    except Exception:
        pass
    return None


def _run_one(item):
    from cube.polyhedral import PolyhedralPuzzle
    from cube.polyhedral_scramble import scramble, scramble_length
    from solver.polyhedral import solve_polyhedral

    parts = item.strip().split(":")
    kind = parts[0]
    n = int(parts[1])
    seed = int(parts[2]) if len(parts) > 2 else 12345
    cube = PolyhedralPuzzle.solved(kind, n)
    cube.colors = [s.face for s in cube.geometry.stickers]
    length = scramble_length(cube)
    scramble(cube, length, seed=seed)
    started = time.perf_counter()
    solution = solve_polyhedral(cube)
    elapsed = time.perf_counter() - started
    replay = cube.clone()
    for move in solution:
        replay.apply_move(move)
    return {
        "kind": kind, "n": n, "seed": seed, "scramble_length": length,
        "seconds": round(elapsed, 3), "moves": len(solution),
        "replay_ok": replay.is_solved(),
    }


def run(spec):
    from kivy.logger import Logger
    path = _bench_file()
    if path:
        try:
            os.remove(path)
        except OSError:
            pass
    results = []
    for item in spec.split(","):
        if not item.strip():
            continue
        try:
            row = _run_one(item)
        except Exception as exc:
            row = {"item": item, "error": type(exc).__name__ + ": " + str(exc)}
        results.append(row)
        Logger.info("device_bench: %s", json.dumps(row, ensure_ascii=False))
    Logger.info("device_bench_done: %s", json.dumps(results, ensure_ascii=False))
    return results
