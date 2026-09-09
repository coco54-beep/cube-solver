# 5x5 魔方求解器 —— 开发进展报告

> 分支：`wip/deterministic-freeslice`
> 报告日期：2026-09-08
> 范围：5x5 降阶求解中「中心保持配棱 + 翻转 tredge 修正」的研究与实现进展。

---

## 1. 一句话现状

5x5 降阶求解已构建到 **Gate 5 完整配成一条 tredge + 翻转完成类型分类 + Gate 5b 翻转修正**。
生产求解器 `solver/edge5` 已能稳定配出**部分完整 tredge**（保护式累积 8~10 条），
但**最后 2~4 条（尤其翻转/奇偶）卡住**。为此已转向**独立 reference oracle**
（离线研究工具）生成参考解，再提取可移植宏。当前 oracle 已完成**独立翼配对器**、
**完整 tredge 分类器**，并**实证「中棱锚定配翼不可达」**，正在转入 Gate 5c 切片宏搜索。

---

## 2. 总体架构与目标

### 2.1 流程总览

```
中心归面 (centers)                    ── Gate 前序，已可复现
   ↓
配棱 (edge pairing)                    ── solver/edge5 主线
   ↓
得到 12 条逻辑棱 tredge
   ↓
翻转修正 (Gate 5b: 目标A FLIPPED→VALID)   ── 当前研究重点
   ↓
降阶成 3x3 (build_reduced_facelets + solve_3x3)
```

### 2.2 两条并行路线

| 路线 | 定位 | 状态 |
|------|------|------|
| **生产求解器** `solver/edge5` | Kivy/Android 手机端，要求"快 + 查表 + 有界搜索" | 配到 8~10 条，最后一段未跨越 |
| **Reference oracle** `tools/research/5x5/reference/` | 离线研究工具，允许慢，生成正确轨迹 | 已建分类器 + 翼配对器 + 不可达诊断 |

**生产端原则**：oracle 生成的正确轨迹 → 分析重复局部结构 → 提取确定性宏与选择规则 → 移植回 `solver/edge5` → 手机端只保留 状态分类 / 查表 / 短宏选择 / 有界局部搜索，**不做运行时大搜索 / 公式挖掘**。

---

## 3. 已完成阶段（按提交顺序）

### 3.1 Gate 1 — 合法 free-slice 插翼（提交 `665d218`）

- 确认合法动作集固定为 **36 个 1X/2X** 动作（`3X` 等非物理动作清除出 compact 搜索空间）。
- 单条 `W + outer + W'` 宏（仅 1X/2X）把目标翼聚到目标中棱槽。
- 后置条件：`relation >= 2 ∧ centers_are_color_solved ∧ fixed centers preserved ∧ 真实 Cube5 重放一致`。
- 例：`2F U F' U' 2F'`（rel 聚集、中心归面、固定面心保持）。
- 测试：`tests/test_freeslice_legal_gate.py`（4 组 target/entry）。

### 3.2 Gate 2 — 固定工作布局 + 纯外层定位表（提交 `c96aa9f`）

- `solver/edge5/freeslice_layout.py`：固定工作槽 `UF`、入口槽 `UR`（右翼位），
  离线预计算**纯外层（仅 1X）定位表**。
- `middle_to_work` / `wing_to_entry`：任一位置 → 纯外层序列。
- **关键认知**：中心归面态下只有纯外层 1X 保持 `centers_are_color_solved`；
  所有宽转 2X 破坏中心归面。故定位 setup 纯用 1X，free-slice 用 `2F + outer + 2F'` 关切片恢复中心。
- （Gate 3 实证后更正：自由切片由 `2U` 改为 `2F`，因为 `2U` 无法组装 UF 工作槽。）
- 测试：`tests/test_freeslice_layout_gate.py`（11 项）。

### 3.3 Gate 3 — 确定性原子插翼 + 2F 自由切片 + 朝向推迟（提交 `a9c4df6`）

- `solver/edge5/atomic_insert.py`：`middle_wing_relation_real` / `insert_wing_atomic` /
  `AtomicWingInsertResult`，关系等级 `REL_SCATTERED=0 / REL_SAME_SLOT=1 / REL_COMBO=2 / REL_ORIENTED=3`。
- 组装宏 body 确定为 **`2F U F' U' 2F'`**。
- **朝向一致性推迟**（用户裁定）：rel=2（中棱+单翼）不强制朝向一致，推迟到 rel=3（完整 tredge，
  第二翼到位）再强制。

### 3.4 Gate 4 — 部分组合存储（提交 `7beebde`）

- `solver/edge5/store_partial.py`：`store_partial_combo` / `combo_survives_free_slice` /
  `safe_untouched_slots` / `StorePartialResult`。
- **关键实证**：纯外层单步永远把同槽「中棱+翼」带在一起 → 适合整体搬运部分组合。
  存储目标槽 = `storage_slots − staging_slots` = `{BL,BR,DB,UB}`（开/关 2F 都不触碰）。
- 三件套（用户裁定 store + survival only）：
  1. **store**：整体搬到 safe-untouched 槽；
  2. **survival**：证明该组合在对其它 piece 做一次 free-slice 循环后仍存活；
  3. **recoverable**：`relocate_middle_to_pos` 可把它搬回工作带。
- 明确留给 Gate 5：第二翼插入会拆散部分组合，是「完整配成一条」的核心难题。
- 测试：`tests/test_freeslice_store_partial_gate.py`（30 passed, 1 skipped）。

### 3.5 Gate 5 — 完整配成一条 + 完成类型分类（提交 `3c6e101`、`875370f`）

- `solver/edge5/complete_tredge.py`：`completion_goal_states` / `find_partial_wing_setup` /
  `complete_tredge` / `TredgeCompletionKind` / `CompleteTredgeResult`。
- **scatter 根因修复**：目标槽枚举从 {UF,BL,BR,DB,UB} 5 个展开到**全部 12 逻辑槽 × 24 翼入口**，
  使 `NO_GOAL_COMPLETED` 18 → 0；可评估样本成功率 30 → 40/59。
- **完成类型分类**：`VALID`（三块同槽 + 朝向一致，可注册保护组）/ `FLIPPED`（装配完成但整体翻转，
  位置动作保留、交 Gate 5b）/ `POSITIONAL_ONLY` / `NOT_COMPLETED`。
- **翻转签名统一**（`SINGLE_TREDGE_FLIP`）：14 个翻转 sample 归一化为恰好两个等价模式 `-++` 与 `+--`，
  均表示**中棱朝向与两翼相反** ⇒ 需要一个参数化双棱宏（含旋转共轭）即可修正全部。

### 3.6 Gate 5a — 冻结翻转 fixtures + 公式分类矩阵（提交 `5b115d9`、`b0ac0bc`、`cb53dc8`、`0b5457b`）

- **冻结 6 个翻转 fixtures**：`tests/fixtures/edge5/gate5b/flip_seed{7,19,23,2,4,51}.json`，
  覆盖多个输出槽与两种翻转模式，含完整生成轨迹 + state_fingerprint，重建一致。
- **物理中央切片语义**（`bcc03bb`）：`cube/middle_slice.py` 提供 `apply_inner_slice` /
  `apply_physical_sequence` / `is_fixed_face_center`，修正旧 `3X` 刚性平面旋转会搬走固定面心的
  非物理行为；`3Rw` 物理分解为 `2R + 物理M`，保持 6 个固定面心。
- **公式应用与分类**（`solver/edge5/formula_application.py`）：物理解析 `parse_sourced_sequence` /
  效果分类 `classify_formula` / 变体 `build_variants` / 往返校准。
- **记号规则**（绑定来源 legend）：speedcubedb 下 `r`=宽2 `2R`；K4 scalar 下 `r`=内层单切片
  `2R+R'`；`M/E/S`→内层切片；`3Rw`→`2R+物理M`；`x/y/z` 与 `U2'` 无法物理解析、整体拒绝。
- **分类矩阵结果**（`tools/research/5x5/phase2_formula_matrix.py`，132 行）：
  所有可物理解析的来源 L2E 公式均**未达成 `TARGET_VALID`**，全部为双棱翼交换副作用
  `PROTECTED_BROKEN`(96) / `CENTER_BROKEN`(24) / `NOTATION_UNSUPPORTED`(12)。

### 3.7 Gate 5b — 双棱「目标→缓冲」奇偶转移（`52c292b`）

- `solver/edge5/flip_transfer.py`：`FlipTransferState`（target/buffer 三块 `piece_positions`、
  `target/buffer_orientation`、`protected_signature`、`center_signature`、`centers_solved`）、
  `compute_flip_transfer_state`、`choose_unpaired_buffer_edge`（确定性选未配对且纯外层可达缓冲槽的棱）。
- **双棱转移目标**（用户裁定）：终点 `A：FLIPPED→VALID；B：允许拆散/重排/接收翻转缺陷；
  其它保护组存活；中心归面；可重放一致`；**不要求**缓冲 B 最终配好。

### 3.8 Phase 4 — Reference Oracle：独立 5x5 配棱器（提交 `24e0b18`）

- `tools/research/5x5/reference/pairing5.py`：**完全独立**于 `solver/edge5` 搜索类的配棱器，
  只依赖 `Cube5` + 外层/宽转。
- **原语**：`P = u R U R' F R' F' R u'`（5x5 用宽层 `u`= 2U 直接推广 4x4 的 `u`）。
  在 5x5 上的翼位置换为 **U 带 8-cycle + 一个 2-cycle**（`FR 下翼` ↔ `BR 上翼`），
  保中心归面 + 固定面心，成组搬动翼对不拆散。
- **能力实证**：6 个翻转 fixtures 全部 12/12 翼对配齐，~78–109 步，全程中心归面 + 固定面心。
- 测试：`tests/test_reference_pairing5.py`（8 passed）。
- **结论**：单层外层转无法拆散 5x5 一条逻辑棱的两翼（同层一起动）；真正拆散需宽转/内层。

### 3.9 完整 tredge 分类器（提交 `2826712`）

- `tools/research/5x5/reference/tredge.py`：
  - `middle_edge_key(state, slot)` / `wing_edge_key(state, slot, side)`：无序色对识别身份；
  - `is_complete_tredge` / `count_complete_tredges` / `complete_tredge_slots`；
  - `tredge_oriented`（方向判断，与身份识别分开，不混用 sorted colors）；
  - `face_colors`（由 6 个固定面心得 face→color）。
- **基准数据**：solved = 12/12 complete + 12/12 oriented；**翻转 fixtures = 1~3 complete，0 oriented**
  （正是翻转缺陷的体现）。
- 测试：`tests/test_reference_tredge.py`（14 passed）。

### 3.10 决定性诊断：中棱锚定配翼不可达（提交 `1d023fc`）

- **误确认**：翼对配齐后只有 `1/12` 槽是完整 tredge；纯外层动作 + 配翼原语 P 都「冻结」
  中棱↔翼对归属。
- **决定性证据**：系统枚举所有短 `setup + P + 逆setup` 共轭（`_compress_log` 去重后共 **4338 个**），
  **0 个改变中棱↔翼归属**（`tests/test_reference_tredge.py::test_conjugates_preserve_middle_wing_assignment`）。
- **机理**：一个槽的中棱在贯穿轴坐标 0、两翼在 ±3；纯外层只按面转动，同一槽三块共享两个 ±6
  面坐标 → 要么同时动、要么都不动 ⇒ 槽单元整体搬运。配翼原语 P 同理（实证每个槽中棱+两翼
  同时搬到同一新槽）。
- **结论**：「先配全部翼对再插入中棱」与「以中棱为锚配翼」在当前原语空间内**等价不可达**。
  要改变「中棱↔翼相对归属」，必须引入会暂时打破槽单元的**单内层切片（M/E/S）**，
  它们移动贯穿轴 0 的中棱而不动 ±3 的翼，从而分离中棱与翼对；但切片会扰动中心。
- **文档**：`tools/research/5x5/reference/MIDDLE_ANCHOR_UNREACHABLE.md`。

---

## 4. 当前进行中：Gate 5c（切片宏搜索）

### 4.1 目标

不再找「每步保中心」的公式，而是找：**宏过程中允许中心打乱，但宏结束时中心必须恢复，
并改变中棱↔翼相对归属**。终态条件：

```text
centers_solved(final_state)
fixed_centers_unchanged(final_state)
relative_middle_wing_assignment_changed(initial, final)
protected_tredges_intact(...)
```

### 4.2 搜索顺序（用户指定，渐进）

1. 枚举短 commutator `[A, B] = A B A' B'`；
2. 枚举共轭 commutator `X [A, B] X'`；
3. `A/B` 至少一个是**单内层切片**（`M/E/S`），另一个是外层短序列；
4. 先搜只影响少量棱槽的结果；
5. 再搜能恢复中心且改变相对归属的结果；
6. 最后才扩大深度。

### 4.3 内部表示（用户要求）

统一用**物理层编号**而非易混淆的 `M/E/S` 字符串：

```python
LayerTurn(axis="x", layer=2, turns=1)
LayerTurn(axis="y", layer=2, turns=-1)
```

最后才转换为 `M/E/S`、`2R`、`3Rw` 等显示记号。

### 4.4 当前发现

- **基础 commutator `[slice, outer]` 全部失败**：不满足「保中心 + 改归属」。
  原因：单个切片扰动中心，`A B A' B'` 中 A' 相对 A 已因中间 B 的搬移而无法完全抵消中心扰动，
  留下净中心位移。
- **外层-外层 commutator**（如 `R' F R F'`）虽能保中心 + 保翼对 + 循环 3 个中棱，
  但只**整体搬运槽单元**（中棱 + 两翼一起走），不改变中棱↔翼归属，无法用于锚定。
- **下一步**：按搜索顺序推进到共轭 `X[A,B]X'`；若单内层切片空间确实不可行，
  考虑扩展 A 为**两个正交切片组合**，或扩大 B 长度；再不行则以「基础空间不可行」
  证据固化，进一步扩大搜索深度（用户允许的渐进策略）。

---

## 5. 相关里程碑 / 卡点

| 阶段 | 结果 | 说明 |
|------|------|------|
| Gate 1 合法插翼 | ✅ | 36 个 1X/2X 动作，`2F U F' U' 2F'` 聚合 |
| Gate 2 布局+定位表 | ✅ | 固定槽 + 纯外层 1X 定位表，2F 自由切片 |
| Gate 3 原子插翼 | ✅ | 高度 rel=2，朝向推迟到 rel=3 |
| Gate 4 部分组合存储 | ✅ | store + survival + recoverable |
| Gate 5 完整配成一条 | ✅ | 12 槽 × 24 翼枚举，VALID/FLIPPED 分类 |
| Gate 5a 翻转 fixtures + 公式矩阵 | ✅ | 6 fixtures 冻结；来源 L2E 公式均 UNSAT TARGET_VALID |
| Gate 5b 双棱翻转转移 | ⏳ | 状态模型已建；公式类别不符 → 转 oracle |
| Phase 4 reference oracle | ✅ | 独立翼配对器 + tredge 分类器 + 末段降阶器 `reduce5.py` |
| Gate 5c 切片宏搜索 | ✅ | 拿到纯净中棱 3-cycle（`E R2 E' R2`）+ 奇左翼换位子宏 |
| Gate 5d/5e 末段降阶 | ⚠️→✅ | 6/6 色对 all-complete；`virtual_3x3_legal` 曾为假阳性（第 11 节） |
| 中棱朝向修正（GF(2)） | ✅ | 恒等置换 2-flip 宏词线性消去 `d`，见第 12 节 |
| Plan 12 端到端 | ✅ | `solve5_ref` 中心→配翼→降阶→朝向修正→3×3→回放，20/20 `is_solved` |
| 保护式累积到 12 条 | ❌ | 生产端 8~10 条后卡住，最后 2~4 条（翻转/奇偶）未跨越 |
| Gate 7 最后两棱奇偶 | ⬜ | 真正无缓冲的最后两棱奇偶，留到最后 |

---

## 6. 测试状态

- 全量收集：**749 tests collected**（含新增 reference 相关）。
- reference 定向测试：`tests/test_reference_pairing5.py`（8 passed）+
  `tests/test_reference_tredge.py`（14 passed）+ `tests/test_reference_reduce5.py`
  （9 passed）= **31 passed**。
- 分支：`wip/deterministic-freeslice`；已提交适配：
  `24e0b18`（独立配棱器）、`2826712`（tredge 分类器）、`1d023fc`（不可达诊断）。

---

## 7. 关键结论与下一步

### 已确认的硬结论
1. **单层外层转无法拆散一条逻辑棱的两翼**（同层一起动）；拆散需宽转/内层。
2. **中心归面态下只有纯外层 1X 保持中心归面**；宽转 2X 破坏，靠 `2X+outer+2X'` 关切片恢复。
3. **配翼原语 + 纯外层 setup 共轭全部保持「中棱↔翼」归属**（4338 共轭 0 变化）⇒ 中棱锚定不可达。
4. **公开 5x5 L2E 公式是双棱翼交换**，不能单独把单条装配翻转 tredge 改 VALID。
5. **翻转签名统一为 `-++` / `+--`**（中棱朝向与两翼相反）⇒ 需参数化双棱宏（含旋转共轭）。

### 下一步
1. **Gate 5c**：切片宏搜索（共轭 commutator → 双切片 → 加深），目标终态恢复中心 + 改变归属。
2. 找到切片宏后，验证**单个中棱锚定增长** + protected tredge 机制（1/12 → 2/12）。
3. 在 6 个 fixtures 上达到 **12/12 完整 tredge**。
4. 建立双向翻译（本地 Cube5 状态 ↔ reference facelets；reference moves ↔ 本地物理动作）+ 重放验证。
5. 挖掘「目标 A FLIPPED→VALID 稳定区间」，提取最小化候选公式；无法提取则延迟 Gate 7 联合处理。

---

## 8. Git 纪律

- 只提交 reference pairing / 相关研究工具与测试；**不提交** `renderer/*`、`ui/*` 等无关 UI 改动。
- `tools/research/5x5/reference/pairing5.py` 不导入 `solver/edge5` 的**搜索类**（复用
  `solver.edge5.positions` 纯坐标数据定义可接受）。
- reference oracle 为离线研究工具，不打包进 Kivy/Android 生产求解器。

---

## 9. 本次里程碑：Gate 5c —— 找到「宏结束中心恢复、改变中棱↔翼相对归属」的 3-cycle 宏（宏 A）

> 日期：2026-09-08 分支续。完成了 plan.md 最关键的一步：**拿到纯净中棱 3-cycle 宏**。

### 9.1 决定性突破：纯净中棱 3-cycle 宏

基础交换子 `[slice, outer]` 中找到了**纯净中棱 3-cycle 宏**（plan.md 宏 A 的理想形态）：

```text
E R2 E' R2        （未压缩：E R' R' E' R R）
```

`compute_effect` 实证效果（在复原态）：

```text
M:   (FR BL BR)        中棱三循环
LW:  identity          左右翼完全不动
RW:  identity
centers: identity      中心归面 + 6 固定面心不动
副作用：仅影响 3 个槽
```

因此该宏在**任意状态**下都是「中棱 3-cycle + 翼恒等 + 中心归面」的干净变换，可用作修复
「翼对正确、中棱错配」的纯工具。

### 9.2 宏库（macro_lib.py）

- **24 个基础纯净中棱 3-cycle**：来自 `[slice, outer^2]`，只覆盖三个环内轨道
  （M 环 `{UF,UB,DF,DB}`、E 环 `{FR,FL,BR,BL}`、S 环 `{UR,UL,DR,DL}`），各 8 个。
- **经纯外层共轭扩展覆盖全部 12 槽**：232 种不同中棱 3-cycle；可达无序三槽组合
  **116 / C(12,3)=220（52.7%）**，且**全部双向**、**完全对称**（每槽出现 29 次）。
- `build_reachable_3cycles()` 返回 `{三槽集合 : [(宏串, 中棱循环, 方向)]}`。

### 9.3 宏 B（纯净单侧翼 3-cycle）结构性不存在（实证）

扩展搜索（单层交换子、双层交换子、宽-宽交换子、嵌套、两段组合、超万级候选）**均 0 命中**，
且从全部 18,332 个「中心归面 + 固定面心不动 + 非整体搬槽」候选分类：

```text
617 个能产生某侧翼 3-cycle
  但 0 个「另一侧翼不动」
  且 0 个「中棱 identity」
```

**结构结论**：切片/宽层宏把「中棱 + 一侧翼」当作整列单元一起搬动，另一侧翼独立成环。
所以任何产生翼 3-cycle 的宏必然联动中棱与另一侧翼；无法只孤立一个翼轨道。

### 9.4 配翼 + 末段抽象状态（terminal_state.py）

实现了 plan.md Plan 1 的抽象状态与缺陷签名：

```text
TredgeSlot(middle_id, left_wing_id, right_wing_id, 朝向) 
缺陷: VALID / FLIPPED / MIDDLE_MISMATCH / LEFT|RIGHT_WING_MISMATCH / MULTI_MISMATCH
```

在 6 个 flip fixtures 上 `pairing5.solve_wing_pairs` 配翼后诊断（配翼后中心归面 + 固定面心不动）：

```text
每槽 = 「一对已配好的翼（同一逻辑棱）+ 一个中棱（可能来自别的逻辑棱）」
主要缺陷为 MULTI_MISMATCH / MIDDLE_MISMATCH（翼对与中棱均可能错位）
中棱归属错配 9~12 槽；中棱归属置换奇偶不一（0 或 1）
```

**含义**：
- 纯中棱 3-cycle 宏可解「中棱归属」的偶置换（parity=0）情形。
- parity=1 情形需奇置换宏；且翼对错位需单独处理（纯翼宏不存在，需接受放宽宏副作用 + 后续修复）。

### 9.5 下一步

1. 用纯中棱 3-cycle 宏（宏库）构建**宏级末段求解器**（plan.md Plan 6/7/11 `solve_terminal_state`），
   在真实 fixture 上验证 8~10 条 → 12/12 VALID。
2. 处理 parity=1 与翼对错位：采用**整体搬运宏（R'FRF' 类整条 tredge 3-cycle）** 与纯中棱宏组合，
   或 plan.md 方案四（直接在最后 4 条真实状态上双向搜索）。
3. 覆盖 6 个 fixtures 达到 12/12 VALID + 中心归面 + 虚拟 3×3 合法。

---

## 10. 末段棱降阶「6/6」——⚠️ 已被第 11 节证伪（判据假阳性）

> 日期：2026-09-08 分支续。落地 Plan 5–12 的末段：`tools/research/5x5/reference/reduce5.py`。
>
> **重要**：本节结论建立在 `virtual_3x3_legal` 判据上，第 11 节已证明该判据**假阳性**。
> 保留本节作为历史记录，但**不要**再把它当作降阶成功的依据。

### 10.1 决定性判据（已被证伪）

降阶成功 = **12 条 tredge 全部 complete（归属全对）+ 中心归面 + 固定面心不动 + 虚拟 3×3 合法**；
**不要求**每条 tredge 朝向 VALID（FLIPPED 为偶数时虚拟 3×3 仍可解）。

### 10.2 奇偶：联合不变量 + 配翼阶段可变

- 真正不变量 = `parity(mid) XOR parity(wing)`，在保持翼对配对的生成元集下不变
  （transport 3-cycle、纯中棱 3-cycle、单层外层 4-cycle 均为「同奇偶」或「偶」）。
- XOR=0：A*（293 生成元）直达 all-complete。
- XOR=1：先用**奇左翼换位子宏**破配对，再**重新配翼**（重配翻转 XOR），再走 XOR=0 路径。
- 奇翼宏正确形式：`2R B'L'B 2R' B'LB`（换位子；实测复原态保中心）。
  **教训**：曾误用 `2R B'L'B2R'B'LB`（非换位子），它复原态即打乱中心，靠重配侥幸带回 0；
  已修正并加回归测试。

### 10.3 结果（真实回放断言）

```text
flip_seed19  xor=0 complete=True center_off=0 fixed=True v3=True moves=133
flip_seed2   xor=0 complete=True center_off=0 fixed=True v3=True moves=136
flip_seed51  xor=0 complete=True center_off=0 fixed=True v3=True moves=126
flip_seed23  xor=1 complete=True center_off=0 fixed=True v3=True moves=187
flip_seed4   xor=1 complete=True center_off=0 fixed=True v3=True moves=182
flip_seed7   xor=1 complete=True center_off=0 fixed=True v3=True moves=155
```

### 10.4 下一步（Plan 12）

完整 end-to-end：中心 → 配翼 → 末段降阶 → 虚拟 3×3 → `solve_3x3` 回放，验证整条流水线。

---

## 11. ⚠️ 重大修正：`virtual_3x3_legal` 假阳性；降阶真正判据是 tredge **内部一致**

> 日期：2026-09-08 分支续（Plan 12 end-to-end 排查中发现）。

### 11.1 现象

`solve5_ref.py` 端到端 5 个随机打乱全部 `solved=False`（`moves3=20`，末态 54~56 块错位），
尽管 `reduce5.reduce_edges` 报告 `complete=True / center_off=0 / fixed=True / xor=0`。

### 11.2 根因

- `build_reduced_facelets`（`solver/reduction/reduced_cube5.py:104-123`）对每条 tredge
  **只取第一块（优先中棱）**的贴纸构造虚拟 3×3，**完全忽略两翼朝向**。
- `is_complete_tredge` 只比较**无序色对身份**（`tredge.py:62`），不检查三块在槽两面是否**同色**。
- 实测：`reduce5` 输出常满足 12/12 色对 complete，但中棱与两翼**内部翻转不一致**
  （某 scramble：`complete=12` 而内部一致仅 DB/BL；另一 scramble：`mo!=wo` 4 槽）。
- 于是 `solve_3x3` 求解的是「中棱构成的虚拟 3×3」，回放后中棱归位、但**翼被留下翻转** ⇒ 整体未复原。

### 11.3 朝向可精确追踪（已实证，关键正面结论）

- 定义 `orient_bit[槽]=0` 当该块在槽**主面**（槽名首字母）的颜色 == 其 **home 主面色**。
- 在随机态上实证：每个宏的翻转增量 **只依赖源位置 q**（与 home 无关），
  `new_orient[dest] = orient[q] XOR delta[q]`；扩展状态
  `(mid_home, wing_home, mid_orient, wing_orient)` 的更新规则**逐位精确成立**。
- 因此朝向感知搜索是可行的；每宏仅需 12 位 delta 表。

### 11.4 朝向修复为何困难

- 293 生成元中**无恒等槽置换的宏**（无法「原地翻转中棱」）。
- `reduce5` 输出已 `mid==wing`（色对齐）；仅用 43 个 transport 宏（保 `mid==wing`）
  A* 3M 状态仍**找不到 `mo==wo`**（目标不可达或极深）。
- `P`（`pairing5` 原语）**会移动 4 个 U 中棱**，中心求解也打乱中棱 ⇒
  「按槽内中棱配对」从源头保证一致的路子也被堵。

### 11.5 修正后的真正降阶判据

```text
12 槽：mid/left_wing/right_wing 三块在槽两面上分别同色（内部一致）
     ∧ center_color_off==0 ∧ fixed centers preserved
     ∧ 虚拟 3×3 可解（build_reduced_facelets + solve_3x3）
     ∧ 回放后 is_solved()
```

### 11.6 下一步（待定路线）

1. **中棱保持的配棱原语**：寻找不移动中棱的翼交换触发（从源头让「翼对匹配槽内中棱」），
   是比事后朝向搜索更可能的干净解。
2. 若沿用现有架构：把朝向纳入末段求解，但需解决「无恒等置换翻转宏」与深搜索问题
   （可能需引入真正的 5x5 奇偶算法宏）。
3. 修正 `reduce5`/测试判据，弃用 `virtual_3x3_legal` 单判据。

---

## 12. ✅ 决定性突破：中棱朝向修正（GF(2) 线性消去），端到端 20/20 复原

> 日期：2026-09-08 分支续。解决第 11 节遗留的「中棱相对翼内部翻转」，`solve5_ref`
> 端到端**真正复原**（`is_solved()==True`）。

### 12.1 结构洞察（实证）

对 `build_all_macros()` 的 275 个宏做朝向增量分类（`delta` 只依赖源位置 q，见 11.3）：

```text
transport 宏（mid_map == wing_map）：43 个，全部 md == wd  ⇒ 中棱+翼整体搬运，保持内部一致
中棱-only 宏（wing_map == identity）：232 个
    ├─ 112 个 g == 0（g = md XOR wd）：只搬中棱、不改相对朝向
    └─ 120 个 g != 0，且 popcount(g) == 2：搬中棱的同时翻转恰好 2 个中棱
```

关键推论：**transport 宏保持 `d = mo XOR wo` 不变**（`g==0`，只置换 d），
所以「4 处不一致」不可能靠整体搬运修好（解释了第 11 节 transport-only A* 的失败）。
必须用「中棱恒等置换 + 翻转偶数个中棱」的词。

### 12.2 关键性质：朝向作用是线性仿射

朝向更新是仿射映射 `mo → P·mo XOR c`。对**中棱恒等置换**的词，`P=identity`，
故对任意起始态都有 `mo → mo XOR 掩码`（平移项 c 与起始朝向无关）。
于是「使 `mo == wo`」等价于求掩码子集 XOR = `d`，**纯 GF(2) 线性代数**，
无需大搜索。

### 12.3 实现

- `tools/research/5x5/reference/middle_orient_fix.py`：
  - `build_patterns()`：BFS（深度≤3）枚举「中棱恒等置换 + 朝向非零」的词，
    得到 **60 个不同掩码**，落盘 `.midflip_cache.pkl`（首次约 17s，之后秒载）。
    首个 2-flip 词 = `M U2 M' U2` · `U R2 S R2 S' U'` · `R' F E F2 E' F R`。
  - `solve_mask()`：GF(2) 高斯消元求子集 XOR == `d`。
  - `fix_middle_orientation(cube)`：读出 `d`，返回修正动作（不改色对归属）。
- `solve5_ref.py`：在 `reduce5` 之后、`build_reduced_facelets` 之前插入该修正。

### 12.4 结果（真实回放断言）

```text
端到端 solve5_ref（40 步宽转打乱，5 个随机种子）：
  scramble#0 solved=True total=779 (center=321 edge=181 orient=... 3x3=20)
  scramble#1 solved=True total=814 ...
  scramble#2 solved=True total=650 ...
  scramble#3 solved=True total=673 ...
  scramble#4 solved=True total=743 ...

批量 20 个种子（含 XOR=0/1）：20/20 solved；d_popcount ∈ {2,4,6,8} 均可消去。
回归：tests/test_reference_solve5_ref.py（5 passed）+
      reduce5/pairing5/tredge 既有测试 = 36 passed。
```

### 12.5 真正降阶判据（最终）

```text
12 槽三块内部一致（mid_orient == wing_orient）
  ∧ mid_home == wing_home（色对对齐）
  ∧ center_color_off == 0 ∧ fixed centers preserved
  ∧ 回放后 is_solved()
```

`virtual_3x3_legal` 仅保证中棱子集自洽，**不能**单独作为降阶成功判据（见第 11 节）。

---

## 13. 生产端移植：`solve_5x5` 端到端 12/12 复原

> 日期：2026-09-08。把 reference oracle 管线搬入生产包，`solve_5x5` 从
> 「11-15/12 卡住」变为**真正复原**（`is_solved()==True`）。

### 13.1 移植策略（方案 A：整管线搬迁）

新建 `solver/reduction/ref5/` 生产包，从 `tools/research/5x5/reference/` 移植 8 个核心
模块，去掉硬编码路径与 importlib hack，改为包内相对导入：

```text
solver/reduction/ref5/
  tredge.py            槽/逻辑棱数据工具（无包内依赖）
  macro_effect.py      宏置换效果（apply_macro 支持 M/E/S 切片）
  macro_lib.py         已验证中棱 3-cycle 宏库（REACHABLE）
  terminal_state.py    末段抽象状态
  terminal_solver.py   宏级 A*（275 宏；macro_cache.pkl）
  pairing5.py          配翼（贪心）
  reduce5.py           末段棱降阶（reduce_edges）
  middle_orient_fix.py 中棱朝向 GF(2) 修正（midflip_cache.pkl）
  pipeline.py          reduce_after_centers / solve5_ref 编排
```

- `terminal_solver.py` 的 `_CACHE_FILE` 指向包目录；`macro_cache.pkl` 随包发。
  pickle 内含 `Macro` 类，**类模块路径随包改变**，旧缓存不可复用，已用新包重新生成。
- `midflip_cache.pkl`（60 掩码）随包发；`middle_orient_fix.build_patterns()` 首次
  重建约 17s。
- 未移植 `joint_solver.py`/`parity_solver.py`（不在主管线内；其 `r"D:\coco\cube-solver"`
  硬编码不影响生产路径）。

### 13.2 接入 `solve_5x5`

`stage 2` 由生产 `pair_all_edges`（单调贪心，卡 11-15/12）替换为：

```text
reduce_edges(work)              # 配翼 + 末段宏级 A* → 12/12 complete
fix_middle_orientation(work)    # 消除中棱相对翼内部翻转
build_reduced_facelets + solve_3x3
```

注意：棱降阶/朝向阶段含 `M/E/S` 物理切片 token，必须用 `macro_effect.apply_macro`
回放（`Cube5.apply_moves` 不识别切片）。

### 13.3 结果

```text
solve_5x5，40 步宽转打乱：
  12/12 solved=True（首解 3.91s 含 hkociemba 表加载；其后 0.17–0.34s）
  总步数 650–846（中心 ~311–376 + 棱降阶 117–207 + 朝向 119–273 + 3x3 19–20）

回归：tests/test_solver5_end_to_end.py = 5 passed
      全量 tests = 769 passed, 4 skipped（282s）
```

---

## 14. App 路径修复：facelets 重建的 cube 也能复原（100/100）

> 日期：2026-09-08。用户反馈 App 仍「怎么还不能解」。生产 `solve_5x5` 对
> 直接打乱的 cube 12/12，但 App 走 `cubies_to_facelets → facelets_to_cubies`
> 后 **0/30**，全部「中心还原后校验失败」。

### 14.1 根因一：`facelets_to_cubies` 设 `home == pos`

`cube/conversion.py:facelets_to_cubies` 对每个 cubie 令 `home = pos`。
`solve_centers5` 依赖 `cubie.home`（`build_pos_to_home_permutation` 读
`CENTER_INDEX[cubie.home]`）→ 置换为单位置换，中心求解器认为「已解」直接返回，
但颜色 `center_color_off` 未变。App 仅在 4x4 调用 `_rebuild_center_homes`
（`ui/screens/input_screen.py:593`），5x5 未调用。

**修复**：`solver/solver5.py` 新增 `_center_homes_consistent` / `_rebuild_center_homes`
（按 `(轨道, 颜色)` 分桶赋互异 home），`solve_5x5` 开头检测 home 不可信则重建。

### 14.2 根因二：中心置换奇偶导致 odd-d（5x5 单棱翻假象）

重建中心 home 后仍有 ~50% 报「中棱朝向修正失败: no GF(2) solution for
orientation mask」。实测：

```text
直接打乱（真 home）        ：odd-d = 0/120
facelets 重建（规范 home）：odd-d ≈ 50%（14/30、20/30、13/30、16/30）
```

`fix_middle_orientation` 的 GF(2) 基由「中棱恒等置换 + 翻转偶数中棱」宏构成，
只能消去偶数权重掩码。odd-d 并非真实物理态（直接打乱从不出现），而是中心
home 赋值奇偶错误所致：**交换任意两个同色同轨道中心的 home**，odd-d 立即变偶
（实测 2 例、全部 66 种交换均成立）。

**修复**：`solve_5x5` 首解失败时交换两个同色中心 home 再解一次
（`_swap_two_center_homes` + `_solve_once(force_center=True)`）。
`SolveResult.success == work.is_solved()`，故重试不会引入假成功。

同时修 `solve_5x5_facelets` 既存 bug：`facelets_to_cubies(facelets)` 缺 `n` 参数。

### 14.3 结果

```text
App 路径（cubies→facelets→facelets_to_cubies(home==pos)→solve_5x5）：
  5 seeds × 20 = 100/100 success
  solve_5x5_facelets(facelets) 同样全部成功
直接打乱路径无回归（真 home，不触发重试）

回归：tests/test_solver5_end_to_end.py = 10 passed（新增 5 条 App 路径用例）
      全量 tests = 774 passed, 4 skipped（288s）
```

## 15. App 回放 M/E/S：`solve_5x5` 的动作现可由 App 动画回放（20/20）

> 日期：2026-09-08。§14 修好求解后，App 仍会在**播放**阶段崩溃：
> `solve_5x5` 返回的 moves 含 M/E/S 物理切片，而 App 的解析/渲染链完全不认。

### 15.1 阻塞点（实证）

```text
Cube5.apply_move("M")        -> ValueError: 非法公式起始字符: 'M'
decompose_move("M", 5)       -> 同上（内部用 parse_move_str）
solve_5x5 一例 token 分布     -> {2:269, F:91, R:84, U:61, L:31, M:30,
                                  B:25, u:22, D:19, E:16, S:12}
```

其中 `2` 前缀（`2U`/`2R`…，宽 2 层）在逻辑层 `parse_move_full` 已支持，
但 `decompose_move`（旧用 `parse_move_str`）不支持前导数字。

### 15.2 修复（原生支持，不改成 3 层组合）

1. `cube/cubie_model.py:apply_move`：首字符 M/E/S → `middle_slice.slice_turns`
   → `apply_inner_slice(axis, turns)`（只转中层可动块，固定面心不动）。
2. `renderer/turn.py:decompose_move`：
   - 切片分支：`slice_turns` → 同向面 base（x→R, y→U, z→F）、`layers=(0,)`、
     `_quarter_angle(base, ccw)` 定角。
   - 面转动改用 `parse_move_full` + `coordinates.layer_values` 计算层坐标，
     与 `apply_move` 完全一致，从而支持 `2U` 等前导数字宽层。
3. `ui/screens/playback_screen.py:_single_turn_string`：切片返回单字符 token；
   层数 >2 返回 `f"{n}{base}"`，==2 返回小写，==1 返回大写。
4. `renderer/cube_view.py:start_turn`：旋转集合排除固定面心
   （`is_fixed_face_center`），避免中层动画视觉上拖动面心（最终 `set_cube` 本会纠正）。

### 15.3 结果

```text
App 动画回放路径（decompose_move + _single_turn_string + apply_move）：
  5 seeds × 20 = 20/20 复原（含 M/E/S 与 2U 宽层）
回归：tests/test_solver5_end_to_end.py = 14 passed
      新增 test_slice_tokens_match_inner_slice（M/E/S 与 apply_inner_slice 等价）
      新增 test_solve_5x5_app_playback（3 seeds，App 回放复原）
      全量 tests = 779 passed, 4 skipped（215s）
```

## 16. 中棱朝向修正：GF(2) 解改为最少步数（朝向 ~147 → ~52 步）

> 日期：2026-09-08。用户反馈「步骤有点多」。实测 5 seeds 平均 **711 步**
> （中心 346 + 棱降阶 199 + 朝向 147 + 3x3 20），约为人类解法的 3-4 倍。

### 16.1 根因：`solve_mask` 只求有解、不求最短

`middle_orient_fix.solve_mask` 原用高斯消去拼接基向量，宏词条数不受控：
seed 3 用 **14 条宏** 去翻转 **6 个中棱**（`d_popcount=6`），共 239 步。

### 16.2 修复：12 位掩码空间上的 Dijkstra

掩码空间仅 4096 个状态，对 `patterns`（每条掩码 → 展平动作）做 Dijkstra，
主代价 = 总动作数，次代价 = 宏词条数。仅改 `solve_mask`，接口不变。

### 16.3 结果（5 seeds）

```text
朝向修正：136/51/239/188/121 -> 68/35/51/51/54（平均 147 -> 52，-95 步）
总步数  ：711 -> 616（-13%）；最坏 812 -> 624
正确性  ：19 passed（end-to-end + reference）；全量 779 passed, 4 skipped
```

中心（346，精确置换 3-cycle 法，已近该方法下界）与棱降阶（199）为下一步。

## 17. 第一轮低风险优化：整段化简 + 候选联合评分 + 配翼变体 → 平均 616 降到 555

> 日期：2026-09-08。在 §16 基础上做不改变算法的低风险优化，5 seeds 平均
> **616 → 554.6**（-61，-10%）；最坏 624 → 584。

### 17.1 整段物理层化简（`solver/reduction/ref5/simplify_moves.py`，新增）

把整段动作映射为「绕某轴、对某些层坐标的带符号 90° 计数」，折叠**连续同轴**动作后
按 `outer/wide2/slice` 分解重建（同轴动作恒可交换，不同轴不可跨轴折叠）。
单趟折叠会漏掉「中间同轴段抵消后两侧同轴段合并」的级联情形（`R U U' R'`），
故迭代到不动点。随机 80 步串约降 13%。`simplify_verified` 在复原态重放比对块状态。

`solver5._solve_once` 末尾对全序列化简并回放校验，消息追加「化简前 %d」。

### 17.2 末段候选联合评分（`reduce5.solve_all_complete_candidates`）

A* 不再只取首个目标，而是收集至多 `max_candidates=6` 个 all-complete 宏序列；
对每个候选施加中棱朝向修正（Dijkstra 距离，`middle_orient_fix.orient_cost/orient_mask`）
并校验虚拟 3x3 合法，按 **棱展开成本 + 朝向修正成本** 取最优。

> 偏差记录：任务原设想把 A* 边成本直接改成真实展开步数，但 293 个宏、
> 弱启发式下按成本排序会指数级膨胀（深度版 11 次弹出即命中目标，成本版
> 数万次仍无解）。故搜索仍按「深度 + 错配」排序，真实成本只用于候选间评分。

### 17.3 配翼变体 + 优先 XOR=0（Task 6）

`reduce_edges` 生成 6 个配翼变体（首个确定性贪心，其余随机贪心），
每个变体消除 XOR 后求最优末段计划，按「配翼 + parity + 棱 + 朝向」总成本选最优。
实测不同配翼可改变 XOR 奇偶：seed 1-5 均找到 XOR=0 变体，省下原先约 38 步的
「奇翼宏 + 重配」parity 修正；个别变体以略长配翼换取显著更短的朝向修正。

### 17.4 结果（5 seeds）

```text
总步数  ：616 -> 554.6（531/572/518/584/568）
分阶段  ：中心 346（不变）、棱降阶 199 -> 178、朝向 52 -> 28、3x3 20
正确性  ：新增 tests/test_simplify_moves.py 6 passed
          定向 36 passed；全量 785 passed, 4 skipped（268s）
```

中心阶段仍占 ~62%，为第二轮主攻方向。

## 18. 第二轮：中心同色等价求解（宏数 21.6 -> 15.4），端到端 554.6 -> 481

> 日期：2026-09-08。第二轮首项：中心只要求「按颜色归面」，同色中心块可互换，
> 从而把长置换拆成更短循环。新建 `solver/center5/color_solver.py`。

### 18.1 原理与算法

- 精确求解要求每块回唯一 home，会在面内同色置换上浪费动作。
- 颜色多重图：每个错色位置记 `(demand=所在面颜色, supply=块颜色)`。
- 分解为闭合 trail（优先 3-cycle、再 2-cycle、剩余闭合）；沿 trail 分配具体位置，
  令块 `p_i -> p_{i+1}`，由 `supply(p_i)==demand(p_{i+1})` 保证落位即归色。
- 置换奇偶只取决于循环个数 T：`parity=(W-T) mod 2`（W=错色位置数）。重启中优先筛
  偶置换分解；必要时在共享颜色顶点拼接两条 trail 翻转奇偶（普通拼接会破坏同色有效性）。
- `decompose_even_pos_to_home` 把偶置换分解为正向 3-cycle，逐个实例化为宏并施加。

### 18.2 结果：中心宏数

```text
seeds 1-5 宏数（corner+edge）：13/14/14/19/17，平均 15.4
精确求解宏数：21.6，中心步数 346 -> 247.6（-98，约 -28%）
```

### 18.3 下游耦合与回退

中心 3-cycle 基元同时会扰动棱（`validate_center_primitive` 只保证中心轨道/固定面心，
不保证棱不动），故同色中心解与精确中心解产生**不同的棱状态**。末段棱降阶 oracle
（`ref5.reduce_edges`）只在其验证过的棱状态上完备：实测精确中心 12/12 可降阶，
同色中心仅 7/12；失败均为 `middle_orient_fix.solve_mask` 无解（朝向掩码不可达），
加大搜索预算/配翼变体数均无效。

处理：`solve_5x5` 先试同色中心；整条流水线失败时用精确 home 中心重解（精确棱状态
始终可降阶），保证正确性。5 seeds 端到端：

```text
总步数  ：554.6 -> 481.0（441/468/518/517/461）
分阶段  ：中心 210/226/354/306/268（seed 3 回退精确 = 354）
正确性  ：tests/test_center_color_solver_5x5.py 24 passed
          定向 39 + end-to-end 14 passed；全量 809 passed, 4 skipped（259s）
```

### 18.4 待办

- 同色中心使棱降阶 oracle 不完备（~40% 回退），是当前主要收益损失。需让末段降阶对
  任意中心置换鲁棒（配翼 beam / 朝向掩码完备化 / parity 联合）。
- 中心 3-cycle 执行顺序优化（当前按 decompose 顺序，未按 setup 长度联合排序）。

## 19. 第三轮：棱降阶完备化 + 配翼 beam + 双基元 setup → 端到端 481 降到 450

> 日期：2026-09-09。针对 §18.4 三项待办逐条处理，另验第 4 项（朝向/parity 联合）。

### 19.1 棱降阶完备化（OLL parity，消除 ~40% 回退）

- 根因：同色中心解产生的棱态配对后 `mid/wing` 置换奇偶 XOR=1，且朝向掩码 d 为奇；
  `_best_edge_plan` 返回 None（偶翻掩码库只张成偶子空间）。精确中心始终为偶。
- 新增 `_OLL_PARITY`（15 步）：`r2 B2 U2 l U2 r' U2 r U2 F2 r F2 l' B2 r2`。
  在复原态重放后 all-complete、`center_color_off=0`、fixed、`d=1`（单条 dedge 内翻）。
- `reduce_edges`：`_best_edge_plan` 返回 None 时，克隆、施加 `_OLL_PARITY`、重试；
  成功则并入前缀并记 `info["oll_parity"]`。
- 结果：5 个原失败 seed 全部可降阶；seed 3 端到端 518→443（不再回退精确中心）。

### 19.2 配翼束搜索（`pairing5.pair_edges_beam`）

- 新增 `pair_edges_beam(cube, beam_width=6, per_state=6)`：贪心展开做束搜索，
  按（已配对槽数，-已用步数）排序，不修改输入。
- 新增 `_SETUP_CACHE`：memoize `_find_best_setup(a,b)`（24×24 有序对）。
- `reduce_edges` 在既有 `pair_variants` 个贪心变体之外追加一个 beam 变体。
- 实测配翼：贪心 ~121.4 → beam(w6) ~116.8 → beam(w16) ~115 步；端到端 466 → 453。

### 19.3 双基元最短 setup

- 每轨道有主/备用两个 3-cycle 基元（`CORNER_MAIN/BACKUP`、`EDGE_MAIN/BACKUP`），
  对同一有序三重产生**同向** 3-cycle，但 setup 长度不同。
- `color_solver` 改用 `_primitives_for(orbit)` 同时建两张表，逐三重取较短宏。
- setup 平均：corner 3.93 → min 3.72、edge 4.69 → min 4.33（每宏省 ~0.2/0.36 步）。
- 端到端 453 → 450.2。

### 19.4 第 4 项（朝向/parity 联合）：无收益，已回退

- `_best_edge_plan` 已联合评分「棱展开 + 朝向修正」；`fix_middle_orientation` 已是最优
  Dijkstra（§16）。
- 试验：XOR=1 时遍历全部 3 条 `_LW_ODD_MACROS` 取总成本最优 → 5 seeds 净变化 0，
  且多出 2 次昂贵末段搜索，已回退。

### 19.5 结果（5 seeds）

```text
总步数  ：481 -> 450.2（421/424/445/483/478；最坏 483）
分阶段  ：棱降阶 178 -> ~150（beam 配翼）、中心 247.6 -> ~245（双基元）
正确性  ：tests/test_center_color_solver_5x5.py 24 passed
          reference 22 passed；end-to-end 14 passed；全量 809 passed, 4 skipped（271s）
```

### 19.6 后续（需换算法，非低风险项）

- 配翼已近 floor（P 基元 9 步 × ~10 对）；大降需 freeslice 重写（破坏中心同色，风险高）。
- 中心宏数 15.4 已近 `decompose_even_pos_to_home` 下界；缩短需更短基元
  （已搜 4 步换位子，无合法者）或跨轨道联合（setup 不共享，无收益）。

## 20. 第三轮续：跨轨道联合基元接入（中心 239→201）+ 联合规划器探索（未果）

> 日期：2026-09-09。人类式观察：`[2B,D2]` 4 步换位子同时做 2 个 corner 3-cycle
> + 1 个 edge 3-cycle，却不动固定面心。据此接入 edge 轨道，并尝试让「一次宏作用
> 的 corner/edge 循环都被规划」的联合规划器。

### 20.1 EDGE_COMM4 接入（-38 步）

- 新增基元 `EDGE_COMM4`（`primitives.py`）：`2B D2 2B' D2`，4 步，
  edge 轨道单 3-cycle `(3,21,23)`，corner 轨道留 2 个 3-cycle（不通过
  `validate_center_primitive`，故不用于 corner 轨道）。
- `color_solver`：`_ACTIVE_ORBITS` 改为 `(EDGE, CORNER)`——先用 `EDGE_COMM4`
  解 edge（4 步基元 + setup，更快），再用 edge-pure 基元解 corner（不破坏已解 edge）。
  `_solve_orbit_color` 增加 `primitives` 参数。
- 结果（5 seeds）：中心 **239.2 → 201.2**（178/188/182/236/222，-38）；
  端到端 **450.2 → 414.8**（364/416/421/443/430，-35.4）。
- 正确性：`test_center_color_solver_5x5` + `test_center_solver_5x5` 50 passed；
  全量 809 passed, 4 skipped（272s）。

### 20.2 当前阶段拆分（5 seeds 均值）

```text
中心 206：edge 90.4 步 / 7.2 宏（12.6 步/宏，EDGE_COMM4）
          corner 115.6 步 / 7.6 宏（15.2 步/宏，8 步 edge-pure 基元 + setup 3.6×2）
```

corner 已成为新瓶颈。

### 20.3 联合规划器探索（全部未果）

目标：让一个 4 步宏的 corner 2 个 3-cycle + edge 1 个 3-cycle 都对准待解循环，
从而「一次宏消 9 块」、把 corner 阶段从 15.2 步/循环降到 ~7-10。

| 尝试 | 结果 |
|---|---|
| 4 步换位子分布 | corner `(5,)`+edge `(3,)` 或 corner `(3,3)`+edge `(3,)`；**无 corner `(3,)`** |
| 朴素贪心（错色数最少） | 震荡退化，648-862 步，失败 |
| beam 搜索（错色数，w8,d14） | seed 1 卡在 wrong=18，不收敛 |
| 任意 2 个 corner 3-cycle 的 setup | 7-10 步（部分深度 10 内无解），宏成本反超 |
| 6 步联合基元 `(3,)+(3,)` | 12/24 步集均无 |
| 8 步联合基元 `(3,)+(3,)` | 12/24 步集均无（edge 3-cycle 枚举 + 边逆配对） |
| 6 步 corner-only 3-cycle | 12/24 步集均无 → **8 步为下界** |

结构性结论：**不存在 ≤8 步、同时只做 1 个 corner + 1 个 edge 3-cycle 的联合基元**；
corner-only 3-cycle 最短 8 步。故多循环宏的 setup（6 约束 7-10 步）抵消了循环数减半的收益。

### 20.4 建议

- 中心在当前框架下已近算法 floor（~200）：短基元已穷尽、颜色分解已多重重启最优、
  corner setup 已 BFS 最优。继续大降需换根本算法（人类式 commutator 直觉搜索 /
  通用 setup 求解器），投入产出比低。
- 若坚持联合规划器，唯一可行路径：预计算「短 setup（≤4 步）→ 可达 corner 循环对」
  查找表（~数十万条），把 3-cycle 分解问题变成「配对匹配可达对」；预计最多再省
  20-40 步，工程量大、可靠性待验证。

### 20.5 转向其他阶段：配翼变体预算 6→10（端到端 414.8 → 404.4）

联合规划器证伪后转攻非中心阶段。分阶段均值（化简前）：

```text
中心 201.2 + 配翼 128.6 + 末段棱宏 39.4 + oll 3.0 + 朝向 34.2 + 3x3 19.8
```

- 逐参数扫描 `reduce_edges`：`pair_variants` 是唯一有效旋钮。
  `6→10` 使「配翼+末段+朝向」总步数 209.7 → 195.3（seeds 1-3 均值）；
  `iters`（60000 vs 150000）与 `max_candidates`（20 vs 30）几乎无差异。
- 改动：`reduce_edges` 默认 `max_candidates 6→20`、`pair_variants 6→10`。
- 端到端 **414.8 → 404.4**（seeds 1-5：364/404/393/443/418；最坏 443）。
- 代价：reduce 阶段 ~1-2s → ~4s/seed（每 seed 多跑 ~4 个配翼变体的 A*）。
- 正确性：全量 809 passed, 4 skipped（360s）。
- 稳健性（seeds 100-119，非调参样本）：20/20 成功；mean 414.9 / median 416 /
  p95 438 / max 453 / min 380（~5.5s/seed）。
- 结论：本框架各阶段已近上限（见 20.3/20.4），后续降步数需换根本算法。

### 21. 手机求解体验优化：热路径 + 进度回调（预算最终保持 10/20）

起因：手机端反馈五阶「点开始后等很久才出解」。profile 显示慢在纯 Python 搜索热路径，
以及 20.5 的预算调大（`pair_variants 6→10`、`max_candidates 6→20`）——该调参只用了
seeds 1-3，存在过拟合。

#### 21.1 热路径优化（步数完全不变）

- `middle_orient_fix.solve_mask`：原实现对每个候选重跑一次 12-bit 掩码空间 Dijkstra
  （实测 ~1000 次 / 5 seeds）。改为对固定 `patterns` 全空间 Dijkstra **只算一次**，
  任意 target 直接回溯；并把 `_load_patterns` 加模块级缓存（原来每次调用都反序列化，
  导致全表 Dijkstra 被重建 23 次）。→ 5 seeds 26.97s → 15.16s（1.78x）。
- `terminal_solver.Macro`：预计算 `operator.itemgetter` 组合 24 项索引（mid 0..11 +
  12+wing 0..11），A* 展开用 `m.apply(state)` 取代两次 genexpr + tuple 拼接。
  原 `apply_macro_to_state` 约 100 万次调用从热点消失。缓存键 `mid_trans_v2→v3`
  （pickle 新增 `apply` 槽，需重建 `macro_cache.pkl`）。
- `reduce5._mismatch` / `_all_complete`：改用 `map(ne/eq, state[:N], state[N:])`，
  避免逐项生成器。
- 综合：seeds 1-5 端到端 5.47s → 稳态 ~2.2s；seed3 cProfile 9.5s → 4.2s。

#### 21.2 预算回退 10/20 → 6/6（留出集证明 20.5 过拟合）

同种子端到端对比（seeds 100-119）：

```text
(6,6)    mean 421.9 步  median 428  max 482   reduce 阶段 ~2x 更快
(10,20)  mean 415.0 步  median 420  max 453
```

- 真实代价 **+6.9 步（+1.7%）换 reduce ~2x 提速**。
- seeds 100-129 的 `reduce_edges` 单测：(10,20) 171.2 / (6,6) 172.0（仅 +0.8）；
  但差异**非单调**：部分种子 (6,6) 反而更短（seed113 137 vs 166、seed105 175 vs 190），
  部分更长（seed119 176 vs 162、seed100 194 vs 187）。更多变体不等于更优。
- 结论：20.5 的「6→10」主要过拟合 seeds 1-3；留出集上并无对应收益。
- **最终决定（用户反馈）**：`(6,6)` 虽 reduce 阶段 ~2x 提速，但端到端总耗时占比不大
  （中心阶段才是主耗时），而步数确实变多。故 **恢复默认 `(10,20)`**，热路径优化保留。

#### 21.3 验证

- seeds 1-10：10/10，mean 411.9 步（(10,20) 配置）。
- 留出 seeds 100-119：20/20，mean 422.0 步，~1.15s/seed（median）。
- 全量回归：809 passed, 4 skipped（238s）。

#### 21.4 求解进度显示（5x5）

- `solve_5x5` 早已接收 `progress_callback` 但从未调用；本次在 `solver5._solve_once`
  各阶段边界上报 `{"stage","progress","label"}`：
  - 中心：0.05 → 0.45（`solve_centers5_color` 新增 `progress_callback`，按轨道
    edge/corner 上报 `{done,total}` 映射到 0.05..0.45）。
  - 棱降阶：0.45 → 0.90（`reduce_edges` 新增 `progress_callback`，每个配翼变体
    `{variant,variants}` 映射）。
  - 朝向修正 0.92、降阶 3x3 0.95、完成 1.00。
- `services/solve_service.py`：5x5 分支补传 `progress_callback=cb`（此前只 4x4 传）。
- `ui/screens/solving_screen.py`：`_apply_progress` 支持浮点 `progress` 直接驱动进度条
  与 `label` 文案；`app/constants.py` 的 `STAGE_LABEL` 增加 `orient`。
- 实测 seeds 1-3 各 19 个进度事件，进度条平滑推进。

### 22. 首解卡顿消除：应用启动后台预热

起因：手机端「第一遍解特别慢，之后很快」——典型的惰性加载。桌面端实测各资源
首次构建耗时：

```text
import solver3（kociemba 两阶段表）  6.885s   ← 主因
setup_table EDGE_COMM4               1.762s
setup_table CORNER_MAIN              1.785s
setup_table CORNER_BACKUP            1.786s
setup_table EDGE_MAIN                1.746s   ← 仅精确回退用
build_all_macros / _load_patterns /
_build_solve_prev / generators / orient_distance_map   均 < 0.02s
```

- 常用主路径需要 EDGE_COMM4 + CORNER_MAIN + CORNER_BACKUP（≈5.3s），精确回退
  额外需要 EDGE_MAIN；`EDGE_BACKUP` 实际未被使用，故不预热。
- 新增 `app/warmup.py`：`warmup_solvers()` 起守护线程，按
  `solver3 → ref5(宏表/掩码/Dijkstra/生成元) → center setup 表` 顺序预热，
  异常全部吞掉；`app/application.py` 的 `on_start` 里触发。
- 实测：预热线程 14.0s 完成（后台），**预热后首次求解 2.11s**（稳态 2.32s），
  首解额外开销基本归零。
- 注意：预热与用户立即求解并发时会争 GIL（重复建表但不会损坏）；预热本身
  不阻塞 UI 线程。

#### 22.1 中心 setup 表版本化磁盘缓存

- 内存缓存不跨进程存活，故每次启动都要重跑 BFS。给 `setup_cache.get_setup_table`
  加**版本化磁盘缓存**：内存 → 磁盘 → BFS（构建后落盘）。
- 缓存键沿用 `cache_key_of`（含 `CACHE_VERSION` + 基元 cycle + 合法动作集 +
  置换约定），任一变化自动失效；文件 `<writable>/.cubesolver_cache/center5_setup/<key>.pkl`。
- 可写目录：Android 优先 `ANDROID_PRIVATE`/`ANDROID_APP_PATH`，桌面回退 `~`；
  无可用目录时静默退化为纯内存缓存。
- 占用与收益（实测）：4 张表共 **1.7MB**（每张 0.4MB）；冷建 7.14s →
  磁盘热载 **0.015s**。整个预热 14.0s → **7.08s**（余下为 kociemba 表加载）。
- `clear_setup_cache()` 现在一并清空磁盘缓存（测试隔离）。
- 未做：把预建表随 APK 发布（可让首启也免 BFS，但省的是后台时间，收益有限）。




