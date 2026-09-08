# 末段宏级求解器 — 当前进展与诚实结论

生成时间：2026-09-08（迭代记录）

## 目标
在「中心归面 + 固定面心不动 + 翼对已配(pairing5)」基础上，把每个棱槽抽象为
`(mid_home, wing_home)`，用已验证宏把末段解到 12/12 VALID（完整、归位、朝向正确）。

## 已达成的能力（已用真实 Cube5 回放验证）

### 1. 置换（归属）求解器 —— seed19 已实证解到全 identity
`terminal_solver.py::solve_two_phase` 两段式构造：
- 阶段 A：用「整体搬运宏」（外层共轭 commutator 得到的 whole-slot 3-cycle）解翼对归属；
- 阶段 B：用「中棱纯净 3-cycle」补余下中棱。

对 `flip_seed19`，回放后 `abstract_state` 从
`(6,8,1,11,9,5,4,3,10,7,0,2, 1,6,4,2,8,3,9,10,11,7,0,5)`
变为 **全 identity** `(0,1,…,11, 0,1,…,11)`，且逐槽检查：
`UF..BL` 全部 `complete&home=True`（12 槽全部完整且归位）。

### 2. 宏效果（compute_effect）验证
- 中棱宏 `['M','U2',"M'",'U2']` → 中棱循环 (UF UB DF)，翼 identity，且翻转所循环的中棱。
- 整体搬运宏 `["R'","F","R","F'"]` → 整体循环 (UF FR UR)，且翻转所搬运槽内容物。

### 3. 宏库
- `build_all_macros()` 构建 中棱 3-cycle（232 个）+ 整体搬运（43 个，覆盖 37 个不同 3 槽组）。
- pickle 缓存到 `.macro_cache.pkl`，避免每次 ~27s 重建 REACHABLE。

## 关键发现

### 1. 置换层可解，但会带入大量翻转
seed19 回放后：12 槽全部 `complete&home=True`，但 **10 槽 `oriented=False`（FLIPPED）**，
仅 `UB`、`FL` 两槽 `VALID`。即：抽象置换已达 identity，真实魔方上大多数 tredge 处于 180° 翻转态。

### 2. 中棱翻转不是干净的 Z₂ XOR 不变量（核心卡点）
实测 `new_flip[dst] = old_flip[src] XOR toggle[dst]` 模型：
- **翼对**：对中棱宏、整体搬运宏均**精确成立**（两次测试 match=True）。
- **中棱**：在若干位置不成立（`F2MF2M'` 在 UF 处、`MU2M'U2` 在 UF/UB/DF/DR/DB 处偏 1）。

根因：`compute_effect` 的 `middle_flip`（“相对 home 翻转”）在宏对**不同 home 的块**搬运时，
翻转 toggle 依 home 而变，并非与 home 无关的群同态。因此无法用单一 `XOR toggle` 在抽象层
精确建模中棱朝向；需改用标准 cubie-orientation 约定（以 U/D 为朝向基准）方可成同态。

### 3. 奇偶障碍 —— 6 个 fixture 中 5 个不可达
配对后逐 fixture 的中棱/翼对置换奇偶（0=偶，1=奇）：

| fixture | mid parity | wing parity | 双偶可解? |
|---------|-----------|-------------|-----------|
| seed19  | 0         | 0           | ✅ 唯一 |
| seed2   | 1         | 1           | ❌ |
| seed4   | 0         | 1           | ❌ |
| seed7   | 1         | 0           | ❌ |
| seed23  | 0         | 1           | ❌ |
| seed51  | 1         | 1           | ❌ |

当前宏库全部是 **偶置换**（3-cycle），故中棱奇偶、翼对奇偶各自为不变量。
仅 seed19 双偶，其余 5 个 fixture 无法仅靠现有偶宏达到 identity——需要新增一个
改变中棱或翼对奇偶的生成元（如 2-cycle / 4-cycle / 恢复中心且可控的 parity 宏）。

## 结论（诚实）
- ✅ **置换层求解器可靠**：能在 seed19 上把（中棱归属, 翼对归属）解到全 identity，
  所有槽完整且归位（真实回放验证）。
- ⚠️ **未达成 12/12 VALID**：即使置换全对，剩余 10 槽翻转为 FLIPPED；中棱朝向
  无法用现有 XOR 抽象精确建模。
- ❌ **奇偶受阻**：除 seed19 外，5 个 fixture 的奇偶持平，当前偶宏集不可达，需额外 parity 宏。

## 后续可选路线
1. 标准 cubie-orientation 建模：以 U/D 面为朝向基准，把朝向作为 Z₂ 同态纳入抽象状态，
   使 `new_flip = old_flip XOR delta` 对中棱、翼对都精确成立，据此做含朝向的搜索。
2. 搜索一个改变中棱或翼对奇偶的宏（保持中心归面 + 固定面心不动），作为额外生成元，
   使 5 个奇偶 fixture 可达。
3. 对每个 fixture 做真实回放断言（count_valid==12 + center_color_off==0 +
   _fixed_centers_preserved==True）才算达成，并在报表中诚实标注达成情况。

---

## 追加迭代：两个关键**负面**结论（2026-09-08 后续）

### 1. 绝对朝向同态**不可能**（已实证证明）

`solver/edge5/orientation.py:1-13` 明确记录 `edge_cubie_flip`（绝对、home 轴相对翻转）
**不是**合法动作群的奇偶不变量，也**不是**槽相对翻转。实测证实：

- 连单层 `R/U/F/L/D/B` 都出现 9~12/36 个源的朝向 delta 不一致（`after_ori = NOT(before)`，
  非同态）。
- `solver/edge5/orientation.py` 宣称的 `middle_flip_parity` / `wing_flip_parity` /
  `total_flip_parity` 不变量，在随机 `M/E/S` 打乱下全部失效。

**结论**：不存在干净的「绝对朝向 Z₂ 同态」，故不能用 `XOR toggle` 精确建模中棱朝向。
**正确目标是「槽相对朝向」**：槽内中棱+两翼在槽的两面上显示相同颜色
（`_orientation_consistent` / `tredge_oriented` 判据），这才是 VALID 的精确定义。

### 2. 奇偶宏**无短解**

对 `[A,B]`、`A B A B'`、以及 33 个动作的全部 2/3 长度组合（35937 序列）搜索
「奇置换 + 保持 centers_ok + fixed_centers_ok + 非整体搬槽」：**0 命中**。

单次宽转/外转虽是奇置换，但会打乱固定面心，且 ≤2 步内无法既修好面心又不撤销奇偶。

### 3. 由此调整方向

- **放弃**「绝对朝向同态」建模（不可能）。
- 朝向目标改用**槽相对**（`is_complete_tredge ∧ tredge_oriented`）驱动求解，
  可复用 `flip_transfer.py` 的 buffer/parity 转移模型。
- 奇偶：要么接受「必须先用更长的结构化奇置换宏」，要么把奇偶放到**虚拟 3×3** 层面的
  降阶奇偶宏处理（plan.md Plan 10：归属全对后检查虚拟 3×3 合法性，再执行 5×5 降阶 parity 宏）。

---

## 追加迭代：Plan 10 关键**正向**实证（2026-09-08）

### 目标判据修正（重大）：真正的降阶成功判据 = 「归属全对 + 虚拟 3×3 合法」，
**不是**「12/12 每条 tredge VALID」。

- 复用 `solver/reduction/reduced_cube5.py::build_reduced_facelets`（已把中心归面+12条逻辑棱
  配对的 Cube5 映射为 3×3 facelets，对棱「任取3块之一、读朝该面颜色」）。
- 复用 `solver/reduction/parity.py::detect_parity`（以 hkociemba `solve_3x3` 为**权威判据**）。

### seed19 实证（唯一归属可达的 fixture）
配翼 + 归属求解到 identity 后真实回放：
- 12 槽 `is_complete_tredge==True` 且归属全对（defects 全为 FLIPPED/VALID，无 MISMATCH）；
- `count_valid=2`（10 槽 FLIPPED）、`center_color_off=0`、`_fixed_centers_preserved=True`；
- 用 `build_reduced_facelets` 构造虚拟 3×3 后，**`solve_3x3` 返回 `success=True`**（20 步解），
  即虚拟 3×3 **合法且可解**。

### 结论
- 10 槽翻转 = **偶数**，故虚拟 3×3 的翻转总数合法（3×3 允许偶数条棱翻转）。
  这正是「翻转不构成障碍」的原因——即使 10/12 条 FLIPPED，虚拟 3×3 仍可被 3×3 求解器接受。
- 因此**不必**把每条 tredge 解到朝向正确。末段只需：
  1. 12 槽**归属全对**（每槽三块为同一逻辑棱，且在正确槽位）；
  2. 构造虚拟 3×3，用 `solve_3x3` 判定合法（非法则应用 5×5 降阶 parity 宏 OLL/PLL_FIX）。
- seed19 **已达成降阶成功**（归属可达 + 虚拟 3×3 合法），可直接接 Plan 12（3×3 阶段）。
- 剩余种子（seed2/51/7/23/4）卡点收敛为**归属层奇偶**：内容物置换为奇时，纯偶宏（3-cycle）
  无法归位，需 5×5 降阶 parity 宏或奇置换宏改变归属奇偶。
