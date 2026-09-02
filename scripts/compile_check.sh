#!/usr/bin/env bash
set -u
cd /mnt/d/coco/cube-solver
echo "=== compile all project .py (excluding scripts with .sh) ==="
python3 - <<'PY'
import os, py_compile, sys
bad = []
for root, dirs, files in os.walk('.'):
    # 跳过排除目录
    if any(p in root for p in ('.buildozer', '.git', '__pycache__', '.pytest_cache', 'scripts', 'tests', 'kociemba-src')):
        continue
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                py_compile.compile(p, doraise=True)
            except Exception as e:
                bad.append((p, str(e)))
if bad:
    print("SYNTAX ERRORS:")
    for p, e in bad:
        print(" ", p, "->", e)
else:
    print("ALL .py COMPILE OK")
PY
