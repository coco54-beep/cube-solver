#!/usr/bin/env bash
set -u
D=/mnt/d/coco/cube-solver/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/dists/cubesolver
echo "=== find main.c in dists ==="
find "$D" -name "main.c" 2>/dev/null | head
echo "=== jni application src ==="
find "$D/jni" -maxdepth 3 -name "*.c" -o -maxdepth 3 -name "*.cpp" 2>/dev/null | head
echo "=== grep for main.py / py run embedded ==="
grep -rn "main.py\|PyRun\|py_run\|import main\|python main" "$D/jni" 2>/dev/null | head
