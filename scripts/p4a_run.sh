#!/usr/bin/env bash
set -u
P=/mnt/d/coco/cube-solver/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/src/main/java/org/kivy/android/PythonActivity.java
echo "=== pythonMain / run related ==="
grep -n "main.py\|run\|python\|import\|PYTHONPATH\|pythonpath\|bootstrap" "$P" | grep -iE "run|main\.py|pythonpath|import" | head -30
echo "=== find the python launcher in jni ==="
find /mnt/d/coco/cube-solver/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2 -iname "*.c" -o -iname "*.cpp" -o -iname "*.h" 2>/dev/null | head
