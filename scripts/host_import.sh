#!/usr/bin/env bash
set -u
# 用 p4a 的 hostpython3 导入应用包，排查运行时 import 错误
HOSTPY=/mnt/d/coco/cube-solver/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/build/other_builds/hostpython3/desktop/hostpython3/native-build/root/usr/local/bin/python
cd /mnt/d/coco/cube-solver
echo "=== host python version ==="
"$HOSTPY" --version 2>&1 | head -2
echo "=== import app chain ==="
"$HOSTPY" - <<'PY'
import os, sys
sys.path.insert(0, '.')
mods = [
    'app', 'app.application', 'app.config', 'app.constants', 'app.fonts',
    'ui', 'ui.screens', 'ui.screens.home_screen', 'ui.screens.input_screen',
    'ui.screens.solving_screen', 'ui.screens.playback_screen',
    'ui.widgets', 'ui.widgets.face_grid', 'ui.widgets.color_picker',
    'renderer', 'renderer.cube_view', 'renderer.geometry', 'renderer.mat4',
    'renderer.scene', 'renderer.turn',
    'services', 'services.solve_service',
    'primitives',
]
for m in mods:
    try:
        __import__(m)
        print("OK  ", m)
    except Exception as e:
        import traceback
        print("FAIL", m, "->", type(e).__name__, e)
        traceback.print_exc()
PY
