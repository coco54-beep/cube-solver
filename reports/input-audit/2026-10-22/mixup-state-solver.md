# Mixup 手动状态求解验收

日期：2026-10-22。范围：Mixup 与 Mixup Plus 的 333、334、344、444，共八款。

## 结果

- 24 / 24 个空历史状态完成求解，并从原始物理状态独立回放至 `is_solved()` 成功。
- 回归检查：185 项通过，4 项跳过。
- 两个回归案例通过真实录入控件，从空白重新输入普通 344、444；其余观测审计通过几何和颜色数据重新匹配物理状态。

| 型号 | 成功 | 步骤范围 | 桌面求解时间范围（秒） |
| --- | --- | --- | --- |
| mixup_333 | 3 / 3 | 308–364 | 0.937–2.046 |
| mixup_334 | 3 / 3 | 541–731 | 1.719–2.516 |
| mixup_344 | 3 / 3 | 813–1,149 | 2.469–17.906 |
| mixup_444 | 3 / 3 | 143–158 | 2.078–4.157 |
| mixup_plus_333 | 3 / 3 | 4,043–6,302 | 12.921–22.391 |
| mixup_plus_334 | 3 / 3 | 9,192–21,331 | 34.031–44.219 |
| mixup_plus_344 | 3 / 3 | 6,622–9,658 | 40.266–54.468 |
| mixup_plus_444 | 3 / 3 | 666–912 | 25.860–32.907 |

## 验证方式

16 个既有观测案例，加 8 个独立生成的合法转动打乱案例。观测文件只提供外形和颜色，不提供打乱历史、片体朝向记录、来源编号或记忆的组合。审计工具重建模型并确认历史为空，调用生产求解入口，再独立回放全部动作检查实际还原结果。

求解过程先恢复外形和组合、按颜色配对，再交给既有三阶或四阶求解器；最后修正需要保留的中心分割线方向。通用预计算操作表不包含上述具体案例。

原始结果：[mixup-acceptance.json](mixup-acceptance.json)。新观测：[fresh-manual-inputs](fresh-manual-inputs/)。既有观测位于 `../2026-10-21/mixup-manual-inputs/`。

复现审计：

```powershell
python tools/audit_mixup_solver.py --also-fresh --output reports/input-audit/2026-10-22/mixup-acceptance.json
```

回归命令：

```powershell
python -m pytest tests/test_mixup_reduction.py tests/test_mixup_manual_random_input.py tests/test_mixup_slots.py tests/test_mixup_entry_edits.py tests/test_mixup_inner_entry.py tests/test_mixup_shared_choices.py tests/test_mixup_input_screen.py -q
```

## 限制与后续工作

- 每款仅验证 3 个案例；打乱来自合法转动，不是均匀随机状态。本结果不能证明任意合法手动状态均可求解。
- 搜索保留时间、节点和步骤限额，困难状态仍可能未完成。
- Plus 334 / 344 部分解法仍有数千至上万步；本次最长为 21,331 步，尚需缩短到更适合实际操作的长度。
- 观测重建通过不代表所有输入菜单组合均已覆盖；本轮未重新设计 Plus 输入菜单。
- 仅在桌面验证，未重新构建 APK，未测手机性能。
- Fused、Bandaged、Tangram、Pentacle、Circle、Crazy 等其他型号的求解缺口未在本轮补齐。
