# Windows 64 位便携版

下载 Release 中的 `CubeSolver-版本号-windows-x64.zip`，完整解压，打开 `CubeSolver/CubeSolver.exe`。`_internal` 是程序依赖和离线求解数据，须与可执行文件一起保留。用户设置仍保存在个人账户目录。

## 从源码构建

在 Windows 上使用 64 位 Python 3.10：

```powershell
git lfs pull
python -m pip install -r requirements.txt pyinstaller==6.22.0
python scripts/build_windows.py
```

构建脚本使用 [Kivy 官方的 PyInstaller 打包方式](https://kivy.org/doc/stable/guide/packaging-windows.html)，包含 SDL2、ANGLE、GLEW、NumPy、中文字体、界面资源以及离线求解表。四阶数据必须是完整的 LFS 文件。

输出在 `bin`：便携 ZIP、SHA-256 校验文件和构建清单。脚本逐个核对包内资源，随后从不同的工作目录启动打包后的程序，执行普通 3／4／6／17 阶及部分异形的求解回放，并检查高阶五魔方的预计算数据。该检查不包含对所有界面的人工操作。

GitHub 的 Windows Release 工作流在推送 `v版本号` 标签后执行同一构建与核对，全部通过才上传 ZIP。
