#!/usr/bin/env bash
set -u
GRADLE_ZIP=/mnt/d/coco/cube-solver/gradle-8.14.3-all.zip
echo "downloading gradle-8.14.3-all.zip from huaweicloud..."
timeout 600 curl -sSL -o "$GRADLE_ZIP" "https://mirrors.huaweicloud.com/gradle/gradle-8.14.3-all.zip"
echo "size: $(du -h "$GRADLE_ZIP" | cut -f1)"
# 验证 zip
unzip -t "$GRADLE_ZIP" >/dev/null 2>&1 && echo "zip OK" || echo "zip BAD"
