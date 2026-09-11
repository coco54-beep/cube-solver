# 🧩 3D魔方智能还原

[English](README.md) | **中文**

> **任意打乱，放心交给它。** 一款用 Python + Kivy 写的跨平台魔方还原应用：
> 把魔方的面输进去，剩下的交给算法——从 **2 阶到 5 阶** 的智能求解（含**从零构建的 5 阶降阶法**），
> 再到 **可交互动画的 3D 回放**，全流程开箱即用。

<div align="center">

### 看它自己还原 👇

<img src="assets/demo.gif" width="300" alt="4x4 魔方求解 3D 回放动画演示" />

</div>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=flat-square)](https://www.python.org/)
[![Kivy](https://img.shields.io/badge/Kivy-2.3.1-7D66BC?logo=kivy&logoColor=white&style=flat-square)](https://kivy.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0-brightgreen?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Android-blueviolet?style=flat-square)](https://github.com/coco54-beep/cube-solver)
[![CI](https://github.com/coco54-beep/cube-solver/actions/workflows/ci.yml/badge.svg)](https://github.com/coco54-beep/cube-solver/actions/workflows/ci.yml)
[![Download APK](https://img.shields.io/github/v/release/coco54-beep/cube-solver?label=Download%20APK&logo=android&color=3DDC84)](https://github.com/coco54-beep/cube-solver/releases/latest)

---

## 🎯 它是什么

一个**真正靠算法**还原魔方的应用，不是背公式、不是查表硬解：

| 你能做到 | 它是怎么做到的 |
|---------|---------------|
| **2 阶** 秒解 | 直接映射到 3 阶色块子集走 Kociemba |
| **3 阶** 最优解 | 真实 **Kociemba 两阶段算法**，**保证 ≤ 20 步** |
| **4 阶 / 5 阶** 智能还原 | **降阶法**：中心还原 → 棱配对 → 朝向修正 → 折叠成 3 阶还原；5 阶末段用**宏级 A\*** 规划 |
| **零学习成本录入** | 展开图点格子填色，一键「随机」打乱、「校验」合法性 |
| **沉浸式 3D 回放** | OpenGL 实时渲染，拖动旋转、缩放、步进、自动播放，一步步看它还原 |
| **内置教学演示** | 按阶数收录分层法 / 七步法 / 降阶法的分步案例 |
| **跨平台** | 桌面（Windows）＋ Android（buildozer 打包），同一套代码 |

> 过程只有三步：**录入魔方 → 一键求解 → 3D 看它还原** 🎬

---

## ⚡ 实测效果

在普通 PC 上对 4 / 5 阶魔方做随机打乱，求解表现如下（数据来自本仓库的基准测试）：

| 指标 | 数值 |
|------|------|
| 3 阶求解步数 | **保证 ≤ 20 步**（Kociemba 两阶段最优界） |
| 4 阶平均步数 | **≈ 100 步**，平均耗时 **≈ 1.0 秒**（含 OLL / PLL parity 规避） |
| 5 阶平均步数 | **≈ 420 步**（非调参留出集 mean 422 / worst 453，比初版 **-41%**） |
| 5 阶平均耗时 | **≈ 2 秒**（纯 Python 热路径优化后，稳态） |
| 测试覆盖 | **813 个单测**（809 passed / 4 skipped，覆盖 2 / 3 / 4 / 5 阶） |

> 4 阶的意义不只是「能还原」，而是**把 OLL parity 从「事后修复」变成「事前规避」**——配棱完成后魔方天然处于可解态，直接省掉约 **15 步**。细节见下文算法研究。
>
> 5 阶则是**从零搭起来的降阶法**：中心用共轭 3-cycle + setup 查表、配棱用 free-slice 宏库 + 末段宏级 A\*、朝向修正用 GF(2) 线性代数，步数从初版 **~711 步压到 ~420 步**。细节见下文「5 阶降阶法研究笔记」。

---

## ✨ 核心亮点

- **真·算法求解**：2 阶直接解，3 阶走 **Kociemba 两阶段算法**（≤ 20 步），4 阶走**降阶法**（含 parity 事前规避），5 阶走**从零构建的降阶法**（中心共轭 3-cycle → free-slice 配棱 → 宏级 A\* 末段 → GF(2) 朝向修正 → 折叠 3 阶）。
- **零学习成本录入**：展开图点格子填色，支持「随机」一键载入打乱布局、**粘贴打乱公式**（如 `R U R' U'`）、「校验」实时检查状态合法性。
- **沉浸式 3D 回放**：实时渲染的 OpenGL 魔方，拖动旋转、缩放、步进、自动播放、调速度，还原过程看得清清楚楚。
- **内置教学演示**：按阶数收录分层法 / 七步法 / 降阶法的分步案例，逐个魔方状态带你去学。
- **跨平台**：桌面（Windows）＋ Android（buildozer 打包），同一套代码。
- **多语言界面（中文 / English / 日本語）· 浅/深主题**：**设置页**可切换语言与主题（**深色**、**柔和暖浅色**，或**跟随系统** Windows / Android 自动深浅）；为触屏优化的大按钮、避免误触的行间距、危险操作二次确认。

---

## 🎬 界面一览

| 页面 | 作用 |
|------|------|
| **首页** | 选择 2 / 3 / 4 / 5 阶（横屏 1×4、竖屏 2×2 卡片），进入录入、演示、帮助或设置 |
| **录入页** | 对应阶数的六个面展开图 · 6 色选择器 · 随机或粘贴打乱公式 / 校验 / 求解 |
| **求解页** | 后台多阶段求解，实时进度与阶段提示，可取消 |
| **回放页** | 3D 动画演示每一步还原，支持回到初始 / 跳结尾 |
| **演示目录** | 按阶数列出分层法 / 七步法 / 降阶法的教学案例（缩略图 + 文字） |
| **演示屏** | 逐个魔方状态的 3D 分步教学与高亮 |
| **设置页** | 切换语言（中文 / English / 日本語）与主题模式（自动 / 浅色 / 深色），查看版本信息 |

<div align="center">
  <img src="assets/screenshots/home.png" width="180" alt="首页（2/3/4/5 阶）" />
  &nbsp;&nbsp;<img src="assets/screenshots/input_4x4.png" width="180" alt="4x4 录入" />
  &nbsp;&nbsp;<img src="assets/screenshots/input_5x5.png" width="180" alt="5x5 录入" />
  &nbsp;&nbsp;<img src="assets/screenshots/playback.png" width="180" alt="3D 回放" />
  &nbsp;&nbsp;<img src="assets/screenshots/demo_menu.png" width="180" alt="演示目录" />
  &nbsp;&nbsp;<img src="assets/screenshots/demo_screen.png" width="180" alt="演示屏" />
</div>

---

## 🚀 快速开始

### 桌面（Windows）

```bash
pip install -r requirements.txt
python run_desktop.py
```

首次启动会加载求解器预计算表（`twophase/`），稍等片刻即可。

### 打包 Android

使用 [buildozer](https://buildozer.readthedocs.io/)（见 `buildozer.spec`）：

```bash
buildozer android debug
```

---

## 🧠 求解器是如何工作的

- **2 阶**：`solver/solver2.py` 直接把 2 阶映射到 3 阶色块子集走 Kociemba 求解。
- **3 阶**：`solver/solver3.py` 把录入的 54 面转换到 Kociemba 坐标系，调用 `kociemba-src/package_src/twophase` 两阶段求解，再把结果映射回本项目的记号。
- **4 阶**：`solver/solver4.py` 走降阶法 —— 先还原中心块，再配对棱块，处理特殊翻棱（parity），最后按 3 阶方式还原。还原过程按阶段回调进度，UI 实时显示。
- **5 阶**：`solver/solver5.py` 走一条完整的降阶管线 ——
  **① 中心归面**（`solver/center5`：共轭 3-cycle + setup 查表 + 同色等价）；
  **② 棱降阶**（`solver/edge5` + `solver/reduction/ref5`：free-slice 配棱，末段用宏级 A\* 把 12 条 tredge 全部归位）；
  **③ 中棱朝向修正**（`middle_orient_fix`：GF(2) 线性消去内部翻转）；
  **④ 折叠为 3×3** 后交给 Kociemba 求解，再回放到 5 阶；
  末段以「归属全 complete + 虚拟 3×3 合法」为判据，对过深打乱返回结构化失败而非输出错误解法。
- 求解在后台线程运行（`services/solve_service.py`），不阻塞界面，可随时取消。

---

## 🔬 算法研究与优化

本项目不止「能求解」——**4 阶与 5 阶降阶法的每个环节**都经过**建模、实现、实验验证与调优**。想了解技术细节的朋友，这里是重点。

<details>
<summary><b>📌 点开看：完整的 4 阶降阶法研究笔记</b></summary>

### 1. 中心还原：两阶段下降 + seeded 变体（`solver/reduction/center_solver.py`）

- 把中心状态拆成**联合位置码**（joint code）与**侧面码**（side code）两段分别求解，
  各自用预计算距离表做**下降法**（descend）逼近目标。
- `solve_centers_variant(cube, seed)` 让同构的下降可以按 `seed` 重滚出**多条等价最优解**，
  这条通道是后面规避 OLL parity 的关键。

### 2. 配棱（Edge Pairing）：交换基元 + 精确增益模拟（`solver/reduction/edge_pairing.py`）

- **交换基元 P**：`u R U R' F R' F' R u'`（9 步）。它把 `FR-bottom↔BR-top` 两翼互换，
  同时使 U 层 4 组棱块**整体轮换**（保持已配对组不变），并额外产生一个 2-cycle——
  「一次交换」因此最多能**同时配对 2~3 个槽**。
- **精确增益模拟** `_simulate_swap_gain`：不再低估或高估，而是用 24 个翼位的真实置换精确算出
  「setup + P + 逆 setup」后配对槽数的净增量（1~3），让贪心/beam 能选中真正划算的交换。
- **多目标排序**：候选交换按 `(-净增益, 压缩后净长度, setup 长度)` 排序，兼顾步数最少与一步多配对。
- **双向 setup BFS**：`_find_setup_pair` 用 meet-in-the-middle 在两种目标摆放次序下求最短 setup，
  避免单向前向搜索的指数爆炸。
- **尾段 beam 搜索** `_pair_beam_finish`：配到后期贪心易陷入局部最优，改用受限 beam
  （按压缩长度择优、允许「穿谷」）精搜尾段，预算不足自动回退贪心。

### 3. Parity 处理：从「事后修复」到「事前规避」（`solver/reduction/parity.py` + `solver4.py`）

- 4x4 的 **OLL parity（单棱翻转）** 只由「内层切片 90° 数量」的奇偶决定（`_inner_parity`）。
- 因此我们**不修、而是躲**：预先枚举多条中心解（`_CENTER_SELECT_EXTRA`），
  从中选出「内层奇偶 == 目标」的那条并重滚出对应降阶解，从而在配棱完成后 **OLL 天然为偶**，
  直接省掉约 **15 步**的 OLL 修复。该关系在 48/48 个测试状态上验证成立。
- **PLL parity（棱组置换奇偶）** 会随最后一次交换改变：尾段 beam 在预算内**优先返回
  「降阶后 3x3 直接可解」的完成态**，从而省掉 PLL repair（6 步）。

### 4. 性能优化（实测）

| 优化 | 效果 |
|------|------|
| `clone()` 由 `deepcopy` 改为逐 cubie 浅复制 | 命中最大热点，显著提速 |
| 中心择优候选数与 tail beam 规模按「步数/耗时」折中刻画 | 步数优先时保持最优步数 |
| 贪心 + 受限 beam 分层 | 在不显著劣化步数的前提下把 beam 耗时压到可控 |

> 经过实验验证，配棱基元 P 的 9 步是**满足「能完成配棱」约束下的最短可行基元**
> （更短的 `w X w'` 类候选和裸 `R2` 均无法完成配对）；交换次数已被贪心压到近下限，
> 进一步增大 beam 搜索对总步数收益已饱和。

</details>

<details>
<summary><b>📌 点开看：完整的 5 阶降阶法研究笔记（从 0 到可用）</b></summary>

5 阶没有现成库可用，这条管线是**从零建立、逐步实证**出来的：中心 → 配棱 → 朝向修正 → 折叠 3 阶。

### 1. 中心还原：共轭 3-cycle + setup 查表（`solver/center5/`）

- 把 5×5 活动中心拆成 **corner / edge 两个轨道**，各自独立求解（已实证互不扰动）。
- 任意错色位形成 **pos→home 置换**；先用极短前缀把两轨道奇偶归一化为偶，再把偶置换分解为**正向 3-cycle**，用 **「S' P S」共轭**逐一作用。
- 每个基元的 setup 只需对该轨道做**一次 BFS**（覆盖 24×23×22 = **12144** 个有序三重），之后每次共轭只查表回溯，无需重搜。
- 再做**同色等价**（只要求按颜色归面、允许同色互换），把长置换拆成更短循环，宏数量 **346 → 248（约 -28%）**。
- **已近算法 floor**：短基元穷尽、setup 已 BFS 最优；并给出结构性结论——**不存在 ≤8 步、同时只做 1 个 corner + 1 个 edge 3-cycle 的联合基元**。

### 2. 配棱：free-slice + 宏库 + 末段宏级 A\*（`solver/edge5/` + `solver/reduction/ref5/`）

- 采用 **free-slice** 思路：允许「打开自由切片时中心暂时被打乱」，用 `W + 外层动作 + W'` 的批次宏统一恢复，而不是每配一条棱就立刻复原中心。
- 把「中棱 + 两翼」的聚集关系从「是否完整」升级为 **0~3 级关系评价**，让搜索在不完整时也能判断进度。
- 末段用**宏级 A\***：抽象状态 = 每槽 `(中棱归属, 翼对归属)`，生成元为整体搬运 3-cycle、纯净中棱 3-cycle、外层 4-cycle，启发式为错配数；解出的宏序列在真实 `Cube5` 上回放并做 **center / fixed / valid 三重断言**。
- 关键判据修正：末段应以**「归属全 complete + 虚拟 3×3 合法」**为准，而非「每条 tredge 朝向都正确」（朝向为偶时虚拟 3×3 仍合法）。

### 3. 中棱朝向修正：GF(2) 线性代数（`ref5/middle_orient_fix.py`）

- `reduce5` 只保证中棱与翼的**色对**对齐，不保证同槽三块同朝向；这类「内部翻转」会被虚拟 3×3 掩盖，导致回放后仍不复原。
- 用「中棱恒等置换 + 翻转偶数个中棱」的宏词把 `d = mid_orient XOR wing_orient` 消去——朝向更新是仿射变换，问题等价于**在 GF(2) 上求掩码子集的 XOR**。朝向步数 **147 → 52（5 seeds 均值）**。

### 4. 步数与性能（实测）

| 阶段 | 平均步数 |
|------|---------|
| 中心 | ~201 |
| 配棱 | ~129 |
| 末段棱宏 + OLL | ~42 |
| 朝向修正 | ~34 |
| 3×3 | ~20 |
| **合计** | **≈ 420 步** |

- 端到端从初版 **~711 步降到留出集 mean 422 步（约 -41%）**，worst 453 / min 380，20 个非调参种子全部成功。
- 纯 Python 热路径优化：掩码空间 Dijkstra 全表只算一次、`Macro.apply` 预计算索引、以 `map` 替代 genexpr → **端到端 5.47s → 稳态 ~2.2s**。
- 调参专门留了**非调参留出集**（seeds 100-129）防止过拟合：曾把搜索预算调大但留出集无收益，最终保留步数较优的配置。

### 5. 手机端体验：随包预建表 + 后台预热

- 中心 setup 表**离线预生成并随 APK 发布**（`solver/center5/data/`，5 张共 ~2MB），设备首启直接命中、**免跑 BFS**（实测 `builds=0`）。
- 启动后台**预热线程**预加载 Kociemba 两阶段表与各阶求解器，首解不再「等半天」；并把首帧前的同步 import 移出，消除启动黑屏。

> 阶段性结论：各阶段都已接近本框架的算法上限（中心 ~200 步、配棱近 floor）；继续显著降步数需要更换根本算法（人类式 commutator 直觉搜索 / 通用 setup 求解器），当前投入产出比已很低。

</details>

---

## 📁 仓库结构

```
app/               应用入口、配置与屏幕流程（常量、字体）
ui/                Kivy 界面（kv 主题、屏幕、颜色选择器、面网格）
cube/              魔方逻辑模型（2x2 / 3x3 / 4x4 / 5x5、坐标、记号、校验）
solver/            求解逻辑（2/3 阶 Kociemba 桥接 + 4/5 阶降阶法）
  center5/         5 阶中心还原（共轭 3-cycle + setup 查表；data/ 为随包预建表）
  edge5/           5 阶配棱（free-slice、宏库、紧凑态搜索）
  reduction/ref5/  5 阶末段参考管线（宏级 A*、朝向修正、化简）
renderer/          3D 渲染（OpenGL 场景、正方体视图、转动动画）
services/          后台求解线程服务
twophase/          两阶段求解器预计算表
kociemba-src/      引用的 Kociemba 求解器源码（GPL-3.0）
tests/             单元测试（pytest）
assets/            字体、着色器与演示素材（NotoSansSC.ttf）
```

---

## ✅ 测试

```bash
python -m pytest
```

覆盖：2x2 / 3x3 / 4x4 / 5x5 转动、记号解析、输入合法性、2/3 阶 Kociemba 桥接，以及 4 阶降阶、5 阶中心（共轭/setup 表）、5 阶配棱与末段管线、朝向修正、求解进度回调等。当前 **813 个测试**（809 passed / 4 skipped）。

> 4 阶求解需要 `p4_table.bin`（约 300 MB，见仓库根目录 `.gitattributes`，通过 **Git LFS** 管理）。
> 克隆仓库后执行 `git lfs pull` 即可获取；CI 与 APK 构建都已自动处理。

---

## 📦 发布新版

打一个形如 `v1.x.x` 的 git 标签并推送，[GitHub Actions](.github/workflows/release.yml)
会自动构建 **已签名的 release APK** 并发布到 [Releases](https://github.com/coco54-beep/cube-solver/releases)：

```bash
git tag v1.2.2
git push origin v1.2.2
```

- 默认使用**临时密钥**签名（每次构建签名都会变化，旧版需先卸载）。
- 想要**固定签名**（可直接覆盖安装），在仓库 Settings → Secrets 里配置
  `ANDROID_KEYSTORE_B64`（keystore 的 base64）、`ANDROID_KEYSTORE_PASS`、`ANDROID_KEY_ALIAS`。

---

## 📄 许可

本项目以 **[GPL-3.0](LICENSE)** 发布。

> 由于 `solver/solver3.py` 直接封装并随仓库分发 **GPL-3.0** 的 Kociemba 两阶段求解器
> （`kociemba-src/package_src/twophase`），依据 GPL 的传染性条款，本项目整体须以 GPL-3.0 发布。

### 第三方资源

- `assets/fonts/NotoSansSC.ttf`：Google **Noto Sans SC** — [SIL Open Font License 1.1](https://scripts.sil.org/OFL)。
- `kociemba-src/`：Herbert Kociemba 两阶段求解器 — **GPL-3.0**（见 `kociemba-src/LICENSE`）。

---

## 🤝 贡献 & 路线

欢迎提 issue / PR。接下来值得做的方向：

- [x] 补充新版界面截图（首页 / 4×4 录入 / 3×3 录入 / 3D 回放）
- [x] 用 `git-lfs` 收纳超大预计算表，让仓库开箱可跑 4 阶
- [x] 新增 N 阶（≥5）支持（2 / 3 / 4 / 5 阶全可用）
- [x] 5 阶降阶法完整管线（中心共轭 3-cycle / free-slice 配棱 / 宏级 A\* 末段 / GF(2) 朝向修正），步数 **~711 → ~420**
- [x] 手机端求解提速：随包预建表（免 BFS）+ 后台预热 + 求解进度显示，并修复启动黑屏
- [x] 生成演示动画 GIF（`assets/demo.gif`，可用 `tools/make_demo_gif.py` 重新生成）
- [ ] 加一个有声音的引导演示视频
