# 1.2.22

## 下载

- Windows x64：`CubeSolver-1.2.22-windows-x64.zip`，完整解压后运行 `CubeSolver/CubeSolver.exe`，无需安装 Python。
- Android arm64-v8a：发布资产中的 APK；本次按用户要求不执行 ADB 安装与手机测试。
- Windows ZIP 随附校验值和构建清单，保留 `_internal` 文件夹。

## 求解与演示

- 普通 N 阶范围为 6–17；目录、模型和审计使用相同上限。
- 普通高阶中心比较三种规划和完整原解，共享准备动作表，减少重复生成。
- 粽子、镜面 4–9 阶按真实块身份比较更短的中心准备动作。
- 普通五阶比较降阶与轨道解；三阶形变类联合比较主体和可见中心的总步数。
- 足球改用带成本的成对翻棱，完整回放后与原方法比较。
- 高阶五魔方压缩搜索状态、批量评分，并加载已核对的 4–13 阶轨道数据。
- 战鼓、转面八面体、高阶斜转、金字塔、魔塔、繁花、格子、四叶草和八叶花增加完整动作等价改写及重复状态压缩。
- SQ1 比较两个阶段的总长；镜面魔塔比较多个最短主体路径后的中心修正成本。
- 二十面体离线缩短 11 条核心关系并核对其作用，保留不变的方向约束。

这是构造解和限时改进，不保证最短解。完整打乱的高阶五魔方、足球仍可能输出数千步；个别尝试没有省步时保留原解。数据见 `reports/algorithm-upgrades/2026-10-13`。

APK 构建和桌面回放检查分别记录，真机安装与测试需以 ADB 手机连接后的记录为准。

## 检查结果

90 个类型／阶数组合的全轴全层打乱完整回放通过；普通 N 阶 6–17 阶另做同输入、同核心解的逐阶比较。299 项专项求解与演示检查通过。没有省步的候选保留原解；高阶仍可能有较长步骤。

详见 [优化报告](../reports/algorithm-upgrades/2026-10-13/report.md)。

## English

Windows x64 portable release: extract the complete ZIP and run `CubeSolver/CubeSolver.exe`; Python is bundled. This release improves higher-order and irregular solving, preserves standard N orders 6–17, and keeps the complete demonstrations through order five. Complete replay passed for 90 type/order configurations; 299 targeted solver and demo checks passed. Results are heuristic and input-dependent. ADB/device testing was cancelled at the user's request.

## 日本語

Windows x64 便携版は ZIP 全体を展開し、`CubeSolver/CubeSolver.exe` を起動します。Python は同梱されています。通常の N 次は 6〜17 段を維持し、高次・変形パズルの求解と 5 段以下の完全な復元デモを提供します。90 種類／段数の完全再生と 299 件の解法・デモ検査に合格しました。手数は入力と時間制限に依存します。ユーザーの希望により ADB／実機テストは行いません。
