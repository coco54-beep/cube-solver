#!/usr/bin/env bash
set -u
cd /tmp
rm -rf apkcheck
mkdir apkcheck
cd apkcheck
unzip -q /mnt/d/coco/cube-solver/bin/cubesolver-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
echo "=== root ==="
ls
echo "=== lib/ ==="
ls -R lib 2>/dev/null | head -40
echo "=== assets/private top ==="
ls assets/private 2>/dev/null | head -40
echo "=== fonts + tables present? ==="
find assets -iname "*.ttf" -o -iname "joint_dist.bin" -o -iname "p4_table.bin" 2>/dev/null
echo "=== twophase dir? ==="
ls assets/private/twophase 2>/dev/null | head
