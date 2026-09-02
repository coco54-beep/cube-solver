# 实验记录：保中心双配宏（double-pair macro）—— 结论：不采纳

日期：2026-09-03
状态：**失败（未达验收标准），实现已从主线干净回退**。本目录用于后续
“非单调真双配宏”研究复用：含失败结论、设计要点、消融数据。

## 一句话结论

把**两个连续单交换宏组合成“双配宏”**，在数学上就**不可能**胜过现有单配
Beam：压缩是结合的，`compress(compress(a)+b) == compress(a+b)`，单配 beam
两层级已到达并压缩同一状态。实测三组打乱 0 步收益、耗时 +65%～75%，
另有单例劣化且无兜底，违反“逐例不劣化”。真正有潜力的“一次配两根”需要
**非单调宏**（过程中临时拆配对、靠内部抵消净配 ≥2），需离线搜索，超出
“两单组合”范围，故未实现。

## 目标

- 在不破坏正确性/确定性/向后兼容前提下降低配棱平均与长尾步数（当时配棱
  阶段约 57.1/109.6 步）。
- 一次动作：保中心 ∧ 已配对且受保护组不被拆散（允许整组移动）∧ matched 净增 ≥2，
  且必须真实状态模拟验证。

## 实现要点（已被回退；可从 tag `exp/double-pair-macro` 恢复）

改动文件：`solver/reduction/edge_pairing.py`、`solver/solver4.py`、
测试 `tests/test_double_pairing.py`（主线已删除）。

- 助手：`_center_sig`（中心签名）、`_matched_color_sets` / `_protected_intact`
  （受保护组、整组可移动）、`_single_seq`。
- `_double_pair_actions(cube, log, singles, limit)`：取前 N 个单交换 → 克隆模拟
  中间态 → 前 M 个再交换 → `_compress_log(seq1+seq2)` → 原状态模拟校验
  （中心一致 / 受保护完整 / matched 净增≥2）→ 翼排列去重 → 净长截断。
- `_pair_beam_finish(...)`：扩展动作集 = 单配 +（剩余未配对 3~6 时）双配；
  每节点单配上限 `_SINGLE_CAP`、双配生成预算 `_DOUBLE_GEN_BUDGET`；
  去重键 = 翼排列 + matched + 日志尾；`pairing_stats()` 调试统计。
- 开关：`pair_edges(..., tail_double=False)`、`solver4._PAIR_DOUBLE_ENABLED=False`。
  默认关闭，历史行为逐字节不变；164 测试全绿（157 原 + 7 新）。

## 消融 A/B（同一打乱逐例，求解含中心择优+尾段beam+3x3 最小化）

数据文件在 `data/`（每例总步数 JSON；`*_on.json` 为启用双配）。

| 基准 | A（关）mean / edge mean / time mean | B（开）mean / edge / time | 逐例差 |
|---|---|---|---|
| seed-42 20×30 宽层 | 95.3 / 57.1 / 2.7s | 95.3 / 57.1 / 4.7s | 0 |
| 固定 160（含 12–25 步） | 154.9 / 109.6 / 4.0s | 154.9 / 109.6 / 6.6s | 11（7 差 +1~2、4 好 −1~−10）|

双配命中（固定 160 启用时）：生成 15696、合法并全被展开 20030、生成预算耗尽
148 次、beam 节点 52544（vs 32842）——开销显著却均值/P90/P95/max 分毫不差。

验收判定：
- 正确性测试全过 ✓（但那是“没坏”，不是“变好”）
- 禁时与旧版一致 ✓
- 平均步数降 1~2 或 P95 明显降：**✗（0 变化）**
- 耗时增加 ≤30%：**✗（+65%～75%）**
- 逐例不劣化（双配劣则回退原 beam）：**✗（未实现兜底，7 例劣化）**

## 根因分析（供“真双配”参考）

1. 双配 = 两个“每步净 +1 matched、保中心”的单交换，其内部抵消已在两层级
   单配 beam 中被压缩捕获 → 无新增可达状态、无更短表示。
2. 要真“一次净配 ≥2”，宏必须在**中间过程临时拆开/重排**某些配对、最终靠序列
   内部抵消回到保护集合，并整体优于任意两条单调单交换。这类宏当前生成器
   （两单调单交换拼接）覆盖不到。

## 后续方向（未做）

- 离线用 双向 BFS / IDA* / meet-in-the-middle 搜索“非单调双配宏”：
  输入若干未配对翼位相对布局，输出保中心、既有配对仅整组移动或临时拆复、
  净增 ≥2 的序列；按触发模式建成动作库，运行时优先匹配。
- 实现后仍需：逐例不劣化兜底（双配结果劣于原 beam 时保留原 beam）、
  确定性校验、以及上文同款 A/B 消融与统计。

## 如何恢复实现

```bash
git tag                # 见 exp/double-pair-macro
git show exp/double-pair-macro:solver/reduction/edge_pairing.py > solver/reduction/edge_pairing.py
git show exp/double-pair-macro:solver/solver4.py        > solver/solver4.py
git show exp/double-pair-macro:tests/test_double_pairing.py > tests/test_double_pairing.py
# 恢复后再按“后续方向”改造生成器，勿直接启用旧实现。
```
