#!/usr/bin/env bash
set -u
P=/mnt/d/coco/cube-solver/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/dists/cubesolver/gradle/wrapper/gradle-wrapper.properties
# 用本地 file URL 替换 distributionUrl
sed -i 's#distributionUrl=.*#distributionUrl=file\\:///mnt/d/coco/cube-solver/gradle-8.14.3-all.zip#' "$P"
echo "=== updated ==="
grep distributionUrl "$P"
