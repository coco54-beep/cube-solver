# 用户照片新增批次（2026-10-26）

> 2026-10-28 四阶菱边补图纠正：旧截面偏移导致额外窄条和小三角；已改为十二彩色面各 4 片、六金面各 4 片，共 72 色面，仍为 56 个机构块。相关 40 项回归和两种原生界面尺寸通过。详见 `../../2026-10-28/rhombic-mask-correction/README.md`。下文较早的批次统计不代表后续全部进度。

本批范围共 16 款：MF8 双子星、随后八张照片、最后七张照片。2026-10-27 根据补图接通 VeryPuzzle #59 五魔球后，9 款已有接入；本轮曾误把新平面模型对为 Crazy Comet，用户补图否定后已单独保留研究款；实际蓝蓝款仍未接通，另 7 款请求未完成。没有打包。

## 已接通的型号

| 用户照片 | 菜单名称 / 标识 | 机构与录入 | 核对结果 |
| --- | --- | --- | --- |
| 八张图第 2 张 | 五魔球 D5 / `megaminx_ball` | 十二轴 72°；球面逐面填色 | 当前已按用户修成二十色三角区域、62 块、140 色面；旧 132 面版本作废，见 2026-10-27 五魔球记录 |
| 八张图第 4 张 | 四轴斜转十二菱面 / `skewb_rhombic` | 四轴 120°；逐面填色 | 14 块、48 贴片：八个三色块、六个四色块 |
| 八张图第 5 张 | 十二轴十二菱面 · Rua / `rua` | 十二轴 180°；逐面填色 | 38 块、72 贴片：8 三色角、6 四色角、24 单面块 |
| 八张图第 6 张 | 菱面三阶 / `rhombic_3` | 三阶立方核心；形状、颜色及方向卡片 | 26 机构块、十二菱面各 5 个贴片 |
| 八张图第 7 张 | 四阶十二菱面 / `rhombic_4` | 四阶核心；同类卡片按可见外观合并 | 56 机构块、十二菱面各 8 个贴片 |
| 八张图第 8 张 | 四阶八面魔球 / `caneball_4` | 四阶核心，按八个空间分区配色；选块录入 | 56 块，每块一个外观颜色；八色各七块。与 Trajber 分开 |
| 七张图第 1 张 | 八轴八面绣球 / `jewel_fto` | FTO 八轴 120°；逐面填色 | 42 块、54 贴片；48 彩色三角及 6 个整块金色方形 |
| 七张图第 4 张 | 四阶菱边 / `rhombic_mask_4` | 截角菱面四阶核心；选块录入 | 56 块；十二原色加共同金色截面，不把每个金色面另设颜色 |
| 七张图第 5 张 | 十二轴十四面体 / `helicopter_14` | 十二棱轴 180°；逐面填色 | 32 块、32 贴片；六面各四片加八个整块金色三角 |

分类沿用斜转、十二面体、八面体和棱转系列，没有新建“特殊魔方”分类。沿用六个动作按钮、选色连续上色、选块旋转、撤销、配色设置、失败保留输入及回放页。灰模与已填色缝线使用现有渲染样式。

菱面体按真实实体裁切，内部封闭；不是在普通立方体上画线。外形比例为照片估计，未取得生产图纸。八面魔球保留 26 个外观平面，不把它当成八色 Trajber。八面绣球的金色方形和十四面体的金色三角没有独立转轴。

教学为本项目原创的机构、阶段和配套起始状态练习。斜转/棱转型号增加了独立构造并回放验证的相邻轴交换子；没有把它冒称为只动三块的公式，也不声称它是任意状态的最短解。完整实例使用实际模型生成及验证。

## 已发现并修正

- 新外壳的拧动、教学和还原回放均使用同一外壳渲染器，避免录入菱面体却播放普通立方体。
- 八面魔球单色三角角块有三种不可见方向。现在只在外观完全一致的候选中匹配合法虚拟朝向；不会因用户选了另一种相同外观而误报无解。看得见的非法角扭转仍被拒绝，原输入保留。
- 角朝向错误归类为“状态不合法”，不归类为程序异常。
- 形状录入页隐藏常驻参考说明行，保留教程内容和真实错误提示。
- 逐面录入从错误恢复到检查通过时，恢复普通状态文字颜色。

## 验证

- `tests/test_lanlan_photo_models.py`：封闭实体、机构块数、每色贴片数、实际转轴、一整圈恢复、序列化、渲染器路由。
- 八款分别从 30 步和 100 步合法打乱观察到的色面重建输入，再调用生产求解服务。未提供打乱历史。解法在输入副本上完整回放，输入本身保持。
- 单色角三种外观相同的方向分别求解；可见非法角朝向不能被自动抹掉。
- `tools/build_expanded_groups.py` 生成四款斜转/棱转的短词群表，每条表内置换逐一用真实动作验证。表合计约 25 KB；不需要运行时生成巨大的原始群分解。
- `tools/audit_lanlan_models.py`：实际 Kivy 页面在 800×600 与 390×844 两种尺寸走分类、空白录入、错误保留、连续上色或选块旋转、拧动、撤销、求解及跳到完成态。结果和截图见 `visible/results.json`。
- 回归记录：`reports/lanlan-models.xml`。这些尺寸测试来自 Windows 图形环境，不能代替安卓真机测试。

## 尚未完成（不能当作已经新增）

| 用户照片 | 名称 / 识别进度 | 尚缺的工作 |
| --- | --- | --- |
| 单独双子星图 | MF8 Twins Skewby Copter | 仅完成未上架的常规转动几何研究；半斜转、半棱转后的混转阻挡、变形录入及专用还原没有完成 |
| 八张图第 1 张 | Kairis 星寻足球魔方（二十轴深切） | 用户补图已确认身份；深切变形、实体阻挡、录入和求解仍需完成，不能按普通足球魔方套用 |
| 八张图第 3 张 | MF8 Sun Cube 2（太阳二号） | 45°面转与左/右射线、隐藏载体和解锁条件尚未建模，不能套用 Mixup 中层 45° |
| 七张图第 2 张 | LanLan Curvy Hexagram Pyraminx / 六角星金字塔 | 与 4-Corners 机构相关；曲线双轴、混转及角部需单独建模 |
| 七张图第 3 张 | LanLan Crazy Comet / 十二轴十二面体 | 用户补充细节图后否定本轮模型对应；研究款独立保留，实际蓝蓝款仍未接通。详见 `../../2026-10-27/crazy-comet/README.md` |
| 七张图第 6 张 | LanLan Clover Pyraminx / 三叶草金字塔 | 实物每条边有两条轴，共十二条；不能拿现有六棱轴半转花瓣四面体替代 |
| 七张图第 7 张 | LanLan 4-Corners Plus / Gemini | 经后续商品照片逐处切线核对，改正先前 Master Clover 的误名；偏轴、附加切面、混转阻挡和变形录入仍需完成 |

## 机制与名称查证（仅研究记录，不植入产品教程）

- [LanLan 4-Corners Plus / Gemini](https://www.ziicube.com/LL-4-Corners-Plus)：七张图第 7 张的对应原型；与后续新增的 Master Clover 是两款不同魔方。

- [LanLan Skewb Dodecahedron](https://www.thecubicle.com/products/lanlan-skewb-dodecahedron)：产品图与八张图第 4 张的四分菱面一致。
- [LanLan Rhombic Dodecahedron](https://www.thecubicle.com/products/lanlan-rhombic-dodecahedron)：四阶菱面体的照片与命名。
- [LanLan Cane Ball](https://www.thecubicle.com/products/lanlan-cane-ball)：四阶机构，按八个空间区配八色。
- [LanLan Jewel](https://www.thecubicle.com/products/lanlan-jewel-cube)：FTO 截角改整块金色方片。并非十二轴斜转模型。
- [LanLan Rua](https://www.atoutcubes.com/fr/dodecaedre/66720-lanlan-rhombic-dodecahedron-12-axes-4000000005742.html)：照片与十二轴菱面模型。
- [LanLan Mask](https://cubein.cn/products/lanlan-super-4x4-mask-cube)：四阶截角菱面变体；店铺宣传的“变形”描述未作为证明，几何由实际裁切独立核对。
- [LanLan Crazy Comet](https://www.thecubicle.com/products/lanlan-crazy-comet)：官方 Oskar 标志版的外观和两类转面说明。
- [LanLan Clover Pyraminx](https://store.tribox.com/products/detail.php?product_id=3098)：明确每条边两根轴。
- [Exploding Twins 结构研究](https://www.schwandtner.info/publications/Exploding%20Twins%20Cube.pdf)：每条棱六片，以及先复形再降阶的机构事实；原文教程没有复制进软件。
