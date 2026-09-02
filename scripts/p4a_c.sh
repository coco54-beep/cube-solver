#!/usr/bin/env bash
set -u
B=/mnt/d/coco/cube-solver/.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2
echo "=== find main.c / py main launcher ==="
find "$B" -name "main.c" -o -name "*.c" 2>/dev/null | grep -iE "main|sdl" | head
echo "=== grep run / import / SDL_main / PyImport in c files ==="
find "$B" -name "*.c" 2>/dev/null | while read f; do
  grep -l "main.py\|PyImport\|SDL_main\|py_main" "$f" 2>/dev/null
done | head
