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
| Phase 4 reference oracle | ⏳ | 独立翼配对器 + tredge 分类器已完成；中棱锚定不可达诊断 |
| Gate 5c 切片宏搜索 | 🔄 **进行中** | 基础 commutator 失败，待共轭 / 双切片扩展 |
| 保护式累积到 12 条 | ❌ | 生产端 8~10 条后卡住，最后 2~4 条（翻转/奇偶）未跨越 |
| Gate 7 最后两棱奇偶 | ⬜ | 真正无缓冲的最后两棱奇偶，留到最后 |

---

## 6. 测试状态

- 全量收集：**749 tests collected**（含新增 reference 相关）。
- reference 定向测试：`tests/test_reference_pairing5.py`（8 passed）+
  `tests/test_reference_tredge.py`（14 passed）= **22 passed**。
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
