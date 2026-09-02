# 3D魔方智能还原 (3D Rubik's Cube Solver)

一个基于 **Python + Kivy** 的跨平台魔方还原应用：录入魔方六个面的颜色，程序自动求解，并用 3D 动画演示还原过程。支持 3 阶与 4 阶魔方。

## 功能

- **6 面录入**：展开图点位逐个填入颜色，支持「随机」快速载入一个打乱布局、「校验」检查状态是否合法。
- **智能求解**：
  - 3 阶：Kociemba 两阶段（Twophase）算法，路径在 20 步以内。
  - 4 阶：降阶法（中心求解 → 棱块配对 → 特殊翻棱 → 按 3 阶还原）。
- **3D 回放**：拖动旋转视角、滚轮/双指缩放；支持上一步 / 下一步 / 自动播放 / 跳到结尾 / 回到初始 / 速度调节。
- **6 色颜色选择**：当前选中颜色高亮，点击格子直接填色。
- **界面**：深色主题，中文界面。

## 平台

- **桌面**：Windows（`run_desktop.py`），Kivy + OpenGL。
- **Android**：用 [buildozer](https://buildozer.readthedocs.io/) 打包（`buildozer.spec`）。

## 运行（桌面）

```bash
pip install -r requirements.txt
python run_desktop.py
```

首次会加载求解器预计算表（`twophase/` 下），可稍等片刻。

## 运行测试

```bash
python -m pytest
```

## 求解器说明

- 3 阶求解依赖 `kociemba-src/package_src/twophase`（Herbert Kociemba 的两阶段求解器，**GPL-3.0**，已随仓库提供）。
- 4 阶求解为本项目自研的降阶法，位于 `solver/`；其运行所需的预计算表由 `twophase/` 目录提供。
- 超出 GitHub 单文件限制的巨型表（如 `p4_table.bin`，约 300MB）未随仓库提交，如需可自行用 `kociemba-src/generate_tables.py` 生成。

## 仓库结构

```
app/         应用入口与配置（屏幕流程、常量、字体）
ui/          Kivy 界面（kv 主题、各屏幕、颜色选择器、面网格）
cube/        魔方逻辑模型（3x3 / 4x4、坐标、记号、校验）
solver/      求解逻辑（Kociemba 桥接 + 4x4 降阶）
renderer/    3D 渲染（OpenGL 场景、正方体视图、动作动画）
services/    后台求解线程服务
twophase/    两阶段求解器预计算表
kociemba-src/ 引用的 Kociemba 求解器源码（GPL-3.0）
tests/       单元测试
assets/      字体与着色器（NotoSansSC.ttf）
```

## 许可

本项目以 **GPL-3.0** 许可发布（见 `LICENSE`）。

> 由于 `solver/solver3.py` 直接封装并随仓库分发 **GPL-3.0** 的 Kociemba 两阶段求解器（`kociemba-src/package_src/twophase`），依据 GPL 的传染性条款，本项目整体须以 GPL-3.0 发布。

### 第三方资源

- `assets/fonts/NotoSansSC.ttf`：Google **Noto Sans SC**，使用 [SIL Open Font License 1.1](https://scripts.sil.org/OFL)。
- `kociemba-src/`：Kociemba 两阶段求解器，**GPL-3.0**（见 `kociemba-src/LICENSE`）。
