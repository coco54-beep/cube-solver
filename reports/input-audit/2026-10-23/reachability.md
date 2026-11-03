# 录入可还原性校验检查

2026-10-23，Windows 桌面：**120 项检查通过**。

## 确认的旧版漏检

用 Git 当前提交中的原校验函数，与本次函数处理相同输入；以下输入保持颜色数量，旧版均接受，新版均拒绝：

| 型号 | 输入问题 | 新版结论 |
| --- | --- | --- |
| 二阶 | 单独扭转一个角块 | 角扭转总和不正确 |
| 三阶 | U/D 贴纸仍朝上，但交换同角另外两张贴纸 | 镜像角块 |
| 四阶 | 单独翻转一个翼棱 | 翼棱身份／方向不正确 |
| 五阶 | 单独翻转一个中棱 | 中棱翻转总和不正确 |

对照数据见 [reachability-acceptance.json](reachability-acceptance.json)。

## 回归范围

- 核心检查 **84 项通过，1.11 秒**：单角扭转、镜像角、重复角、翼棱翻转、中棱翻转、中心跨轨道错位、合法面转／宽层／整体转动，以及二阶求解回归。
- 录入回归 **36 项通过，1.26 秒**：二至十七阶面色输入、各绑块型号三个打乱案例的无历史重建，以及普通输入与绑块输入的不同校验提示。
- 四、六、八阶的合法翼棱奇置换通过检查，避免错挡偶数阶正常特殊情况。
- 检查不修改传入的面色数据。

原始结果：[核心检查](reachability-core-tests.xml)、[录入检查](reachability-entry-tests.xml)。

```powershell
python -m pytest tests/test_input_reachability.py tests/test_validation_3x3.py tests/test_validation_4x4.py tests/test_validation_5x5.py tests/test_solver_2x2.py -q --tb=short
python -m pytest tests/test_manual_entry_roundtrip.py tests/test_bandaged_entry.py -k "standard_cube_face_input or manual_colours_and_seams or check_distinguishes" -q --tb=short
```

## 尚未证明的部分

本次补的是确定可检查的标准魔方约束及提示，没有证明任意绑块、Mixup 或其他复杂异形录入都可达。它们即使通过形状／配色匹配，仍需对应算法找到合法路径并在原状态上回放。有限搜索达到上限仍不得等同于“无解”。没有手机实测或更新安装包。
