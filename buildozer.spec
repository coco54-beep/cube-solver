[app]

# ----------------------------------------------------------------------------
# 应用元信息
# ----------------------------------------------------------------------------
title = 3D魔方智能还原
package.name = cubesolver
package.domain = com.example
version = 1.0.0

# 工程源码目录（buildozer 会把它拷贝进打包环境）
source.dir = .
source.include_exts = py,kv,png,jpg,json,txt,bin,md,ttf

# 额外包含的无后缀文件（twophase 预生成表）
source.include_patterns = assets/solver_tables/*,twophase/*,joint_dist.bin,p4_table.bin

# 打包时排除：构建脚本目录、探索/调试脚本、git
source.exclude_dirs = scripts,.git,.buildozer,__pycache__,.pytest_cache,tests
source.exclude_patterns = dev.py,discover.py,explore_*.py,find_primitive.py,probe_*.py,search_*.py,deep_ud.py,table_gen*.log,pytest.ini

# ----------------------------------------------------------------------------
# 构建需求
# ----------------------------------------------------------------------------
requirements = python3,kivy==2.3.1

# 竖屏
orientation = portrait
fullscreen = 0

# 架构（arm64 为主，兼容 armeabi-v7a）
android.archs = arm64-v8a,armeabi-v7a
android.minapi = 26
android.api = 33
android.ndk_api = 26

# 图标（如无则跳过）
# icon.filename = assets/icons/%source.name%.png

# 权限：离线求解无需网络/存储
android.permissions = INTERNET

# 自动接受 Android SDK 许可证
android.accept_sdk_license = True

# python 打包选项
android.entrypoint = main.py
android.allow_backup = True

# ----------------------------------------------------------------------------
# buildozer 输出
# ----------------------------------------------------------------------------
[buildozer]
log_level = 2
warn_on_root = 0
