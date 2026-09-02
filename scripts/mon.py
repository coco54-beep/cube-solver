#!/usr/bin/env bash
ps aux | grep -E "buildozer|p4a|python" | grep -v grep | head -20
echo "--- log size ---"
wc -c /mnt/d/coco/cube-solver/build_apk.log 2>/dev/null
echo "--- tail ---"
tail -15 /mnt/d/coco/cube-solver/build_apk.log 2>/dev/null
