# 5x5 中心求解研究

本目录保存「5x5 中心求解」的已验证实验脚本与结论，作为正式模块
`solver/center5/` 的对照与回归基线。正式迁移见 `solver/center5/solver.py`。

## 验证状态

- `exp_center_solver.py`：**20/20 随机打乱全部还原成功**（种子 `2024`，打乱长度
  从 `[5, 10, 15, 25]` 中随机选取，动作集见下）。这是本里程碑的算法基准。
- `exp_move_parity.py`：分类单次合法转动对 corner/edge 两轨道奇偶的影响。
- `exp_conj_clean.py`：验证共轭 3-cycle 对另一活动轨道完全无扰动（0/200 脏）。

## 合法动作

仅外层与两层宽转，以及各自 `''`/`'`/`2` 后缀：

```
R L U D F B        # 外层
2R 2L 2U 2D 2F 2B  # 两层宽转
```

`3R`/`4R` 等会旋转经过中面，置换六个绝对面心，为非法动作，求解器边界拒绝。

## 中心轨道结构

中心位置共 54 个，分成：

```
FIXED  6 个（六个绝对面心，固定参考件）    mags == [0,0,6]
CORNER 24 个（角/对角中心）                mags == [3,3,6]
EDGE   24 个（边/十字中心）                mags == [0,3,6]
```

轨道尺寸恒为 `[1,1,1,1,1,1,24,24]`。轨道成员由生成元自动计算（见 `orbits.py`），
不硬编码；语义名由 `kind_of_position` 按坐标绝对值给出。

## 基元动作串

见 `solver/center5/primitives.py`，官方主/备用基元：

- `CORNER_MAIN`：`2B 2D F 2D' 2B' 2D F' 2D'`，期望 cycle `(0,2,18)`
- `CORNER_BACKUP`：`2B 2L F 2L' 2B' 2L F' 2L'`，期望 cycle `(18,20,51)`
- `EDGE_MAIN`：`2B2 2D2 L2 2D2 2B2 2D2 L2 2D2`，期望 cycle `(3,5,48)`
- `EDGE_BACKUP`：`2D2 2B2 R2 2B2 2D2 2B2 R2 2B2`，期望 cycle `(1,46,52)`

每个基元在合法动作下恰好循环对应轨道 3 个中心，固定其余 21 个，完全固定另一
活动轨道与 6 个固定面心；棱/角的副作用允许（由后续阶段处理）。

## 置换方向约定（重要）

**结论：`conjugate_cycle(prim, (a,b,c))` 应用正向位置置换 `a→b, b→c, c→a`。**

为求解某轨道，需分解 **`pos → home`** 映射（`permutation[pos] = home`，即位于
位置 `pos` 的中心块最终应属于 `home`）为正向 3-cycle。注意**不要**分解
`home → pos`（会死循环）。回归测试 `test_permutation.py` 冻结了该约定：
每次分解都重新组合验证 `compose_cycles(cycles) == permutation`。

## 奇偶前缀表

corner 轨道奇偶等于**四分一转（90°）次数**的奇偶：`R`/`R'` 翻转（奇），而
`R2`/`U2`/`F2` 这类 180° 转动为**偶**（不翻转）；edge 轨道奇偶则**只被外层四分
一转**翻转（宽转 `2R` 等只翻 corner 不翻 edge）。注意：**奇偶必须从打乱后的实际
状态读取**（见 `build_pos_to_home_permutation` + `permutation_parity`），不能简单
按打乱长度推断。据此得到下表：

| 状态 `(corner_parity, edge_parity)` | 前缀 |
| --- | --- |
| `(0, 0)` | `()` |
| `(1, 0)` | `(2R)` |
| `(1, 1)` | `(R)` |
| `(0, 1)` | `(2R, R)` |

执行前缀后必须**从前缀执行后的工作魔方重新计算**两轨道 `pos -> home` 映射，
不能仅在旧映射上翻转奇偶位。前缀后两轨道奇偶应均为 0。

## 轨道独立性

两轨道共轭互相无扰动（corner 共轭 0/200 扰动 edge 中心，反向亦然），因此可按
固定顺序 `corner → edge` 独立求解。

## 运行方式

```bash
python tools/research/5x5/exp_center_solver.py
```

输出 `pass N/20`。脚本自带 `sys.path.insert` 到仓库根目录，可直接运行。
