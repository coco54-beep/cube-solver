#!/usr/bin/env bash
set -u
PLAT=/mnt/d/coco/cube-solver/.buildozer/android/platform
mkdir -p "$PLAT"
cd "$PLAT"
rm -rf python-for-android p4a.tgz
echo "Downloading python-for-android (master)..."
timeout 300 curl -sSL -o p4a.tgz "https://codeload.github.com/kivy/python-for-android/tar.gz/refs/heads/master"
echo "downloaded size: $(du -h p4a.tgz | cut -f1)"
tar xzf p4a.tgz
mv python-for-android-master python-for-android
echo "extracted. Contents:"
ls python-for-android | head
