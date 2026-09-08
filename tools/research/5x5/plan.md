明白，只讨论**5 阶求解算法**，不讨论 UI、软件架构和手机端开发。

你现在的算法已经能保护式完成 8～10 条完整 tredge，剩余问题集中在最后 2～4 条的中棱错配、翻转和奇偶；“以中棱为锚继续配翼”已实证不可达，因此下一步必须转向**切片宏 + 末段整体规划**。[1]

# 剩余完整解法

```text
已完成中心
→ 普通方法完成前8条完整tredge
→ 保留4条作为工作区
→ 用中心恢复型切片宏解决中棱错配
→ 整体解决最后4条
→ 修正最后2条/单棱翻转/奇偶
→ 得到12条VALID tredge
→ 降阶成3×3
→ 使用现有3×3算法完成
```

关键改变是：

> 不要继续贪心做到 10 条再想办法补最后两条，而应主动保留最后 4 条作为统一末段，用 3-cycle 和 parity 宏整体解决。

---

# Plan 1：定义末段抽象状态

不要再直接按 5×5 全贴纸搜索。把每个棱槽抽象为：

```python
TredgeSlot(
    middle_id,          # 中棱属于哪条逻辑棱
    left_wing_id,       # 左轨翼属于哪条逻辑棱
    right_wing_id,      # 右轨翼属于哪条逻辑棱
    middle_orientation,
    left_orientation,
    right_orientation,
)
```

每条槽分为：

```text
VALID
    中棱、左右翼属于同一逻辑棱，方向也正确

FLIPPED
    三块归属正确，但降阶方向错误

MIDDLE_MISMATCH
    两翼匹配，中棱属于其他逻辑棱

LEFT_WING_MISMATCH
RIGHT_WING_MISMATCH
MULTI_MISMATCH
```

定义整局缺陷签名：

```python
EdgeReductionState(
    slots[12],
    valid_mask,
    flipped_mask,
    protected_mask,
)
```

后面的搜索只在这个抽象状态上规划，找到宏序列后再回放到底层魔方。

---

# Plan 2：不要搜索任意公式，搜索三类目标宏

Gate 5c 的目标已经明确：允许宏执行过程中破坏中心，但宏结束时必须恢复中心，同时改变中棱和翼的相对归属。[1]

优先寻找以下三类宏。

## 宏 A：中棱 3-cycle

目标效果：

```text
middle(A) → B
middle(B) → C
middle(C) → A
```

同时尽可能：

```text
左右翼保持原槽
中心终态恢复
其他9条tredge不变
```

这是最重要的宏，因为当前主要缺陷就是：

```text
翼对已经正确
但中棱属于另一条逻辑棱
```

不要优先搜索中棱二交换。合法魔方置换通常有奇偶约束，三循环更容易实现。

理想效果：

```text
M: (A B C)
LW: identity
RW: identity
centers: identity
```

如果做不到纯中棱 3-cycle，可接受：

```text
M:  (A B C)
LW: (A B C)
RW: controlled permutation
```

只要其副作用已知并且可由第二个宏消除。

---

## 宏 B：单侧翼 3-cycle

分别寻找：

```text
左翼轨道3-cycle
```

和：

```text
右翼轨道3-cycle
```

目标效果：

```text
LW: (A B C)
M: identity
RW: identity
```

或者镜像版本：

```text
RW: (A B C)
M: identity
LW: identity
```

它们用于解决：

- 某一枚翼属于错误逻辑棱；
- 左右翼轨道位置错误；
- 中棱已正确但翼分配不正确；
- 中棱 3-cycle 宏产生的受控副作用。

---

## 宏 C：翻转/奇偶修正

目标不是简单交换 cubie，而是改变降阶棱的有效朝向：

```text
FLIPPED → VALID
```

可以允许暂时影响另一条缓冲 tredge，但宏结束时必须：

```text
目标翻转被修正
中心恢复
固定面心不变
其他非缓冲tredge保持VALID
```

如果单目标翻转受群约束不能独立实现，就搜索双目标形式：

```text
flip(A) + flip(B)
```

然后通过 setup、缓冲槽和第二个宏消除辅助缺陷。

---

# Plan 3：用 commutator 和 conjugate 搜索宏

不要从所有动作做普通 BFS。按照以下结构搜索：

## 一级：基本交换子

```text
[A, B] = A B A' B'
```

其中：

```text
A = 内层切片或宽层动作
B = 1～3步外层动作
```

优先模板：

```text
[slice, outer]
[slice, outer outer]
[slice, outer outer outer]
```

---

## 二级：共轭交换子

```text
X [A, B] X'
```

其中 `X` 把目标槽搬到工作位。

搜索时不需要为12个槽分别找公式。只需找到一个标准工作位宏，再通过 setup 共轭覆盖其他槽。

---

## 三级：两个宏组合恢复副作用

如果一个候选能调整中棱，但中心未完全恢复，可以搜索：

```text
C1 C2
```

其中：

```text
C1：产生目标中棱变化，同时产生中心缺陷
C2：消除中心缺陷，同时不撤销目标变化
```

最终只要求整个组合满足：

```text
centers_solved(final)
fixed_centers_unchanged(final)
relative_assignment_changed(initial, final)
```

这正是当前 Gate 5c 的目标条件。[1]

---

# Plan 4：按置换效果筛选候选宏

每个搜索结果先在复原魔方上计算完整效果：

```python
MacroEffect(
    middle_permutation,
    left_wing_permutation,
    right_wing_permutation,
    middle_orientation_delta,
    left_orientation_delta,
    right_orientation_delta,
    center_permutation,
    affected_slots,
    move_count,
)
```

只保留下列候选：

## 一级候选

```text
中心终态完全恢复
固定面心不变
只影响不超过3～4条棱
中棱或单侧翼产生3-cycle
```

## 二级候选

```text
中心恢复
影响5～6条棱
但副作用可由另一个已知宏消除
```

## 直接淘汰

```text
宏结束后中心仍乱
只是整体搬动完整槽
中棱与翼相对归属没有改变
动作回放效果与搜索效果不一致
影响范围过大且无稳定逆修复
```

特别注意：

```text
M、LW、RW三者执行完全相同置换
```

这种宏只是整体搬槽，没有修复价值。

---

# Plan 5：前8条与最后4条分开求解

你当前能累计 8～10 条，但最后 2～4 条卡住。[1] 最稳定的策略不是尽量做到 10 条，而是：

## 普通阶段

```text
0 → 1 → 2 → … → 8条VALID tredge
```

保护这 8 条。

## 末段阶段

剩余 4 条全部取消贪心保护，作为工作区：

```text
A、B、C、D
```

这样至少有：

- 一个目标槽；
- 一个来源槽；
- 一个缓冲槽；
- 一个辅助/奇偶槽。

三循环需要至少三个活动对象，因此保留四条会明显比只剩两条更容易。

---

# Plan 6：最后4条使用抽象宏规划器

在只剩4条时，不再逐块手写判断，而是在宏效果层运行小型搜索。

状态只包含：

```text
4个中棱归属
4个左翼归属
4个右翼归属
相关方向
```

动作不是基础转动，而是已经验证的宏：

```text
middle_cycle(A, B, C)
left_wing_cycle(A, B, C)
right_wing_cycle(A, B, C)
flip_macro(A, B)
```

可使用 BFS、A* 或 IDA*。

推荐启发式：

```python
h = (
    middle_mismatch_count
    + left_wing_mismatch_count
    + right_wing_mismatch_count
    + 2 * flipped_count
)
```

目标状态：

```text
4条全部VALID
```

由于只有4条活动棱，抽象状态空间远小于整颗5×5魔方。

---

# Plan 7：中棱错配的具体解法

假设剩余4槽中，翼对逻辑归属为：

```text
槽A：翼A + 中棱B
槽B：翼B + 中棱C
槽C：翼C + 中棱A
槽D：翼D + 中棱D
```

那么中棱形成：

```text
A → C
B → A
C → B
```

直接应用一个逆向中棱 3-cycle：

```text
middle_cycle(A, C, B)
```

即可一次修复三条。

如果中棱关系表现为二交换：

```text
槽A：翼A + 中棱B
槽B：翼B + 中棱A
```

不要搜索纯二交换。暂时引入缓冲槽 C：

```text
(A B) 借助 C 分解成两个3-cycle
```

可以在抽象规划器中自动求解，不必硬编码具体分解；原则是：

```text
暂时破坏C
→ 把A/B二交换扩展为三循环问题
→ 第二个三循环恢复C
```

如果仍受奇偶约束，就使用第四个工作槽 D。

---

# Plan 8：左右翼错配的具体解法

如果中棱已经正确，但某个 wing orbit 形成循环：

```text
左翼A在槽B
左翼B在槽C
左翼C在槽A
```

执行对应的：

```text
left_wing_cycle(A, C, B)
```

右翼同理。

如果是左右翼分别存在不同循环：

```text
先修左翼轨道
重新分析状态
再修右翼轨道
```

不要假定第一个宏完全不影响另一个轨道，应以实际 `MacroEffect` 更新状态。

---

# Plan 9：最后两条不能直接解时主动解锁一条

如果已经做到 10 条，剩下两条互换或翻转：

```text
A、B存在缺陷
```

不要坚持保护另外10条。选择一条容易恢复的已完成 tredge C：

```text
protected = protected - {C}
active = {A, B, C}
```

然后：

1. 用 3-cycle 修复 A；
2. 缺陷转移到 B/C；
3. 再用另一个 3-cycle 修复 B；
4. 最后恢复 C。

因此最后两条的通用解法是：

```text
2条缺陷
→ 主动释放第3条
→ 转成3条末段
→ 用3-cycle解决
```

如果涉及方向奇偶，则释放第四条，转入最后四条规划器。

---

# Plan 10：翻转与奇偶处理

当 12 条看似完整时，不能只检查颜色归属，还要构造虚拟3×3并检查合法性。

需要区分：

## 情况 A：普通方向错误

三块属于同一逻辑棱，但整个 tredge 相对目标方向反转：

```text
FLIPPED tredge
```

使用翻转宏修复。

## 情况 B：抽象3×3出现单棱翻转

表现为：

```text
12条tredge归属都正确
但虚拟3×3棱方向和非法
```

这是降阶奇偶，需要执行 5×5 层面的 parity 宏，然后重新检查 12 条 tredge。

## 情况 C：边角置换奇偶不匹配

如果虚拟3×3中：

```text
edge permutation parity != corner permutation parity
```

不能交给普通3×3算法。必须先在5×5层修正对应奇偶，再重新降阶。

正确流程：

```text
构造虚拟3×3
→ 检查棱方向和
→ 检查角方向和
→ 检查棱角置换奇偶
→ 若非法，执行5×5 parity宏
→ 重新检查tredge
→ 再次构造虚拟3×3
```

只有虚拟3×3完全合法，才能进入3×3阶段。

---

# Plan 11：完整边降阶主算法

最终可以按下面的逻辑实现：

```python
def reduce_5x5_edges(state):
    protected = set()

    # 第一阶段：只完成前8条
    while count_valid_tredges(state) < 8:
        target = choose_normal_target(state, protected)
        moves = solve_normal_tredge(state, target, protected)
        apply(state, moves)

        if is_valid_tredge(state, target):
            protected.add(target)

    # 第二阶段：保留4条活动棱
    active = all_edge_slots - protected

    abstract_state = build_terminal_edge_state(state, active)

    macro_plan = solve_terminal_state(
        abstract_state,
        macros=[
            middle_cycle_macros,
            left_wing_cycle_macros,
            right_wing_cycle_macros,
            flip_macros,
        ],
    )

    for macro in macro_plan:
        apply(state, macro.moves)
        assert centers_solved(state)
        assert fixed_centers_unchanged(state)
        assert protected_tredges_intact(state, protected)

    # 第三阶段：处理降阶奇偶
    while not reduced_3x3_is_legal(state):
        parity = classify_reduction_parity(state)
        macro = choose_parity_macro(parity)
        apply(state, macro.moves)

    assert count_valid_tredges(state) == 12
    assert centers_solved(state)

    return state
```

---

# Plan 12：降阶成3×3并完成

当满足：

```text
中心全部归面
12/12 tredge为VALID
虚拟3×3状态合法
```

执行映射：

```text
5×5固定面心 → 3×3中心
5×5角块       → 3×3角块
5×5完整tredge → 3×3棱块
```

然后：

```python
state3 = reduce_to_3x3(state5)
moves3 = solve_3x3(state3)
apply_outer_moves_to_5x5(state5, moves3)
```

3×3阶段的动作只能映射成5×5外层动作：

```text
R、L、U、D、F、B
```

不能再使用宽层，否则会重新拆开已经配好的 tredge。

---

# 推荐的实际实施顺序

## 第一阶段：先找到可用宏

按优先级依次找：

```text
1. 中棱3-cycle宏
2. 左翼3-cycle宏
3. 右翼3-cycle宏
4. tredge翻转宏
5. 降阶parity宏
```

中棱 3-cycle 是第一突破点。

## 第二阶段：只解决一个真实末段状态

选择一个当前卡在 8～10 条的 fixture，实现：

```text
当前状态
→ 释放到4条活动棱
→ 宏级规划
→ 12/12 VALID
```

## 第三阶段：覆盖全部6个 flip fixtures

要求每个都达到：

```text
12/12 VALID
中心恢复
虚拟3×3合法
```

## 第四阶段：接已有3×3解法

最终验证：

```text
原始5×5状态
→ 中心
→ 配棱
→ 末段
→ parity
→ 3×3
→ 完全复原
```

---

# 如果找不到“纯中棱3-cycle”

按以下顺序放宽条件，不要无限增加搜索深度：

## 方案一：允许同时循环一个翼轨道

```text
M 发生3-cycle
LW同时发生已知3-cycle
```

之后用单侧翼宏消除副作用。

## 方案二：允许破坏一个辅助 tredge

宏只需保护前8条，最后4条全部可以被改变。

## 方案三：两段式中心恢复

```text
第一宏修中棱但打乱中心
第二宏恢复中心且保留中棱效果
```

## 方案四：直接搜索最后4条完整解

如果局部宏始终找不到，就不要继续要求单宏漂亮。直接在一个真实最后4条状态上做双向搜索：

```text
正向：从当前缺陷状态搜索
反向：从4条全VALID状态搜索
中间相遇
```

搜索动作仍使用结构化短宏，而不是所有基础转动。

---

# 最终算法路线

你的剩余解法应固定为：

```text
普通配棱做到8条
        ↓
主动保留4条活动tredge
        ↓
中心恢复型切片宏
        ↓
中棱/左翼/右翼3-cycle
        ↓
宏级末段搜索完成最后4条
        ↓
最后两条失败时主动释放第3/4条
        ↓
FLIPPED与降阶奇偶修正
        ↓
12/12 VALID tredge
        ↓
合法虚拟3×3
        ↓
现有3×3算法
        ↓
5×5完全复原
```

最重要的下一步只有一个：

> **先搜索出至少一个“宏结束中心恢复、改变中棱与翼相对归属”的 3-cycle 宏。**

因为“中棱锚定配翼”已经被验证不可达，而 Gate 5c 的正式目标就是允许中途打乱中心、终态恢复中心并改变相对归属。[1] 一旦拿到这个宏，就能把当前最后 2～4 条问题转化为规模很小的宏级排列搜索，而不必继续在整颗 5×5 上盲目试公式。