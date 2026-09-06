# 5x5 Free-slice Foundation（Milestone 3 基础）

> 目标：从「深 beam 盲搜」切换到「标准 free-slice 机制驱动 + 局部搜索辅助」。
> 本文件记录 Foundation 组件、实验结果与下一步路线。

## 关键结论（本轮验证）

1. **中心解会深打乱棱**：`solve_centers5` 用大量宽层动作，把棱系统打成深态。
   因此「逐条配棱 + 每步恢复中心」的旧模型不可行，改用 **批处理 free-slice**：
   打开切片 -> 连续组装/暂存多条翼 -> 批次末统一恢复中心。

2. **4x4 的 P 宏不能直接搬到 5x5**：`2X R U R' F R' F' R 2X'` 对全部宽层动作
   的最终中心 `color_off >= 4`，中心被破坏。

3. **找到 6 条真实的 5x5 free-slice 装翼宏**：在受控分散态下，它们把目标
   中棱与翼的关系等级从分散/组合提升到聚集，且**宏结束后中心 color_off==0**、
   **六个固定面心不被移动**。全部为合法 5x5 求解器动作。
   `2L D R' D' 2L'`, `2L' U R U' 2L`, `2L2 B R2 B' 2L2`,
   `2U F' U' F 2U'`, `2U' F' U F 2U`, `2U2 F' U2 F 2U2`。

4. **宏作用机制**（以 `2U F' U' F 2U'` 为代表）：在 U/F 带内对整条棱组做
   4-循环（中棱 `UL->UF->FR->UB->UL`），把目标棱的翼分派到 FR/BR 等工作带。
   它能**建立目标中棱+单翼的二块组合**，但**单次宏 + 外层 setup 从任意深态
   尚不能一次完成三块完整组装**（实验验证：cap=4 仍常只到组合级）。这正说明
   需要 batch/保存机制（实验 B/C）来把二块组合暂存并累积成三块。

## Foundation 组件

- `solver/edge5/free_slice.py`
  - `FreeSliceState`：active_axis / slice_offset / work_slot / buffer_slot /
    staged_pairs / protected_groups。
  - `EdgeAssemblyRelation`：目标中棱与两翼的聚集等级（0~3）。
  - `FreeSliceMacroEffect` + `analyze_macro`：宏的完整副作用报告
    （中心是否按颜色归面、固定面心是否保持、目标中/两翼前后槽位、
    配对槽增减、触及槽集合）；在真实 Cube5 上重放、不改输入。
  - `edge_relation(state, slot)`：关系级评价（非只数完整配对）。
  - `enumerate_wide_outer_wide_compact(max_outer, slot, start)`：
    枚举 `W + outer^(1..N) + W'`，紧凑状态求关联与中心。
  - `controlled_start(slot, entry)`：构造受控分散态。
  - `WHOLE_EDGE_SWAP_MAIN = ("2B","B2","F2","2B'")` 及 `WHOLE_EDGE_SWAP_PAIRS`
    （BL<->BR, FL<->FR, DB<->UB, DF<->UF），中心保持的整条已配棱搬运宏。
  - `whole_edge_swap_effect`：在该宏下每对整棱的前后槽位映射。

## 测试

`tests/test_free_slice.py`（18 项）覆盖：宏合法性 + 中心归面 + 固定面心保持、
`WHOLE_EDGE_SWAP_MAIN` 中心保持 + 成对搬运映射、`edge_relation` 等级、
`analyze_macro` 一致性、枚举器能找到提升宏、`FreeSliceState` 字段。
（`test_edge5.py` + `test_edge5_search.py` + `test_free_slice.py` = 78 passed。）

## 实验 B/C/D 结果（决定性）

- **实验 B/C（`assemble_validate.py`, `experiment_c*.py`）**：用「外层 setup +
  已发现宏/闭环单元 + 逆setup」在**真实中心已还原打乱 Cube5** 上反复提升关系，
  无论是否允许每单元 `color_off==0`，**都对深打乱态 0 成功率**（cap=2~4 均到
  组合级即停滞，gather 无中心约束也 0/4）。根因：闭环单元 `W outer^n W'` 对
  棱系统净效果仍只是「整带循环」（`2B B 2B'` 等），在深态无法把目标的两翼
  与中棱凑到一起。
- **实验 D（`experiment_d.py`）**：在**受控分散态**（`controlled_start`，
  目标中棱 home + 翼在邻近带）上，open-slice 单元 `W outer^n W'` 枚举
  找到 **972 条 `rel=3 + color_off==0` 的完整组装单元**（如 `2B B 2B'`）。
  即：**只要初始排列有利，单元确实能一次完成整条三块棱**。失败仅发生在
  真实深打乱态（初始排列不利）。
- **结论**：瓶颈不在「单元本身不能组装」，而在「从深态到有利排列的
  **过渡**」。需要"切片保持打开、在带内多次插入、把已成型棱移出带暂存、
  最后统一恢复中心"的**跨多单元连续 free-slice**，而不是逐个孤立闭环单元。

5. **两种「配对」定义必须区分（本轮关键修正）**：
   - `is_edge_paired(cube, slot)` 是 **槽位锚定**：检查「位置 slot」上的三块
     是否色对一致。用于最终验收。
   - `member_slots` / `edge_relation` 是 **类型锚定**：追踪「home 属于该类型
     的三块」当前各在哪。用于装配过程中「把某类三块聚到同一槽」的目标。
   - 二者并非同一件事：某类型三块聚到槽 Y 时，槽 X 未必配对。
   - **结论**：free-slice 装配的搜索目标必须用**类型锚定 + 三块同槽**判定，
     不能用槽位锚定的 `is_edge_paired`（我早前实验误用了后者作验收，导致
     把「已聚好」错判为"未配对"，造成 0/n 假象）。
   - 附：`compact_state` 的 `state_of` / `step` 与真实 `Cube5.apply_move`
     对新旧 300 组随机序列**完全一致**（`tools/research/5x5/diag_compact.py`），
     抽象可信。

6. **打开切片并不必然聚合**：`实验 F` 追踪表明，当目标三块确实分散时，
   `open W` 并不会自动把它们转到某一槽；之前「打开后就 rel=3」是
   目标块恰好已在带内的特例。因此**不能用"就靠开切片聚合"**，必须靠
   主动插入序列把块搬到目标槽。

7. **【决定性】free-slice 需要纯内层切片动作，当前合法动作集不具备**：
   合法动作集只有「1 层外层 + 2 层宽转」，**没有纯内层切片**
   （`3R/3L/3U/3D/3F/3B`）。这是**无法用外层+宽层完成 free-slice 装配的根因**：
   - `cube` 模型本身**已支持** `3R` 等内层切片（`apply_move('3R')` 正常）；
   - 但 `solver/center5/legal_moves.py`(冻结) 与 `compact_state.MOVES`/`MOVE_TABLES`
     只含外层+宽层，**排除内层切片**；
   - `实验 H`：在真实 Cube 上仅用内层切片动作 BFS(d=3)，从深打乱态把目标
     三块**聚成完整棱成功**（3/3 达到 COMBO，其中 1 例 GROUP/三块同槽）。
   - **结论**：edge-pairing 阶段必须**扩展动作集加入纯内层切片（3X）**。
     `state_of` 读取真实 cubie 位置、不受动作集限制，可用于含内层切片态的验证；
     只需把 `3X` 补进 `compact_state.MOVE_TABLES`/`MOVES` 以便快速搜索。

## 下一步（重定向）

- 用**类型锚定**目标（`member_slots`：三块同槽）驱动装配。
- 实现**连续 free-slice 单元**：选定一个工作切片（轴+层），打开后保持不关，
   连续做多次插入，把每条成型的「中+翼」组合用带内动作 **搬出切片带暂存**，
   关闭前统一恢复中心。
- `WHoleEdgeSwapMain`（`2B B2 F2 2B'`）用于把已配棱在带上/带外整体搬运，
   作为暂存/保护区重排的原子操作。
- 把 beam 降级为「定位宏 / 保存路径 / 宏间规划 / 例外处理 / 轨迹生成」。

## 已知限制 / 退出条件

- 逐个「闭环单元 + 外层 setup」从真实深打乱态完成三块组装：**已证伪**。
- 「打开切片即聚合」：**不成立**（目标块分散时无效）。
- 只靠闭环单元无法从深态过渡到有利排列；必须依赖「切片保持打开的连续插入 +
  暂存 + 末批恢复中心」。
- 若在连续 free-slice 骨架下仍无法完成、或动作模型无法表达真实内层切片语义、
  或公式与实体 5x5 机制持续不一致、或时间预算不足，应暂停（按主线方案 3 的
  退出条件）。

## M2.5 进展（本轮）——内层切片入 compact + 装配可行，但联合恢复是硬阻

8. **已把纯内层切片 `3X` 补进 `compact_state`**：`_make_move_tables` 现在
   在 `LEGAL_5X5_CENTER_MOVES`(36 个宽/外层) 之外，额外加入
   `3U/3D/3L/3R/3F/3B` 及其 `'`/`2` 共 18 个动作（`MOVES` 含 54 个）。
   `solver/center5/`(冻结) 未改动；已验证 `3R`(及 `2L`) 的 `compact_step` 与
   真实 `Cube5.apply_move` 一致。`tests/test_edge5*.py`+`test_free_slice.py`
   仍 78 passed。

9. **【突破】装配机制已打通**（`solver/edge5/free_slice_pair.py`）：
   新增 `free_slice_pair.py`（`assemble_edge`/`_beam_search`/`restore_centers_keep_gathered`）
   与 `pairing.py`（M2.5 联合谷式 beam，`joint_search`/`pair_one_edge_joint`）。
   - `assemble_edge` 用 **beam + 内层切片** 从真实「中心已还原深打乱态」把目标
     三块聚拢：**4/4 成功**（2~4 步，`member_slots` 三块同槽）。→ **证明内层切片
     确是 free-slice 装配之必需，且装配本身可解**。
   - 但装配后中心 `color_off` 变为 12~22（内层切片扰动中心，符合 free-slice 预期，
     需末批恢复）。

10. **【决定性阻点】联合目标（`三块同槽 ∧ 中心color_off==0`）由 beam 搜索不可达**：
    - 中心恢复：从已聚拢态（rel=3, co=12）**允许目标暂时拆散**时，**1 步内即可把
      co 降到 0**（`test_center_feasible`，3/3 案例）。
    - **但恢复中心的那一步会拆散已经聚好的三块**：`restore_centers_keep_gathered`
      （全动作/或仅宽+外层）深度 6 内都**无法在保持聚集的前提下把 co 降到 0**
      → 返回 None。
    - 「保持聚集子图」**并不小**：宽/外层动作会整组搬运已聚三块（保持 rel==3），
      使保持聚集 BFS 也**超时爆炸**；而非保持聚集则必然拆散。
    - `joint_search`（谷式 beam，depth 10 / per_bucket 24 / max_buckets 128）
      展开 12 万节点后**仍未命中**「rel==3 ∧ co==0」，FRONTIER_EXHAUSTED。
    - **结论**：中心与棱在**单条装配层面被强耦合**——聚拢需要扰动中心的动作，
      恢复中心则拆散聚拢；逐条「联合目标」的穿谷 beam 无法越过此耦合。

11. **路线判定（按 plan §14 停止条件）**：穿谷 beam 对单棱联合目标**失败**，
    应调用 plan §14 第一行备选：
    **转向「中心闭环宏库 + 固定工作槽 + 双向搜索」**。
    中心恢复不应依赖「保持聚集的逐条搜索」，而应依赖**中心闭环宏**
    （始/终中心均归面、中间可扰动，如 `WHOLE_EDGE_SWAP_MAIN`）来在**批量末**
    恢复全部中心，同时整组搬运已配棱而不拆散它们。
    → 需要新增 `center_closed_macros` / `macro_search`(plan §3.7)，把
    `WHOLE_EDGE_SWAP_MAIN` 等中心闭环宏作为**高层原子动作**，拼接出
    「批量装配 → 闭环宏恢复中心」的骨架，而不是逐条联合搜索。

12. **【决定性根因】中心与内层切片的数学耦合（已证明，本轮）**：从中心已归面
    的紧凑身份态出发，逐动作实测 `color_off`：
    - **只有「1 层外层」18 个动作（U/D/L/R/F/B + ′/2）保持 co==0**；
    - **全部 2 层宽转（2X）与全部内层切片（3X）都会扰动中心**（co 变非 0）。
    - 而 Foundation #7 已证：**仅用外层+宽层无法做 free-slice 翼相对中棱的装配**
      （inner-slice 是必需）。
    - **推论**：free-slice 装配**必然**需用扰动中心的动作（宽/内层），而**唯一
      保持中心的动作（1 层外层）无法完成装配所需的内层搬翼**。→ 装配所需动作集
      与「保持中心归面」所需动作集**不相交**。
    - 实验佐证：`assemble_edge`（3X 驱动）达到 rel=3 时 co 变 12~22；内层切片
      **无法**在保持 rel==3 的前提下把 co 降到 0（`test_inner_restore`，None）；
      wide+outer 也无法把 3X 造成的中心扰动还原（`solve_centers5` 对 3X 打乱无效）；
      `restore_centers_keep_gathered`（全动作/或仅宽层）在深度 6 内都失败。
    - **结论**：**逐条「装配 + 中心恢复」在数学上等价于不可行**。中心扰动是
      **内层装配的固有代价**，只能用**同类的内层/宽层动作**去还原，而这些动作
      又会拆散已装配的三块。

13. **【架构判定】必须采用「批量末统一恢复中心」且用「整组搬运的内层/宽层宏」**：
    既然中心扰动无法在「保持已装配三块」下逐条还原，则：
    - 装配阶段**接受**中心被内层/宽层扰动（co 可累积），逐条/批量把三块聚好；
    - 恢复阶段**不再要求保持单条聚集**，而是**把 12 条全部配对后**，用
      「整组搬运（不拆三块）且能调整中心」的宏（如 `WHOLE_EDGE_SWAP_MAIN`
      及同族 2 层/内层宏的组合）**整体重置中心**，即终点所有三块仍配对 + co==0。
    - 需要验证的关键问题（下一步）：**在「全部 12 条已配对 + 中心被扰动」的态上，
      是否能用「整组搬运 3 块的宏族」把 co 归 0 而不拆散任何一条**。若可行，则
      批量架构成立（等价于 plan M5 的「最后两棱 + 中心回收」但放在批量末）。
    - `macro_search.py`（`find_center_closed_improving` / `discover_closed_macros_on_detail`）
      已写成，用于从真实态挖掘「始/终中心均归面且关系提升」的中心闭环宏；但目前
      深度 3 未发现任何提升宏（与上述耦合一致）。

