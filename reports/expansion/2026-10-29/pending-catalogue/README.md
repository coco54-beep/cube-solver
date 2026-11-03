# 未接入型号：目录参考卡片

用户要求把尚未接入的型号也放进App。本轮收录7款可查看参考图的卡片，沿用现有分类；没有增加第二个特殊分类，也没有把未核对的研究机构当作实物型号开放。

| 现有分类 | 新增可见卡片 |
| --- | --- |
| 转棱系列 | 向阳花、仙女座、蝶恋花、十二轴双棱花 |
| 金字塔系列 | 三叶草金字塔 |
| 十二面体系列 | VeryPuzzle Clover Dodecahedron |
| 足球系列 | Kairis 星寻足球 |

所有卡片和首页搜索均显示“待接入”。点击打开参考图和功能状态；没有录入、拧动、拍照或求解按钮。关闭参考图回到原分类的滚动位置，当前输入不变。重复点击不会叠加参考图窗口。三叶草金字塔的已知外壳不符研究原型仍只供开发核对，不从正式卡片进入。

`candidate_puzzles.PENDING` 与可操作型号 `REQUESTED` 分开登记。公共分类同时包含两者，`IMPLEMENTED_ORDERS`、拍照入口和课程清单不把待接入卡片计作可操作型号。参考图复制到 `assets/puzzles/pending/`，使用现有Windows和Android资源规则，来源见 [references.json](references.json)。原图不修改，不依赖外部网络。

- [手机比例分类卡片](edge-picker-390.png)
- [手机比例参考图页面](reference-390.png)
- [桌面分类卡片](edge-picker-800.png)
- [页面检查结果](ui-results.json)

33项目录、分类、搜索、多语言、入口隔离、拍照过滤和资源选择检查通过，见 `reports/pending-catalogue-tests.xml`。原生页面检查覆盖7款×800×600及390×844共14组，实际滚动到可见卡片、打开参考图、返回、输入搜索并点击结果，均保持当前魔方输入。未打包，未进行安卓真机验收。

用户指出重复后已纠正：原白色MF8 2号照片属于太阳二号，误标成Gemini的待接入卡片已移除。太阳二号的已有入口、模型及存档保持原样，待接入从8款改为7款；没有把真实的LanLan Gemini与MF8 Sun Cube II当作通用别名。原照片归档于 `artifacts/expansion-references/sun2/confirmed-stickerless.jpg`。
