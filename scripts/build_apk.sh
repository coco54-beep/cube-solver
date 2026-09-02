#!/usr/bin/env bash
set -u
export VIRTUAL_ENV=/opt/buildvenv
export PATH=/opt/buildvenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /mnt/d/coco/cube-solver
# 先喂一个 y 应对 root 提示，再保持 stdin 打开以防后续交互
( echo y; sleep 5400 ) | buildozer android debug > /mnt/d/coco/cube-solver/build_apk.log 2>&1
echo "buildozer exited: $?"
