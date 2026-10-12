# Windows 桌面启动与 OpenGL 1.1

当日志显示 `Backend used <glew>`、`Microsoft Corporation / GDI Generic`、
`OpenGL version 1.1.0` 时，Kivy 会在应用加载前终止，因为最低要求是 OpenGL 2.0。
这发生在窗口初始化阶段。

`run_desktop.py` 和 `main.py` 现在都在导入 Kivy 前调用
`app.desktop_runtime.configure_graphics()`。Windows 环境已安装
`kivy_deps.angle` 和 `kivy_deps.sdl2` 时，默认选择 `angle_sdl2`，并使用 SDL2
创建窗口。[Kivy 官方后端说明](https://kivy.org/doc/stable/api-kivy.graphics.cgl.html)
列出了这一配置及所需依赖。Android 与其他平台继续使用各自默认后端。

用户提供的 Python 3.10 日志已确认两项依赖均成功导入；本机对应 ANGLE
目录也有 `libEGL.dll`、`libGLESv2.dll` 和 `d3dcompiler_47.dll`。

再次用原来的解释器启动 `run_desktop.py`。正常配置应先打印
`Windows graphics backend = angle_sdl2`，后续图形日志应使用 ANGLE。

显式设置的 `KIVY_GL_BACKEND` 会保留；如果 IDE 的运行配置之前强制设为了
`glew`，需要移除该项或改为 `angle_sdl2`。本次没有运行窗口启动测试，因此
仍需重新启动以确认该机器上的 ANGLE 图形上下文是否成功建立。
