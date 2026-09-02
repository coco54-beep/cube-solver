#!/usr/bin/env bash
set -u
B=/mnt/d/coco/cube-solver/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a
rm -rf "$B/build/venv"
echo "removed build/venv; remaining build dirs:"
ls "$B/build" 2>/dev/null
