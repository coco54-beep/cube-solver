#!/usr/bin/env bash
set -u
P4A=/mnt/d/coco/cube-solver/.buildozer/android/platform/python-for-android
echo "=== grep for entrypoint / python_main / import ==="
grep -rn "entrypoint\|python_main\|main.py\|PyImport" "$P4A/pythonforandroid/bootstraps/sdl2/" 2>/dev/null | grep -viE "\.pyc|comment" | head -30
echo "=== python_main.c ==="
find "$P4A/pythonforandroid/bootstraps/sdl2" -name "python_main*" 2>/dev/null
