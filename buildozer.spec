[app]

# ----------------------------------------------------------------------------
# 应用元信息
# ----------------------------------------------------------------------------
title = 3D魔方智能还原
package.name = cubesolver
package.domain = com.example
version = 1.2.2

# 工程源码目录（buildozer 会把它拷贝进打包环境）
source.dir = .
# 注意：扩展名过滤在 pattern 匹配之后无条件生效，include_patterns 只能取消排除、
# 不能新增扩展名。故 .pkl 必须列在 include_exts 里，否则会被丢弃。
source.include_exts = py,kv,png,jpg,json,txt,bin,md,ttf,pkl

# 额外包含的无后缀文件（twophase 预生成表；这些文件无扩展名，靠 pattern 通过）
source.include_patterns = assets/solver_tables/*,twophase/*,joint_dist.bin,p4_table.bin

# 打包时排除：构建脚本目录、研究/实验脚本、git
source.exclude_dirs = scripts,tools,experiments,_shots,.git,.buildozer,__pycache__,.pytest_cache,tests
source.exclude_patterns = table_gen*.log,pytest.ini,*.log

# ----------------------------------------------------------------------------
# 构建需求
# ----------------------------------------------------------------------------
requirements = python3,kivy==2.3.1

# 竖屏
orientation = portrait
fullscreen = 0

# 架构（arm64 为主；v7a 已放弃，绝大多数新机型都是 64 位）
android.archs = arm64-v8a
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
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 0
