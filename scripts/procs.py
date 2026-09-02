#!/usr/bin/env bash
echo "=== buildozer/p4a procs ==="
ps aux | grep -E "buildozer|pythonforandroid|toolchain" | grep -v grep | head
echo "=== log mtime + size ==="
stat -c '%y' /mnt/d/coco/cube-solver/build_apk.log 2>/dev/null
wc -c /mnt/d/coco/cube-solver/build_apk.log 2>/dev/null
echo "=== feeder procs ==="
ps aux | grep -E "sleep 5400|sleep 540" | grep -v grep | head
