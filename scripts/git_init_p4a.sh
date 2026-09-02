#!/usr/bin/env bash
set -u
P4A=/mnt/d/coco/cube-solver/.buildozer/android/platform/python-for-android
cd "$P4A"
git init -q
git config user.email "build@local"
git config user.name "build"
git add -A
git commit -qm "imported python-for-android master"
git remote add origin https://github.com/kivy/python-for-android.git
echo "git setup done:"
git log --oneline -1
git remote -v
