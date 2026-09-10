#!/bin/bash
ADB=/root/android-sdk/platform-tools/adb
APK=/mnt/d/coco/cube-solver/bin/cubesolver-1.0.0-x86_64-debug.apk
OUT=/mnt/d/coco/cube-solver/_shots
mkdir -p $OUT
$ADB shell wm size 1080x1920
$ADB shell wm density 420
sleep 2
$ADB install -r $APK 2>&1 | tail -1
$ADB logcat -c
$ADB shell am start -n com.example.cubesolver/org.kivy.android.PythonActivity 2>&1
sleep 15
# 首页 -> 演示按钮(中部, 使用说明上方) -> 演示页
$ADB shell input tap 540 1180
sleep 4
$ADB exec-out screencap -p > $OUT/demo1.png 2>/dev/null
# 播放公式
$ADB shell input tap 540 1780
sleep 5
$ADB exec-out screencap -p > $OUT/demo_play.png 2>/dev/null
# 下一个案例
$ADB shell input tap 890 1780
sleep 4
$ADB exec-out screencap -p > $OUT/demo_next.png 2>/dev/null
$ADB shell pidof com.example.cubesolver
ls -la $OUT/demo1.png $OUT/demo_play.png $OUT/demo_next.png
