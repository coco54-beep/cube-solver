#!/usr/bin/env bash
echo "=== buildozer/toolchain procs ==="
ps aux | grep -E "buildozer|pythonforandroid" | grep -v grep | head -3
echo "=== bin ==="
ls -lh --time-style=+%H:%M /mnt/d/coco/cube-solver/bin/*.apk 2>/dev/null
