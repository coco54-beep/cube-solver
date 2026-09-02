#!/usr/bin/env bash
set -u
# 清理进程
pkill -f "buildozer" 2>/dev/null
pkill -f "sleep 5400" 2>/dev/null
pkill -f "pythonforandroid.toolchain" 2>/dev/null
sleep 2
# 清理 app 暂存（让 buildozer 重新复制带 __init__.py 的源码）
rm -rf /mnt/d/coco/cube-solver/.buildozer/android/app
echo "cleaned app staging; buildozer/p4a procs:"
ps aux | grep -E "buildozer|toolchain" | grep -v grep | head
