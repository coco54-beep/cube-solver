#!/usr/bin/env bash
pkill -f "buildozer" 2>/dev/null
pkill -f "sleep 5400" 2>/dev/null
pkill -f "pythonforandroid.toolchain" 2>/dev/null
sleep 2
echo "remaining:"
ps aux | grep -E "buildozer|toolchain|sleep 5400" | grep -v grep | head
