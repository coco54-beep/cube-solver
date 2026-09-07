可以。下面给出从当前 **430 tests passed、M1+M2 已入库**，一直到“任意合法5×5打乱能够端到端还原”的完整实施计划。后续可按此连续推进，不再每完成一小段就重新确认方向。

---

# 〇、5×5 Current Status（当前状态）

> 本节为当前实际进度总览，随里程碑推进更新。

### Completed
- [x] Center solving（中心还原，已冻结）
- [x] Protected partial edge pairing（保护式部分配棱，可稳定推进到 7～10 条，具体取决于输入 scramble；`pair_all_protected` 对相同状态是确定的）
- [x] Pairing determinism audit（配棱确定性审计：相同输入、相同预算、相同宏顺序 → 相同结果）
- [x] Physical move semantics audit（物理动作语义审计）
- [x] Remove non-physical 3X/4X/5X from compact search（从 compact 搜索移除非物理深层动作）
- [x] Legal free-slice Gate 1（合法 free-slice 插翼 Gate 1）
- [x] Fixed work layout Gate 2（固定工作布局 + 纯外层定位表）
- [x] Atomic wing insertion Gate 3（确定性原子插翼，rel≥2 位置组合，朝向推迟到 rel3）
- [x] Real Cube5 replay validation（真实 Cube5 重放验证）
- [x] Full suite 553 tests passing

### Current legal move model（当前合法动作模型）
只允许外层转与两层宽转：

```text
1X: legal（外层）
2X: legal（两层宽转）
3X/4X/5X: non-physical in the current Cube5 engine（非法，因其会移动 6 个固定面心）
```

正式搜索动作集固定为 36 个 1X/2X 动作。

### Next gates（后续 Gate）
- [x] Gate 2: fixed work layout（固定工作布局 + 纯外层定位表，`solver/edge5/freeslice_layout.py`）
- [x] Gate 3: deterministic atomic wing insertion（确定性原子插翼，`solver/edge5/atomic_insert.py`）
- [ ] Gate 4: store partial assembly（保存部分组合）
- [ ] Gate 5: complete one tredge（完整配成一条三块棱）
- [ ] Gate 6: protected ladder 1→2→4→6→8→10（保护式累积梯度）
- [ ] Gate 7: last two edges and parity（最后两棱与奇偶）
- [ ] End-to-end deep scramble regression（端到端深乱回归）

> 说明：当前「9→12」并非已被群论证明的硬不变量。更严谨表述为：
> 在当前合法动作集、宏库与搜索预算下，最后 3～5 条需要非单调、多步穿谷及专用最后两棱处理；
> 现有贪婪、beam 与双向 BFS 未能稳定跨越。除非给出群论证明，否则不宣称其为数学上的硬不变量。

---

# 一、总路线

完整流程固定为：

```text
输入合法5×5状态
    ↓
中心还原 solve_centers5（已完成、冻结）
    ↓
常规棱配对（前10条）
    ↓
最后两棱 + 配对奇偶
    ↓
验证：中心按颜色归面 + 12条棱全部配对
    ↓
构造 reduced 3×3
    ↓
检测并修正降阶奇偶
    ↓
调用 solve_3x3
    ↓
把3×3动作映射为5×5外层动作
    ↓
整机重放、校验、简化动作
```

剩余工作分成七个里程碑：

| 里程碑 | 内容                                |
| ------ | ----------------------------------- |
| M2.5   | 穿谷单棱构造器                      |
| M3     | 保护式常规棱配对                    |
| M4     | 前10条棱配对                        |
| M5     | 最后两棱与配对奇偶                  |
| M6     | reduced 3×3 映射与奇偶检测          |
| M7     | 接入 `solve_3x3`                    |
| M8     | `solver5.py` 端到端集成、回归和优化 |

---

# 二、模块规划

建议最终形成：

```text
solver/
├── center5/                    # 已冻结
├── edge5/
│   ├── __init__.py
│   ├── positions.py            # 已完成
│   ├── state.py                # 已完成
│   ├── moves.py                # 已完成
│   ├── compact_state.py        # 联合搜索紧凑状态
│   ├── heuristic.py            # 搜索评分和下界
│   ├── single_edge.py          # 单棱构造器正式实现
│   ├── macro_search.py         # 中心闭环宏挖掘
│   ├── macros.py               # 已验证高层宏
│   ├── protected.py            # 已配棱保护模型
│   ├── regular_pairing.py      # 常规前10棱
│   ├── last_edges.py           # 最后两棱
│   ├── parity.py               # 棱配对/降阶奇偶
│   └── solver.py               # solve_edges5
├── reduction5/
│   ├── __init__.py
│   ├── state.py                # reduced 3×3 状态
│   ├── mapping.py              # Cube5 → Cube3
│   ├── validation.py           # 降阶合法性检查
│   └── replay.py               # 3×3外层动作回放到Cube5
└── solver5.py                  # 总流程

tools/research/5x5/
├── benchmark_single_edge.py
├── search_edge_macros.py
├── analyze_last_edges.py
└── edge_pairing_analysis.md

tests/
├── test_edge5_search.py
├── test_edge5_regular_pairing.py
├── test_edge5_last_edges.py
├── test_edge5_parity.py
├── test_reduction5.py
└── test_solver5_e2e.py
```

原则：

- 不修改已冻结的 `solver/center5/`；
- 新算法只通过其公开状态判定或已有接口使用中心模块；
- 不把研究脚本直接作为运行时依赖；
- 所有正式动作必须在真实 `Cube5` 上重放验证。

---

# 三、M2.5：破解深打乱单棱构造

这是当前第一优先级。

## 3.1 联合目标

废弃严格的：

```text
Gather完成后保持目标棱不拆 → Restore中心
```

改为单一联合目标：

```python
is_edge_paired(cube, target_type) \
and centers_are_color_solved(cube)
```

搜索过程中允许：

- 目标三块棱暂时聚集后再次拆散；
- 中心错位暂时增加；
- 匹配数从3退回2、1甚至0；
- 未保护棱任意变化。

## 3.2 紧凑状态

建立：

```python
@dataclass(frozen=True)
class CompactPairingState:
    middle_pos: int
    wing_pos_a: int
    wing_pos_b: int
    center_color_signature: tuple[int, ...]
```

其中：

- 两个同色翼不可区分时，对位置排序；
- 中心签名只记录位置颜色，不记录同色块身份；
- 第一版不记录其余33个棱块身份；
- 每条候选路径最终必须在完整 `Cube5` 上重放，防止抽象状态丢失约束。

如果紧凑状态出现不同真实状态映射到同一键、导致错误剪枝，再按需增加：

```python
work_area_edge_signature
```

而不是直接退回完整98块状态。

## 3.3 穿谷分桶 beam

每层候选按以下维度分桶：

```text
目标匹配成员数：0 / 1 / 2 / 3
中心颜色错位：0 / 1–8 / 9–16 / 17–24 / 25+
穿谷深度：0 / 1–2 / 3–4 / 5+
```

每个桶独立保留候选，防止“目标已聚集但中心无法恢复”的状态占满整个 beam。

评分建议：

```python
score = (
    goal_reached,
    target_members_in_same_slot,
    -target_piece_slot_distance,
    -center_color_mismatch,
    -valley_depth,
    -path_length,
)
```

不能把评分做成硬单调约束。

## 3.4 多样性保留

同一层除高分候选外，额外保留：

- 中心错位最低的一批；
- 目标棱聚集度最高的一批；
- 与当前最优状态差异最大的一批；
- 最近首次达到某种 `(matched, center_bucket)` 组合的一批。

这样可以保留跨越局部低谷的路线。

## 3.5 禁忌与动作剪枝

只做安全剪枝：

- 禁止动作后立即执行其逆；
- 同一面连续动作规范化；
- 四次同动作循环不展开；
- 相邻同轴可交换动作按规范顺序保留一种；
- 不禁止“暂时拆棱”；
- 不禁止“暂时增加中心错位”。

## 3.6 双向/meet-in-the-middle 备选

如果穿谷 beam 对长度8～10仍无明显改善，再加入双向搜索。

目标集合不是单状态，而是：

```text
目标色对三块处于同一逻辑槽
+
中心按颜色归面
```

可以先固定一个工作槽以缩小目标集合。

流程：

```text
当前紧凑状态正向展开 d1
目标集合反向展开 d2
在紧凑状态键上相遇
拼接动作
完整 Cube5 重放验证
```

## 3.7 中心闭环宏挖掘

与穿谷搜索并行研究，但不阻塞主线。

宏的验收条件改为：

```text
起点中心颜色归面
终点中心颜色归面
中间可任意扰动中心
对目标棱产生有利变化
```

候选结构：

```text
S A S'
[A, B]
S [A, B] S'
A B C B' A'
```

不再要求：

- 纯翼3-cycle；
- 固定所有中棱；
- 只移动三个棱块。

正式宏只需满足：

- 中心最终恢复；
- 固定面心保持；
- 动作合法；
- 对某类配对状态有稳定效果；
- 在真实 `Cube5` 上可重放；
- 逆动作正确。

## 3.8 M2.5 验收标准

固定同一组种子和动作生成规则：

| 打乱长度 |               最低目标 |
| -------: | ---------------------: |
|     1～3 |                   100% |
|     4～6 |                   ≥90% |
|    8～10 | ≥70%，且明显优于旧beam |
|       15 |   至少出现稳定成功案例 |

所有成功结果必须满足：

```python
assert is_edge_paired(replay, target)
assert centers_are_color_solved(replay)
assert fixed_face_centers_unchanged(replay)
assert all_moves_are_legal(result.moves)
```

失败必须返回：

```text
NODE_LIMIT
DEPTH_LIMIT
TIME_LIMIT
FRONTIER_EXHAUSTED
ABSTRACTION_REPLAY_MISMATCH
```

不能无限搜索，也不能把部分结果报告为成功。

---

# 四、M3：保护式单棱构造

M2.5解决“能否构造一条”，M3解决“能否在已有成果上再增加一条”。

## 4.1 保护对象按块组身份跟踪

不能只保护槽位，因为外层转会整体搬运配好的棱。

```python
@dataclass(frozen=True)
class PairedEdgeGroup:
    edge_type: EdgeType
    middle_piece: int
    wing_piece_a: int
    wing_piece_b: int
```

检查：

```python
def is_group_still_paired(cube, group) -> bool:
    """三个成员仍聚集在某个逻辑槽，不要求原槽不变。"""
```

## 4.2 搜索状态加入保护摘要

```python
@dataclass(frozen=True)
class ProtectedPairingState:
    target_state: CompactPairingState
    protected_group_slots: tuple[int, ...]
    center_color_signature: tuple[int, ...]
```

保护约束分两档：

### 硬保护

任何一步都不允许拆散已有配对。

优点是可控，缺点是可能找不到路径。

### 软保护

允许短暂拆散，但最终必须恢复；评分中施加高惩罚。

第一版先尝试硬保护：

```text
k = 0、1、2、3
```

若 k 增加后搜索断裂，再启用有预算的软保护：

```text
最多临时拆1条
最多连续拆散4～6层
终点必须全部恢复
```

## 4.3 固定工作槽和工作带

根据 `EdgeMoveEffect` 自动选择工作区，不照搬人工公式。

候选工作槽应满足：

- 外层动作容易将目标中棱送入；
- 宽层动作能插入两翼；
- 涉及的逻辑槽数量少；
- 容易将已配棱移入保护区；
- 宏结束时中心容易闭环。

对12个槽进行离线评分，最终固定一个主工作槽和一个备用槽。

## 4.4 高层动作集

M3搜索不再只使用36个原子动作，也使用经过验证的宏：

```text
外层定位宏
单翼插入宏
中心闭环宏
工作槽交换宏
已配棱移出宏
```

每个宏记录：

```python
@dataclass(frozen=True)
class EdgePairMacro:
    name: str
    moves: tuple[str, ...]
    precondition: ...
    edge_effect: ...
    center_effect: ...
    protected_slots_touched: ...
```

高层搜索输出宏序列，最后展开成原子动作。

## 4.5 M3验收

分别构造具有 `k` 条预配棱的状态：

```text
k = 0、1、2、3
```

要求：

```text
输入：k条已配
输出：至少k+1条已配
原k条仍配对
中心颜色归面
动作可重放
```

通过后扩展到：

```text
k = 4、5、6
```

---

# 五、M4：常规前10条棱配对

## 5.1 主循环

```python
def pair_regular_edges(
    cube: Cube5,
    target_count: int = 10,
) -> EdgePairingResult:
    while paired_count(cube) < target_count:
        target = choose_next_edge_type(cube)
        result = pair_one_protected_edge(cube, target, protected)
        ...
```

## 5.2 目标选择策略

优先顺序：

1. 已经配好，直接加入保护集合；
2. 某槽已有中棱+一个匹配翼；
3. 三个成员中已有两个同槽；
4. 目标翼靠近工作槽；
5. 对当前保护区干扰最少；
6. 完全分散的目标最后处理。

每轮可对多个候选目标执行有限前瞻：

```text
估算配对成本
估算保护冲突
估算中心恢复成本
```

选择预计总代价最低者。

## 5.3 保护区动态管理

若保护区占据工作路径，可使用外层动作整体重新排列配好棱，因为外层动作不会拆组，也不会破坏中心颜色归面。

保护集合记录块组身份，而不是固定槽名。

## 5.4 允许有限回退

如果严格单调从 `k` 到 `k+1` 无解，允许：

```text
临时拆1条已配棱
一次操作最终净增加至少1条
```

即：

```text
k → k-1 → k+1
```

不能无限破坏已有成果。

## 5.5 M4验收

分阶段要求：

```text
随机状态配到4条
→ 配到6条
→ 配到8条
→ 稳定配到10条
```

前10条完成后必须：

```python
assert paired_edge_count(cube) >= 10
assert centers_are_color_solved(cube)
```

建议随机回归：

| 打乱长度 | 案例数 |
| -------: | -----: |
|        5 |     20 |
|       10 |     20 |
|       20 |     20 |
|       50 |     20 |

研究期允许失败，但正式进入M5前，固定回归集必须稳定可复现。

---

# 六、M5：最后两棱与配对奇偶

最后两条不能继续依赖自由槽，单独实现。

## 6.1 规范化最后两棱状态

通过外层动作，把两条未配棱搬到固定工作槽，例如：

```text
UF / UB
```

其他10条作为保护集合。

对最后两条的：

- 两个中棱位置；
- 四个翼位置；
- 局部中心颜色状态；
- 配对关系；

进行规范化编码。

## 6.2 枚举状态类别

从大量随机“前10条已配”状态收集最后两棱签名，按对称归一化，分类为：

```text
可直接配对
翼需要交叉交换
两组翼错配
降阶单棱翻转型
其他奇偶类
```

不要仅凭人工名称判断，必须由置换和重放验证。

## 6.3 最后两棱查表

优先构建小型精确表，而不是继续通用 beam：

```python
LAST_EDGE_TABLE[state_signature] = macro_sequence
```

从已解决状态反向 BFS：

- 使用中心闭环宏；
- 固定或整体搬运前10条配好棱；
- 只保存最后两棱的规范化签名；
- 每条生成路径在完整 `Cube5` 上验证。

如果状态空间仍大，按奇偶类别拆分多个表。

## 6.4 奇偶检测

明确区分：

1. 实体翼块没有独立翻转；
2. 配对后逻辑棱可能表现为降阶单棱翻转；
3. reduced 3×3 可能因此成为普通3×3不可达状态。

接口：

```python
@dataclass(frozen=True)
class EdgeParityReport:
    pairing_parity: int
    reduced_edge_flip_parity: int
    reduced_edge_perm_parity: int
    corner_perm_parity: int
    parity_kind: EdgeParityKind
```

奇偶宏必须满足：

- 修正目标奇偶；
- 最终12条棱全部配对；
- 中心颜色归面；
- 不破坏角块合法性；
- 固定面心保持。

## 6.5 M5验收

```python
result = solve_edges5(cube)

assert result.success
assert all_edges_paired(result_cube)
assert centers_are_color_solved(result_cube)
assert validate_5x5(result_cube).valid
```

覆盖：

- 普通最后两棱；
- 每个已识别奇偶类别；
- 宏及其逆；
- 固定seed随机状态；
- 从原状态重放。

---

# 七、M6：构造 reduced 3×3

中心和棱配对完成后，把5×5视为逻辑3×3。

## 7.1 映射规则

### 角块

8个实体角块直接映射到3×3角块：

```text
位置
置换
朝向
```

### 逻辑棱

每个逻辑槽的三块棱已经配对，因此映射为一个3×3逻辑棱：

```text
色对身份
逻辑位置
逻辑朝向
```

### 中心

使用六个固定面心确定面颜色和坐标系。

## 7.2 映射接口

```python
@dataclass(frozen=True)
class ReducedCube3State:
    corner_perm: tuple[int, ...]
    corner_ori: tuple[int, ...]
    edge_perm: tuple[int, ...]
    edge_ori: tuple[int, ...]
    face_colors: tuple[Color, ...]
```

```python
def build_reduced_cube3(cube5: Cube5) -> ReducedCube3State:
    ...
```

前置条件不满足时明确失败：

```text
CENTERS_NOT_COLOR_SOLVED
EDGES_NOT_ALL_PAIRED
INVALID_LOGICAL_EDGE_COLORS
INCONSISTENT_LOGICAL_EDGE_ORIENTATION
```

## 7.3 reduced 合法性

调用3×3求解器前检查：

```text
角朝向和 mod 3 == 0
棱朝向和 mod 2 == 0
角置换奇偶 == 棱置换奇偶
每种角/棱身份各一次
```

如果失败：

- 若属于5×5降阶奇偶，返回M5做奇偶修正；
- 若不属于已知降阶奇偶，则报告映射或配对错误；
- 不把非法状态直接交给 `solve_3x3`。

## 7.4 M6验收

测试来源：

1. 已还原5×5；
2. 仅执行外层打乱的5×5；
3. 中心解好、棱配好但逻辑3×3打乱；
4. 已知奇偶状态；
5. 随机配对输出。

应验证 reduced 状态与外层动作效果一致。

---

# 八、M7：接入 `solve_3x3`

## 8.1 适配现有接口

根据现有求解器输入，提供：

```python
def reduced_state_to_3x3_input(state: ReducedCube3State):
    ...
```

可能是：

- `Cube3` 对象；
- cubie permutation/orientation；
- 54 facelets。

优先使用内部 cubie 表示，避免重复颜色解析。

## 8.2 只允许外层动作

3×3求解阶段只能输出：

```text
U D L R F B
及其 ' / 2
```

不能输出任何宽层动作。

原因：

- 外层动作整体搬运配好的三块棱；
- 不拆配对；
- 中心按颜色仍归面。

## 8.3 回放验证

```python
cube5_after_reduction.apply_moves(solution3)
```

必须验证：

```python
assert cube5_after_reduction.is_solved()
```

而不是只验证 reduced 3×3 模型已解。

同时验证：

```python
assert all_edges_paired_during_or_after_outer_solution
assert centers_are_color_solved(...)
```

## 8.4 M7验收

- 外层短打乱全部成功；
- reduced随机状态成功；
- 3×3输出动作全部可由5×5 parser解析；
- 返回动作在原始5×5上重放后完全还原。

---

# 九、M8：正式接入 `solver5.py`

## 9.1 总结果对象

```python
@dataclass(frozen=True)
class Solve5Result:
    success: bool
    moves: tuple[str, ...]
    center_moves: tuple[str, ...]
    edge_moves: tuple[str, ...]
    parity_moves: tuple[str, ...]
    reduced_3x3_moves: tuple[str, ...]
    diagnostics: Solve5Diagnostics
    error_code: str | None = None
    message: str = ""
```

诊断至少记录：

```text
中心3-cycle数量
中心setup缓存命中
单棱搜索节点数/深度
配对顺序
保护回退次数
最后两棱类型
奇偶类型
各阶段动作数和耗时
```

## 9.2 正式流水线

```python
def solve_5x5(cube):
    validate_5x5(cube)

    center_result = solve_centers5(cube)
    apply(center_result.moves)

    edge_result = solve_edges5(cube)
    apply(edge_result.moves)

    reduced = build_reduced_cube3(cube)

    if reduced_has_parity(reduced):
        parity_result = fix_reduction_parity(cube)
        apply(parity_result.moves)
        reduced = build_reduced_cube3(cube)

    solution3 = solve_3x3(reduced)
    apply(solution3.moves)

    replay_all_from_original()
    verify_fully_solved()

    return Solve5Result(...)
```

每个阶段失败立即返回明确错误，不继续污染状态。

## 9.3 输入修改约定

建议：

```text
solve_5x5 默认不修改输入Cube5
内部使用副本
返回动作序列
最终从原始状态重放验证
```

---

# 十、动作简化与计数

完整功能成功后再优化，不能提前影响正确性。

## 10.1 局部合并

```text
R R    → R2
R R'   → 删除
R2 R   → R'
2R 2R' → 删除
```

严格区分：

```text
R2  = 外层180°
2R  = 两层宽转90°
2R2 = 两层宽转180°
```

## 10.2 跨宏抵消

宏展开后统一简化：

```text
... S + S' ...
```

但不能跨越不可交换动作错误重排。

## 10.3 阶段统计

输出：

```text
raw moves
simplified moves
center moves
edge-pairing moves
parity moves
3×3 moves
```

第一版目标仍以正确率为主，不以动作最短为阻塞条件。

---

# 十一、完整测试矩阵

## 11.1 单元测试

覆盖：

- 紧凑状态与真实状态一致；
- 每个原子动作影响一致；
- 宏效果与真实重放一致；
- 保护组跟踪；
- 最后两棱签名；
- 奇偶分类；
- reduced映射；
- 动作简化。

## 11.2 分阶段随机测试

### 单棱构造

```text
长度1、3、5、8、10、15
```

### 前10棱

```text
长度5、10、20、50
```

### 全棱配对

```text
普通状态
最后两棱状态
每种奇偶状态
```

### 完整5×5

逐步扩大：

```text
短打乱：100例
中等打乱：100例
长打乱：50例
持续随机：夜间/非CI测试
```

## 11.3 每个端到端案例验证

```python
original = scrambled.copy()
result = solve_5x5(original)

assert result.success

replay = scrambled.copy()
replay.apply_moves(result.moves)

assert replay.is_solved()
assert validate_5x5(replay).valid
assert all_moves_are_legal(result.moves)
```

## 11.4 确定性

固定输入和配置应得到相同结果：

```python
solve_5x5(cube).moves == solve_5x5(cube).moves
```

除非显式启用随机搜索模式。

## 11.5 CI与慢测试分离

```text
普通CI：单元测试 + 固定短案例
slow：中长打乱
stress：大量随机状态和性能统计
```

避免日常全量测试因搜索耗时失控。

---

# 十二、性能和资源上限

所有搜索接口统一支持：

```python
SearchLimits(
    max_nodes=...,
    max_depth=...,
    timeout_seconds=...,
    beam_width=...,
)
```

失败时返回搜索统计。

不能出现：

- 无限循环；
- 无边界BFS；
- CI机器内存爆炸；
- 超时后没有诊断；
- 搜索失败却返回部分动作并标记成功。

setup、最后两棱表和宏库均应版本化缓存，缓存键包含：

```text
动作集合
位置编号版本
状态编码版本
宏库版本
```

---

# 十三、提交顺序

建议按以下提交推进：

```text
1. feat(5x5-edge): add compact joint pairing state and valley search

2. research(5x5-edge): add center-closed macro discovery and benchmarks

3. feat(5x5-edge): add protected paired-edge tracking

4. feat(5x5-edge): implement regular pairing planner

5. test(5x5-edge): add protected pairing and first-ten regressions

6. feat(5x5-edge): solve last two edges and classify parity

7. test(5x5-edge): add last-edge and parity regressions

8. feat(5x5-reduction): map paired cube to reduced 3x3

9. feat(5x5): integrate reduced solve_3x3 replay

10. feat(5x5): implement end-to-end solve_5x5 pipeline

11. test(5x5): add randomized end-to-end regression suite

12. perf(5x5): simplify moves and version search caches

13. docs(5x5): document reduction architecture and known limits
```

不要把所有工作压成一个大提交。

---

# 十四、各阶段停止条件与备选路线

## 穿谷 beam 仍失败

转向：

```text
中心闭环宏库
+ 固定工作槽
+ 抽象状态双向搜索
```

不再无上限扩大 beam。

## 硬保护无法增加配对数

启用：

```text
有限软保护
允许暂拆1条
终点净增加1条
```

## 前10棱成功、最后两棱状态太复杂

采用：

```text
状态规范化
+ 小状态反向查表
+ 奇偶类别分表
```

不强迫常规配对器解决最后两棱。

## reduced 3×3 非法

先判断是否为已知降阶奇偶：

- 是：执行奇偶宏；
- 否：视为配对器或映射器缺陷，停止并报告；
- 禁止让3×3求解器处理非法输入。

## 完整随机状态仍有失败

保留完整诊断：

```text
失败阶段
搜索边界
目标棱
保护集合
中心签名
最后两棱类别
reduced合法性报告
随机seed和打乱动作
```

将失败样例固化为回归测试后再修复。

---

# 十五、最终完成标准

只有同时满足以下条件，才能宣布5×5求解器完成：

1. 中心按颜色全部归面；
2. 六个固定面心保持；
3. 12条逻辑棱全部配对；
4. 降阶奇偶能够检测和处理；
5. reduced 3×3状态合法；
6. `solve_3x3`输出能在真实 `Cube5` 上重放；
7. 最终98个 cubie全部还原；
8. 输入对象修改行为明确；
9. 所有动作合法且可解析；
10. 固定随机回归稳定通过；
11. 搜索全部有节点、深度和时间上限；
12. 失败返回结构化诊断，不假装成功；
13. 全量现有测试保持通过；
14. 中心冻结模块无回归改动。

---

# 十六、预计剩余工作量

按当前进度粗估：

| 工作              |         预计有效开发时间 |
| ----------------- | -----------------------: |
| M2.5 穿谷单棱构造 |                   2～5天 |
| M3 保护式构造     |                   2～5天 |
| M4 前10棱         |                   2～5天 |
| M5 最后两棱和奇偶 |                   3～7天 |
| M6 reduced 3×3    |                   1～2天 |
| M7/M8 集成与回归  |                   2～5天 |
| **合计**          | **约12～29个有效开发日** |

最大不确定性仍在：

```text
深状态单棱构造
保护已有配对
最后两棱奇偶
```

---

## 最终执行顺序

后续直接按下面这条主线连续做：

```text
联合紧凑状态
→ 穿谷分桶beam
→ 中心闭环宏
→ 稳定单棱构造
→ 保护组跟踪
→ 前10棱
→ 最后两棱查表
→ 奇偶修正
→ reduced 3×3
→ solve_3x3
→ solver5端到端
→ 随机回归
→ 动作优化
```

其中只有遇到明确的架构性矛盾或数学不可达状态时才需要暂停重新决策；普通阶段完成后无需逐段再确认。