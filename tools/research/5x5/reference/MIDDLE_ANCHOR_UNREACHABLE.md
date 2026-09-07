# 中棱锚定配翼 —— 不可达诊断

日期 2026-09-08，分支 `wip/deterministic-freeslice`。
配套提交：`提交一`（tredge classifier，含标志性共轭不变量测试）。

## 结论

**当前配翼原语无法实现「以中棱为锚的完整 tredge 构造」。**

在 6 个真实 flip fixture 上，翼对全部配齐后通常只有 `1/12` 槽是完整 tredge；
理论上试图读取目标槽中棱颜色键、把两枚同色翼配到该中棱周围，但在当前
`setup + P + 逆setup` 原语空间内被证明**不可达**。

## 决定性证据：共轭保持「中棱↔翼归属」不变量

系统枚举所有短 `setup + P + 逆setup` 共轭（`P = u R U R' F R' F' R u'`，
setup 为纯外层动作，长度 ≤ 2，`_compress_log` 去重后共 **4338** 个）：

- 对每个共轭，从 solved 态施加 `setup + P + 逆setup`；
- 统计任何「中棱颜色对 ≠ 该槽两翼颜色对」的槽数（即归属被改变）。

结果：**4338 个共轭全部保持中棱↔翼归属，0 个改变**。

对应的回归测试 `tests/test_reference_tredge.py::test_conjugates_preserve_middle_wing_assignment`。

## 机理

一个棱槽（如 UF）的中棱位于贯穿轴坐标 `0`，两翼位于贯穿轴坐标 `±3`。
- **纯外层动作**只按面转动任意一层：同一槽的三块（中棱 + 两翼）共享两个
  `±6` 面坐标，任一面转要么同时移动三者、要么一个都不动 ⇒ 槽单元整体搬运。
- **配翼原语 P** 及 `setup + P + 逆setup` 同理：实证中 P 对每个槽都把
  「中棱 + 两翼」整体搬到同一新槽（`same slot = True`），只做槽单元
  `U 带 8-cycle + 1 个 2-cycle` 的整体置换。

因此任何 `外层 setup + P + 逆setup` 都无法把中棱与它当前槽的翼对**分离**，
也无法把指定颜色的两枚翼送到指定中棱周围。这正是「中棱↔翼归属不变量」。

## 后果与路线

成立「先配全部翼对，再插入中棱」与「以中棱为锚配翼」在**当前原语空间内等价地不可达**。
要改变「中棱↔翼相对归属」，必须引入会**暂时打破槽单元**的动作：

- 单内层**切片**（`M/E/S`）会移动贯穿轴 `0` 的中棱而不动 `±3` 的翼，从而分离中棱与翼对；
- 但切片会**扰动中心**（移动活动中心跨面）。

故转入 **Gate 5c**：允许宏过程中临时破坏中心、但宏**终态恢复中心**且**改变**
中棱↔翼归属的切片宏搜索。搜索目标不是「每步保中心」，而是
`centers_solved(final) and fixed_centers_unchanged(final) and
relative_middle_wing_assignment_changed(initial, final) and protected_tredges_intact(...)`。

## 相关待办

- [x] tredge classifier（`reference/tredge.py`）
- [x] 共轭不变量诊断测试
- [ ] Gate 5c 切片宏搜索（终态恢复中心 + 改变归属）
- [ ] 单个中棱锚定增长验证（依赖切片宏）
- [ ] 6 fixtures 全部 12/12 complete tredges
