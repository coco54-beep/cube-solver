#!/usr/bin/env bash
grep -n -E "SyntaxError|File \"\.buildozer/android/app" /mnt/d/coco/cube-solver/build_apk.log | grep -B0 -A0 "SyntaxError" | head -40
echo "=== 报错文件 ==="
grep -n -E "File \"/mnt/d/coco/cube-solver/\.buildozer/android/app" /mnt/d/coco/cube-solver/build_apk.log | grep -iE "syntaxerror|line [0-9]+" | head -40
