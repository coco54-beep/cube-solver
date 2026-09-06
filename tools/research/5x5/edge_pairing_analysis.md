# 5x5 棱配对（Edge Pairing）前期分析

> 对应里程碑：**棱位置模型 + 轨道/朝向分析 + 配对基元搜索 + 真实 Cube5 重放验证**。
> 本文件记录在本阶段测得的全部结论；这些结论冻结了配对阶段的结构约束，供后继配对器设计使用。

坐标约定：5x5 `maxc=6, d=3`，坐标取值 `{-6,-3,0,3,6}`（见 `cube/coordinates.py`）。
面轴：`0=X(R/L) 1=Y(U/D) 2=Z(F/B)`。面法线见 `FACE_NORMALS`。

---

## 1. 棱位置模型（已验证）

还原态下共有 **36 个棱块**（贴 2 面），按坐标绝对值分为两类：

| 类型 | 坐标特征 | 数量 |
|------|---------|------|
| 中棱（middle） | 恰好 2 个坐标 ±6，第三坐标 0 | 12 |
| 翼（wing） | 恰好 2 个坐标 ±6，第三坐标 ±3 | 24 |

每条**逻辑棱**（连接两个面的棱）由 `1 个中棱 + 2 个翼` 组成，共 12 条逻辑棱：

- 12 条逻辑棱名与 4x4 `SLOTS` 相同：`FU RU BU LU FD RD BD LD FR BR FL BL`。
- 每条逻辑棱的 3 个成员共享同一**色对**（该棱两个面的颜色）。
- 例：`RU` 逻辑棱 → 中棱 `(6,6,0)`，两翼 `(6,6,-3)` 与 `(6,6,3)`，色对 `{R_U_color, U_U_color}`。
- 每个色对在全立方中恰有 **1 个中棱 + 2 个翼**（两翼为该色对仅有的两份）。

---

## 2. 轨道分析（已验证）

在全部合法动作（外层 `R/L/U/D/F/B` + 两层宽转 `2R/…`，各含 `''/'/2`）作用下，
用 union-find 对 36 个棱位置做轨道划分，得 **恰好 2 个轨道**：

```
轨道 1：24 个翼位（每条逻辑棱的 2 翼位属于同一轨道）
轨道 2：12 个中棱位
```

结论（重要）：

- **翼与中棱分属两个互不连通、各自封闭的轨道**。翼块永不可能移动到中棱位，反之亦然。
- 这一分离在「仅外层」与「仅两层宽转」下**各自成立**（两种情况都同样 24/12 分离）。
- 因此：**中棱子系统和翅膀子系统是两块独立的钟摆**，配对可分别规划，但见 §5 的联动耦合。

---

## 3. 朝向 / 配对一致性分析（已验证）

定义每条逻辑棱的「配对完成」：其 3 个成员的 **color→face 映射完全一致**
（即同色必贴同一面）。这是能否降阶成合法 3x3 边块的判据。

测得：

- **还原态**：12 条逻辑棱全部一致。
- **随机打乱（中心已还原）后**：多数情况只有 0~3/12 条逻辑棱一致。

对「该槽两翼位都被 home 色对占据」的槽做统计（120 次随机、30 步）：

| 成因 | 次数 |
|------|------|
| 两翼彼此朝向不同（翼翻转） | **0** |
| 槽内中棱不是 home 色对的中块 | 6 |

**决定性结论**：

- 任一色对的 **2 片翼永远彼此朝向一致**（`wings_flip` 恒为 0）。翼片的朝向是**固定的**，
  两翼之间**不存在翻面差异**。原因：翼在位时其两 sticker 必然指向该槽的两个面，
  色到面的指派由该翼的物理体固定，且同一色对的两翼内在同向。
- 逻辑棱不一致的**唯一来源是放错了中棱**（`middle_mismatch`）。
- 因此 **5x5 配棱退化为纯位置指派问题**：
  > 每条逻辑棱必须恰好装入其 home 色对的 1 中棱 + 2 翼；装齐即自动一致，无需处理翼翻面。

---

## 4. 中棱 / 翼的孤立解决可行性

由于翼与中棱分处两个封闭轨道，且朝向固定，可各自看作独立置换：
- 中棱：12 个中位置上的 12 个置换；
- 翼：24 个翼位置上的 24 个置换（每色对两翼可互换，等价于配对问题）。

理论上均可用「3-cycle + 共轭」把所需件搬入目标位（与中心解法同构）。
**但 §5 的联动耦合使「干净」基元稀缺**。

---

## 5. 联动耦合（关键发现，实测）

与 4x4（无中棱）不同，5x5 的**每一个合法动作都会同时移动中棱和翼**：

```
move_U  -> wings 8 器, middles 4
move_R  -> wings 8, middles 4
move_2U -> wings 12, middles 4
move_2R -> wings 12, middles 4
...
```

即：中棱与翼在单步移动中被**强制联动**。

进一步实测搜索「干净」基元：

- **middle 归位 + 翼 3-cycle**：BFS（≤10 万节点、深度≤12）**未找到任何**序列（0 个）。
- **短翼 3-cycle**：随机搜索（4 万序列）与 BFS **均未找到**。
- **中棱 3-cycle 存在但联动**：例如 `B U' 2B' U`（长 4）给出干净的中棱
  `(6,6,0)→(0,6,-6)→(6,0,-6)→(6,6,0)` 3-cycle，但**同时移动 9 片翼**，
  并使 4 条逻辑棱（DL/BU/FU/DR）失去一致性。

**重要性**：5x5 不存在「只动翼不动中棱」或「只动中棱不动翼」的短复合基元，
且在棱子系统上**单个翼 3-cycle 无法以短序列达成**。这意味着 5x5 配棱必须被当作
**耦合系统**处理（与中心解法可完全解耦、逐轨道独立求解的情形不同）。

---

## 6. 后续建议（进入配对器设计）

1. 采用**整体逻辑棱迁移**：把「整条逻辑棱的内容（1 中 + 2 翼）作为一个单元做 3-cycle」，
   而不是单独搬翼。这种整体 3-cycle 更可能保持各槽内部一致性。
2. 或采用**自由切片（free-slice）法**：以 U 层（或某层）作为 buffer，共享地搬动
   「中+翼」联动的槽，逐条把色对收敛到 home 逻辑棱。
3. 必须先解决**联动耦合**：要么设计「整棱」基元，要么把「中棱归位」与「翼配对」
   作为可交替推进的两个子目标，用双向/beam 搜索在耦合空间中收敛。
4. 配对完成后生成 reduced 3x3 状态（复用 `solver/reduction/reduced_cube.py` 思路），
   再走 `solve_3x3`，最后 `solver5.py` 端到端回放。
5. 5x5 特有的**最后两条棱 / 棱配对奇偶**需单独建模（联动耦合加剧奇偶结构）。

---

## 7. 参考脚本（tools/research/5x5/）

| 脚本 | 内容 |
|------|------|
| `exp_edge_model.py` | 36 棱块分类与 12 逻辑棱位置模型 |
| `exp_edge_orbit.py` | 36 位置在合法动作下的轨道划分（24 翼 / 12 中） |
| `exp_edge_consistency.py` / `exp_wing_flip_check.py` | 配对一致性 / 翼翻转统计 |
| `exp_wing_flip_detail.py` | 不一致槽的成因分解（中棱错位，非翼翻面） |
| `exp_move_analysis.py` | 单动作对 W/M 的联动 |
| `exp_clean_wing_bfs.py` / `exp_wing3cycle_search.py` / `exp_mid3cycle_rand.py` | 干净基元搜索 |
| `exp_verify_mid3.py` | 在真实 Cube5 重放验证候选基元 |

---

## 8. 交付状态（Milestone 1 + Milestone 2，已入库）

### M1：配对状态模型 + 动作影响表（已交付并测试）

包 `solver/edge5/`：

| 模块 | 内容 |
|------|------|
| `positions.py` | 36 棱稳定编号（`MIDDLE_ORDER` 12 / `WING_ORDER` 24）、12 逻辑槽
`SLOTS`（UF UR UB UL DF DR DB DL FR FL BR BL）、`LogicalEdgeSlot(middle,left_wing,right_wing)`、
`edge_type_of_cubie`（frozenset 色对）、`color_pair_of_slot`、`is_middle_pos`/`is_wing_pos`/
`slot_of`/`edge_positions` |
| `state.py` | `is_edge_paired`（同色对 3 成员聚集同槽，不要求 home）、`is_edge_solved`（配对且回 home）、
`paired_count`/`solved_count`/`all_edges_paired`/`all_edges_solved`、`edge_type_at`、`face_colors` |
| `moves.py` | `EdgeMoveEffect`（middle_perm 12 / wing_perm 24 / touched_slots / group_moved_whole /
group_split / fixed_face_centers_preserved / inverse_restores）、`build_edge_move_effects` |
| `__init__.py` | 公开 API 导出 |

**关键实现结论（发现并修正了初期的错误判断）：**

- **轨道闭合**：翼（24）与中棱（12）是互不相通的封闭轨道；每个动作同时移动两者。
  （`test_orbit_closure` 在 10 个 20 步随机打乱下验证翼、中棱各自不改轨道。）
- **朝向一致性**：不一致槽全部由「middle 放错」引起（6/6 middle_mismatch，**0 wings_flip**）；
  同色对 2 翼永远彼此一致。因此**配棱退化为纯位置指派**（装入 home 色对的 1 中 + 2 翼即自动一致）。
  `typ_eq == paired` 实测证实。
- **语义分离**：`is_edge_paired`（聚集同槽）与 `is_edge_solved`（回 home）解耦；顶层只要求 `all(is_edge_paired)`。
  在随机打乱下能观测到 `paired > solved` 的分离态（`test_semantic_separation`）。
- **动作影响表与真实 Cube5 一致**：`test_effect_consistent_with_cube` 对全部 36 个合法动作比对
  middle_perm/wing_perm 与真实引擎重放，全一致；`inverse_restores`、`fixed_face_centers_preserved` 全真。
- **外层 vs 宽层**：外层（R/U）整组搬运（group_split 0，touched 4）；宽层（2R/2U）拆散工作区 4 组
  （group_split 4，touched 8）——这是自由切片/belt 法的直接依据。
- **关键修正（中心评价指标）**：必须区分**中心块身份位移**与**中心按颜色归面**。
  - `center_identity_off`：统计单贴面块是否回到唯一 home 槽。外层动作会旋转同面 8 个活动中心 → 身份
    位移 >0（如 R 得 8）。
  - `center_color_off`：统计「所在面颜色」≠「该块自身颜色」的块数。外层动作只置换同面中心身份、
    不改面色 → **0**（`centers_are_color_solved` 为真）；两层宽转会跨面色 → >0（如 2R 得 12）。
  - **因此「外层动作也破坏中心」的早期结论需修正为**：外层动作只扰动同面中心身份，**不破坏按颜色归面**；
    真正破坏面色的是宽层造成的跨面颜色错位。降阶求解的中心恢复目标应使用 `centers_are_color_solved`
    （颜色归面），而非全部单贴面块回到唯一 home 槽（`center_identity_off==0`）。配棱搜索把
    `center_identity_off` 当代价会施加不必要的约束。
  - 新增 `state.py` 的 `center_color_off` / `center_identity_off` / `centers_are_color_solved` / `face_of_position`
    及回归测试 `TestCenterColorVsIdentity`（外层保面色、宽层破坏面色）。

### M2：单条棱构造原型（`solver/edge5/solver.py`，已交付但为研究原型）

`SingleEdgePairResult(success, target, work_slot, moves, centers_restored, target_paired,
error_code, message, nodes_explored)`；

`pair_single_edge(cube, target, work_slot, max_depth=24, beam_width=300, node_budget=2_000_000)`。

- **模型**：紧凑状态（中/翼/中心三置换 [mid, wing, cen]）+ 预计算 `_MOVE_TABLES`，避免整立方体克隆，单次配对约 0.1–2s（旧全立方体克隆 beam 为 8s+）。
- **搜索**：受限 beam，评分 `matched*1000 - color_off*1 - depth`；目标达成须同时
  `matched==3`（工作槽含目标 1 中 + 2 翼）**且** `color_off==0`（中心按颜色归面），并以真实 Cube5 重放
  校验 `is_edge_paired(work_slot)`、`centers_are_color_solved`、六个固定面心原位、动作全合法、输入不被修改。
- **能力（实测成功基线，`node_budget=150000`，每深度 10 seed）**：
  | 打乱长度 | 成功 | 说明 |
  |---|:---:|---|
  | ≤3 | 10/10 | 可靠 |
  | 4–6 | 4/10–6/10 | 部分成功（种子相关） |
  | ≥8 | 0/10–1/10 | 多数失败，返回 `SEARCH_LIMIT_REACHED` / `SEARCH_BUDGET_EXHAUSTED` |
  - solved 输入 → 返回成功、空动作。
  - 已校验：所有成功结果重放一致、动作合法、目标配对、中心按颜色归面、输入不被修改（24/24 验证通过）。
- **已知限制（明确记录）**：
  1. **联动耦合陷阱（本质）**：目标需同时达成「匹配=3」与「中心颜色=0」，而中心归位常须先临时打散
     已匹配的 3 成员（穿过评分「山谷」）。单调上升的 beam 会卡在此联合态。
  2. **两阶段实验（gather→restore）结论**：单独「Gather」（弃中心约束、只求 matched==3）非常可靠
     （n=15 仍 8/8）；但「Restore」（保持 3 成员聚集同时把中心颜色降到 0）在 n≥10 基本失败——
     因为真正的中心恢复本身要求与棱动作交织（需临时拆散），无法与「保持聚集」硬约束兼得。
     所以两阶段各自独立推进并不能解决深层打乱；仍须设计「整棱」基元或真正的穿谷搜索。
  3. 尚未保护其它已配棱（Milestone 3），任意深入打乱的单棱构造会扰动先前结果。
  4. **可改进方向**：穿谷容许的搜索（允许暂时降到 matched<3 再回升）、双向搜索、或设计「整棱」基元
     ——与前期「须先解决联动耦合」结论一致。

### 测试

`tests/test_edge5.py`（M1+M2，含中心颜色/身份区分回归，共 47 项）：位置模型 / 色对无色序 /
轨道闭合 / 语义分离 / EdgeMoveEffect 一致性（solved、单动作、逆动作、36 动作全表）/
M2 solved 空链 / 受控短打乱可靠构造 / 深入打乱失败错误码 / 未知工作槽报错 /
`TestCenterColorVsIdentity`（外层保面色、宽层破坏面色）。全量回归 `pytest` 通过（本轮 430 项）。


### M2.5：联合紧凑状态 + 穿谷分桶 beam（solver/edge5/compact_state.py + single_edge.py）

新增模块（不修改 M2 的 solver.py，二者并存）：
- compact_state.py：CompactPairingState（中/翼/中心三位置置换），state_of/step/color_off/
  matched/work_paired/score_state/bucket_key/target_home_slot，及 MOVES/MOVE_TABLES 表。
- single_edge.py：pair_single_edge_valley 穿谷分桶 beam，SearchLimits(max_nodes, max_depth,
  timeout_seconds, beam_width, per_bucket)，ValleySingleEdgeResult，失败错误码
  NODE_LIMIT/DEPTH_LIMIT/TIME_LIMIT/FRONTIER_EXHAUSTED/ABSTRACTION_REPLAY_MISMATCH、
  以及 TARGET_NOT_FOUND。目标=is_edge_paired(target)&centers_are_color_solved。

设计要点：
- 单一联合目标，允许中途退回（目标重新拆散、中心错位暂时增加、匹配数降到 2/1/0）。
- 分桶保留多样性：按 (matched 档, 中心颜色错位档, 穿谷深度档) 独立保留 top，防止
  「目标已聚集但中心无法恢复」的状态占满 beam。
- 禁忌/剪枝：禁止立即逆动作、禁止四次同动作循环、不做其它安全剪枝；不禁止暂时拆棱。
- 所有达成路径仍在完整 Cube5 上重放校验（is_edge_paired + centers_are_color_solved
  + 固定面心原位 + 目标槽中的棱色对确实 == target）。早期发现并修复：必须校验目标槽
  中的棱色对等于 target（否则会把别的已配棱误当成功）；基准重放须从打乱后的状态出发。

实测成功基线（n=6~12，beam 2000~3000，per_bucket 80~120）：
- len 1-3：100%
- len 5：约 70-90%（随 beam 调大而提升；beam3000/per120 达 90%）
- len 8-10：需要 beam 3000+ 时耗随深度急剧上升，已超过可接受预算

结论：穿谷分桶 beam 相比 M2 单调 beam 是明确改进（短打乱 100%，len5 可达 90%），
但对 len 8-10 仍受「beam 修剪丢失关键路径」限制，扩大 beam 代价非线性。按 plan §14.1，
下一步正规路线是「中心闭环宏库 + 固定工作槽 + 抽象状态双向(meet-in-the-middle)搜索」，
而不是无止境扩大 beam。

测试：tests/test_edge5_search.py（13 项）覆盖 compact_state（身份/step 与真实一致、
外/宽层 color_off、matched 范围、work_paired、评分排序、分桶、frozen 可哈希）与
single_edge（已配对空链、受控短打乱修复、成功重放校验、未知目标报错、时间上限不抛异常）。
全量 pytest 通过（本轮 443 项）。
