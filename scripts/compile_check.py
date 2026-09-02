#!/usr/bin/env bash
set -u
cd /mnt/d/coco/cube-solver
python3 - <<'PY'
import py_compile
targets = [
    "main.py", "primitives.py",
    "app/application.py", "app/config.py", "app/constants.py", "app/fonts.py",
    "ui/__init__.py", "ui/screens/__init__.py",
    "ui/screens/home_screen.py", "ui/screens/input_screen.py",
    "ui/screens/solving_screen.py", "ui/screens/playback_screen.py",
    "ui/widgets/__init__.py", "ui/widgets/face_grid.py", "ui/widgets/color_picker.py",
    "renderer/__init__.py", "renderer/cube_view.py", "renderer/geometry.py",
    "renderer/mat4.py", "renderer/scene.py", "renderer/turn.py",
    "services/__init__.py", "services/solve_service.py",
]
bad = []
for p in targets:
    try:
        py_compile.compile(p, doraise=True)
    except Exception as e:
        bad.append((p, str(e)))
for p, e in bad:
    print("ERR", p, "->", e)
print("RESULT:", "OK" if not bad else "FAILED (%d)" % len(bad))
PY
