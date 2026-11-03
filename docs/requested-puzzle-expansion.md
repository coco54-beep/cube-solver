# 本批异形魔方接入记录（2026-10-23）

后续照片批次：2026-10-26 的十款花式魔方请求与状态见
`docs/flower-photo-requests.json` 及 `reports/expansion/2026-10-26/flower-batch/README.md`。
后续实际进度以 `reports/expansion/2026-10-27/pending-completion/README.md` 为准；有限范围与未接通的研究记录均不得当作整款完成。

用户原清单列出 34 个名称，其中 Trajber’s Octahedron 与 Trajber 4×4 按用户确认
是同一款四阶魔方，按用户要求移除与既有“足球三阶”重复的 Tuttminx 入口后，本批共 32 款，名单保存在 `candidate_puzzles.py`。型号尚未
确定或功能尚未接入的款式不显示为可操作魔方。下列 32 个型号现已按系列
并入目录。Trajber 只有四阶入口；已移除误加的三阶版本。
这份记录区分代码接入与实际验收，不代表所有款式已完成实物核对。

## 当前接入

2026-10-24 目录整理：撤掉“更多异形系列”入口，每款仅归入一个系列，
首页只保留一个“其他异形”收纳尚无对应系列的独立型号。

| 目录系列 | 本批归入型号 |
|---|---|
| 字母形扩展 | I、L、T、X、Tri、Temple、Cross |
| 绑块与连体 | Siamese A、B |
| 八面体 | Trajber 四阶、Pyraminx Diamond |
| 十二面体 | Crystal、Starminx I、Pentultimate、Master Pentultimate、2×2／3×3 Dodecahedron、Rediminx、Master Brilic |
| 二十面体 | Dogic I、20 色 Dogic |
| 斜转 | Container |
| 圆柱与球体 | Rubik Cheese、3-Layer Cheese、Masterball |
| 五边形柱体 | Domino、Prism、4-Layer、Professor |
| 镜面 | Blanker、Mirror Kilominx、Mirror Megaminx |

原有普通五魔、FTO、绑块、镜面等型号仍在对应系列中；同一分类选择框
同时列出原有型号与新增型号。旧会话从“更多异形”返回时，按当前型号
转到新的所属系列。

| 型号 | 模型与录入 | 求解 |
|---|---|---|
| Siamese A／B | 按用户两张截图分别共享 1×1×3／2×1×3 块；两个固定转轴中心；过滤触及连接块的层 | 从贴片状态匹配实际可转动层生成的有限群 |
| Trajber’s Octahedron（即 Trajber 4×4） | 四阶机构、56 块、八面体刚性外壳；有穿过核心的中间切面；内层与外层均可转动并变形；选块与方向录入，八色独立设置 | 四阶机构还原与形状等价块匹配 |
| 2×2／3×3 Dodecahedron | 普通二／三阶机构承载十二面体外壳；十二色形状卡片录入 | 普通机构还原、三阶中心方向修正 |
| Pyraminx Diamond | 六个四色尖块与八个独立中央三角形；尖块与相邻四个中央面一起转 90° | 专用实际置换群；与 Skewb Diamond 分开 |
| Pyraminx Crystal | 十二面体面转；切深 1/√5；50 块、120 贴片 | 实际层置换的有限群 |
| Starminx I | 20 个顶点轴、120°；20 角、30 棱及 12 个固定中心 | 实际层置换的有限群 |
| Pentultimate | 穿过中心的深切面转 | 实际层置换的有限群 |
| Master Pentultimate | 双侧深切面转，独立于普通五魔模型 | 实际层置换的有限群 |
| Dogic I／20 色 Dogic | 两版共用 80 个物理块、切割和转层；12 色版中央三色区属于一个块，边界不画成切缝；20 色版每个完整三角面一种颜色；顶角和五面深层各转 72° | 独立目标配色、实际层置换群 |
| Rubik Cheese（用户截图款） | 两层，每层六瓣，共 12 块、24 张贴片；顶底各同色、侧面分色；每层 60°、半盘 180° | 12! 阶实际贴片置换群；重新生成短公式表 |
| 3-Layer Cheese（用户截图款） | 三层，每层六瓣，共 18 块、30 张贴片；同一单色方案与真实曲面；没有彩虹或额外半贴片 | 实际层置换群，独立短公式表 |
| Pentagonal Domino／Prism／4-Layer | 2／3／4 个水平层；五个侧轴 180°，顶底 72°；浅切五边形棱柱 | 实际层置换群与短公式表 |
| Professor Pentagonal | 5 个水平层、两个侧向切深；每个矩形面 5×5 格，顶底各 31 张贴片 | 实际层置换群；预计算保留完整稳定子群 |
| Container | Skewb 机构承载旋转 45°、长宽比 √2 的长方体外壳；14 个真实块，形状颜色方向卡片输入 | 复用同机构的普通 Skewb 与中心方向修正表；最终按 Container 外壳回放核对 |
| Masterball | 八经线四纬层；纬层转 45°、半球翻转 180°；曲面渲染 | 两个 16 块轨道的完整置换群 |

Tuttminx 与已有足球三阶为同一型号，按用户要求去掉重复入口；已有足球入口保留。

八面体／十二面体变形均按真实刚体外壳随内部块移动，录入沿用形状卡片、方向、
逐面观察动画。配色页已支持八色／十二色编号面片，避免显示空白六面展开图。
上述新状态可沿用会话保存；Siamese 转动动画围绕各自核心转动。

### 数据与搜索

`tools/build_expanded_groups.py` 离线构建短公式稳定子表，并逐条检查公式在完整
贴片集合上的实际作用。运行时核对几何指纹、颜色数量，从当前录入状态做颜色
约束匹配。没有使用打乱历史。缺少预计算文件时可在后台构建同一有限群，可取消；
大群的首次构建与搜索可能很慢，不能据此承诺手机性能或任意输入的秒级还原。

先前 16 个新贴片录入型号已具备几何指纹匹配的预计算表。Rediminx 共用 Starminx I 的同机构数据；Master Brilic 改用核心还原加独立三循环，避免生成庞大的完整稳定子表。
新表使用 `*_expanded_group.bin`，与先前排除的六张旧表不同；Android／Windows
现有规则会携带这些新表。没有恢复任何旧的大型距离表。

### 当前核对范围

`reports/solver-audit/2026-10-23/expanded-round-manual-probe.json` 记录四个桌面案例：
旧单层 Cheese、Pyraminx Diamond、Masterball、Siamese A 各打乱 30 步后，只用贴片颜色重建，
历史为空，再求解并回放。短公式表生成后的这四个案例分别为 6／29／142／187 步。
其中旧单层 Cheese 案例已不适用于本次用户指定型号。
`layered-cheese-manual-probe.json` 记录改正后的两层／三层 Cheese：分别打乱 30 步，
仅用颜色重建、没有打乱历史，求解分别为 42／41 步，回放均已还原。
`pentagonal-manual-probe.json` 记录四款五边形棱柱同样的 30 步／种子 223 案例：
Domino／Prism／4-Layer／Professor 分别得到 58／76／158／694 步，均回放还原。
`container-manual-probe.json` 用刚体块和方向重建 Container，35 步回放还原。
这些是程序重建录入状态，不是操作手机界面逐格输入；单个种子不代表随机状态覆盖。

**未完成整批实物录入、手机 UI、Android 包和长时间性能验收。** Trajber 四阶的
切割比例及十二面体外壳方向仍应与用户指定产品照片进一步核对。

## 本轮补入的 12 款

| 型号 | 模型与录入 | 求解 |
|---|---|---|
| I／L／T／X／Tri／Temple／Cross | 三阶核心分别在 1／2／3／4／3／5／6 个指定方向扩展一层；扩展中心与核心中心相连，外围八块独立；六视图记录可见颜色、深度和块边界 | 先恢复符合角扭转、棱翻转及奇偶约束的核心，再按完整扩展置换群还原；最终在原录入状态合法回放 |
| Rediminx | 顶点 120°，62 块、132 面片；弯曲的公共接缝共享网格；逐面连续填色 | 与 Starminx I 同一个 Dino 十二面体转动机构，共用表，避免复制资产 |
| Master Brilic | Crystal 深层加浅层，共 230 块、360 面片；每层 72°；十二色逐面输入 | 先恢复普通五魔核心，再用三组独立三循环还原额外 60 块轨道；完整回放核验 |
| Blanker | 八个不等宽二阶角块，白色外壳的 3×3 细线只作装饰；选形状、方向录入 | 匹配等形块与不可见角方向，再还原二阶机构；最终核对外壳形状 |
| Mirror Kilominx／Megaminx | 20／62 个刚性块，不等高的偏移外壳，独立形状卡片和朝向；卡片每页八项 | 按实际块位、方向还原五魔机构，必要时处理剩余外壳方向；不从银色贴片猜状态 |

字母形的三阶核心有些面被外层盖住。录入不要求辨认不可见的块编号，内部通过
动态匹配同时满足三阶规则和扩展块的相对奇偶性。七款扩展表均核验到
`(4k)!² / 2` 的完整自由扩展群（k 为扩展面数），表中公式逐条检查其真实作用。

本轮 `letter-manual-probe.json`：七款各打乱 30 步，重建帧和颜色、历史为空，均回放还原。
`letter-six-view-probe.json`：I／L／Tri／Cross 从六视图重建，再从无历史状态求解，均通过。
`new-shapes-manual-probe.json`：Rediminx、Blanker、两款镜面五魔同样打乱 30 步后重建并回放通过。
`master-brilic-manual-probe.json`：40 步打乱，仅用颜色重建、无历史，2934 步合法回放还原，桌面约 1.1 秒。
这些是指定随机案例，不代表所有状态或手机性能均已验收。

`new-entry-ui-probe.json` 记录新增 12 款在桌面 800×600 实际目录路由与录入页创建，
截图保存在同目录；全部入口与序列化可用。另核对 Cross、Blanker、Mirror Megaminx 的 400×850 竖屏页面与帮助入口，记录为 `new-portrait-ui-probe.json`。尚未完成真机触控及 Android 包验收。

### 外形参考的适用范围

- Tri-Cube 按 Calvin 的 Trio-Cube 扩展系列处理。不同厂家的同名型号应另行核对。
- Rediminx 的曲线是独立绘制的近似外观，保持 Dino 机构与块数，不是厂商原始曲面 CAD。
- Master Brilic 浅切比例为独立几何参数 0.8，深切为 1/√5；360 面片与机构一致，外壳比例尚非实物尺寸测量。
- 两款镜面五魔使用统一偏移外壳；二阶内部用角块分区补齐外表，未复刻某厂内部零件。

## 结构参考

- [Cubing.js 几何定义](https://github.com/cubing/cubing.js/blob/main/src/cubing/puzzle-geometry/pgPuzzles.ts)：深切十二面体与 Trajber 的数学切割参考；本项目独立生成网格与层置换。
- [Oskar：Pyraminx Diamond 与 Duo](https://oskarvandeventer.nl/meffert.html)：Diamond 是只保留角与中心的魔方机构变形。
- [Jaap：Dogic](https://www.jaapsch.net/puzzles/dogic.htm)：顶角与五个完整面的两类转动；12 色中央三色块。
- Cheese 两款按用户 2026-10-23 提供的截图确认，分别是两层／三层同色面圆柱，优先于之前查到的原版单层和彩虹版资料。
- [Jaap：Masterball](https://www.jaapsch.net/puzzles/master.htm)：八经线四纬层与半球翻转。
- [Twisty Prisms 术语](https://staff.fim.uni-passau.de/~kreuzer/TP/TwistyPrisms.html)：Pentagonal Prism 与 Pentastar Prism 的区别。

Starminx I 的名称在博物馆旧记录与部分商店间存在编号混用；目前选择常见的
角转 Dinominx 版本。若用户所指是面转深切版本，应独立提供型号，不能沿用此模型。

## 本轮几何校正

Professor 按用户打乱图采用 5×5 侧面，不能只把普通 Prism 拉高。所有新预计算
的生成公式均逐条在完整贴片集合回放。短公式裁剪另加完整群阶检查，避免仅凭
轨道／奇偶性相同就错误丢弃必需生成元。

`tools/export_puzzle_thumbs.py` 已接入本批已开放型号，目录缩略图从实际模型导出；
全部 32 个开放型号及系列入口已生成。未重新打包 Android。

录入的“检查”改为按真实贴片置换枚举单块合法颜色朝向，再核对各块轨道的
颜色组合数量；避免平行顶底轴、连体偏心轴或 Dogic 三色块套用普通魔方
朝向规则而误报。此检查不代替完整群可达性核验，提示文案已明确区分。

整合清单见 `expanded-integration-inventory.json`；当前活动入口及缩略图为 32 个。
字母形扩展的宏表与稳定子表单独列出；本轮新增表没有恢复之前排除的六张旧大型距离表。

### 本轮追加参考

- [Jaap 的实物收藏照片](https://www.jaapsch.net/puzzles/gallery.htm?d=0&i=2&p=6)：Calvin L、T、Trio、X、Temple、Cross 扩展系列。
- [Trio-Cube 产品](https://www.puzzlemaster.ca/browse/cubepuzzle/otherrubiks/8155-3x3x5-trio-cube-with-evgeniy-logo-stickerless)：系列与型号名称。
- [TomZ 的 Master Brilic](https://www.tomvanderzanden.nl/puzzle.php?puz=Master+Brilic)：360 面片、Crystal 的浮动内棱加浅层。
- [Rob 的 Rediminx 实物收藏](https://www.robspuzzlepage.com/rearrangement.htm#rediminx)：弯曲接缝和 Dino 十二面体机构参考。
- [Blanker 产品图片](https://store.tribox.com/products/detail.php?product_id=3635)：白色九格外观与偏心二阶机构。

### Master Brilic 的专用降阶

浅层面转与普通五魔的 20 角、30 棱逐面对应。求解先恢复这部分，再分别处理
60 个内棱及两组各 60 个中心块。预计算仅保存三条独立三循环，逐条确认：
只改变指定三个物理块、不拆块、没有额外方向残留。每组还核验全部
60×59×58/3 个有向三循环的共轭覆盖，避免短搜索深度限制。
`master_brilic_cycles.bin` 为 206 字节；不需要完整 360 面片稳定子表。
当前公式仍较长，实际动画播放时间会明显长于计算时间。

追加种子 977 的七款字母形案例：各打乱 45 步，经六视图重建后求解，全部回放还原。
Master Brilic 另用种子 1／977 各打乱 72 步，仅输入颜色；分别 3148／3023 步回放还原。
详见 `letter-six-view-extra-probe.json` 与 `expanded-extra-manual-probe.json`。
镜面五魔的形状卡片增加斜视角，以显示中心块的实际高度，不用正面五边形猜厚度。
