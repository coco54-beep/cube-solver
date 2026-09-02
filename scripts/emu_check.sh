#!/usr/bin/env bash
set -u
SDK=/root/.buildozer/android/platform/android-sdk
echo "=== emulator binary ==="
ls "$SDK/emulator/emulator" 2>/dev/null && echo "emulator present" || echo "NO emulator"
echo "=== system images ==="
ls "$SDK/system-images" 2>/dev/null
echo "=== avds ==="
ls ~/.android/avd 2>/dev/null
echo "=== avdmanager ==="
ls "$SDK/cmdline-tools" 2>/dev/null
