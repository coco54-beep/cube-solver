# Mixup 手动状态求解

## 本次接入

`solver/mixup.py` 对八种 Mixup / Mixup Plus 提供不依赖打乱历史的降阶求解：

1. 按真实片体的几何位置恢复立方体形状。四阶 Plus 的剩余内棱朝向使用合法翻转组合与双向几何搜索。
2. 将整块、两半、四小块等组合归回对应布局。Plus 334 / 344 在执行被整条内棱阻挡的半层转动前，先调整内棱组合。
3. 在布局边界上按实际颜色配对。预计算群表只包含通用合法操作，不包含具体输入或打乱记录。相同颜色的小块编号仅用于引导搜索，不能替代实际颜色、几何检查。
4. 333 / 334 / 344 交给三阶；444 交给四阶。交接前检查完整表面、分割格边界、每格颜色；三阶额外要求中心配色符合真实空间朝向。
5. 使用普通三阶恒等组合恢复长方形中心的分割线方向。
6. 从原始输入独立回放全部动作，只有真实模型 `is_solved()` 成功才返回解法。

有正确打乱记录的状态保留原有快速入口。手动录入的空历史状态会走上述独立路径。

## 同时转动多层

`cube.mixup.MixupSliceMove` 表示相邻层同时转动，只检查联合层两侧的切面。中间跨层片体可以随联合层一起移动；单层操作仍保留自己的阻挡检查。动作已接入播放动画、文本标记和状态保存。

## 预计算资源

- `solver/data/mixup*_group.bin`：七份压缩操作表，普通 444 的标准降阶不需要额外群表。
- `assets/mixup_center_finish.json`：保持普通三阶块位、修正中心分割线的组合。
- 表中记录版本及按 8 位小数规范化的几何指纹。几何模型不匹配时拒绝加载。
- 应用运行时仅使用标准库和既有依赖；SymPy 只用于开发机器离线建表。
- `artifacts/` 为开发中间结果，已从 Android 包资源排除。

重新建表示例：

```powershell
python tools/build_mixup_solver.py mixup_plus_444 --install
python tools/build_mixup_center_finish.py
```

## 验证方法与范围

审计工具先读取仅含外形、颜色的 JSON 观测，重新匹配为完整物理模型，断言历史为空，再调用生产求解入口并独立回放。另有两例使用真实录入控件从空白组合和颜色重新输入。

```powershell
python tools/audit_mixup_solver.py --also-fresh --output reports/input-audit/2026-10-22/mixup-acceptance.json
python tools/audit_mixup_solver.py --input-directory reports/input-audit/2026-10-22/fresh-manual-inputs
python -m pytest tests/test_mixup_reduction.py tests/test_mixup_manual_random_input.py
```

2026-10-22 验收：24 / 24 个空历史观测状态求解并独立回放成功；相关回归 185 项通过、4 项跳过。逐型号步骤、时间和范围见[验收报告](../reports/input-audit/2026-10-22/mixup-state-solver.md)。

## 当前限制

- 尚未证明覆盖全部合法状态。形状搜索、组合搜索、颜色搜索均保留时间或节点限额；用户取消会终止计算。
- 部分 Plus 334 / 344 的返回步骤较多，尚未达到实用短解水平。
- 随机案例来自合法转动打乱，不是均匀随机状态抽样。
- 观测审计不等同于所有组合菜单均能通过点击录入这些形状。本轮处理求解算法，未重做 Plus 输入菜单覆盖。
- 本轮没有重新生成 APK，也没有验证 Android 真机运行时间。
- 用户列出的其他型号求解缺口没有在本轮统一补齐。
