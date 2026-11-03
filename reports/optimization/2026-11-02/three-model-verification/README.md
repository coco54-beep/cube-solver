# 十四面直升机、星寻足球、AJ 四阶曲线五魔核实

核实日期：2026-11-02。范围为型号对应、现有代码、参考定义及候选混转位置。没有修改 App 转动规则、输入入口或分类，也没有打包。

后续用户确认：星寻足球不支持混转，不再继续追查或增加混转动作。以下星寻足球探测仅保留为当前推导模型的历史记录，不作为实物动作依据；后续修正优先级中的星寻足球项已取消。

后续用户也确认 AJ 四阶曲线五魔不支持混转。保留双层 120°常规动作，不增加混转；下文未确认项作为核实过程记录，不继续追查。

十四面直升机后续已补整块混转、形变打乱及状态求解，见 [实现与验证报告](../helicopter-14/README.md)。下文“软件缺口”记录的是核实时的旧状态。

## 结论

| 型号 | 本轮结论 | 软件缺口／后续处理 |
| --- | --- | --- |
| 十四面直升机 `helicopter_14` | 对应 LanLan Corner-Cut Helicopter，商品资料明确说明可 jumbling、可形变；不是十四面齿轮。当前切面模型也找到约 70.5288°准备后的重叠转层分离位置 | 当前仅 180°固定槽位不完整，应补整块姿态、隐藏材料与混转阻挡；准备角来自软件几何计算，不能说商品说明认证了精确角度 |
| 星寻足球 `kairis_star_finder` | 现有照片推导模型中，约 44.4775°准备后出现新的重叠转层分离位置，是需要优先验证的混转候选 | 仍未取得与该商品完全对应的设计者机构定义／实物连续转动证据，不能宣布实物角度已核实，也不能说它不会形变 |
| AJ 四阶曲线五魔 `aj_curvy_dinominx_4` | 型号对应 AJ 4-Layer / 4x4 Curvy Dinominx。双层转角机构及当前 120°常规动作有依据；未证实遗漏混转 | 本轮测试的两层、44.4775°和 60°准备位置均未发现可分离的重叠转层。这不是任意状态、任意角度的否定证明；保留常规动作，不凭猜测开放混转 |

## 外部证据及来源强弱

### 十四面直升机

- [Kubekings：LanLan Helicopter Corner Cutted](https://kubekings.com/cubos-curvy/lanlan-helicopter-corner-cutted.html) 的商品描述明确写出截角同色、支持 jumbling 并产生形变。属于销售方资料，支持型号对应及动作类别，不提供精确几何尺寸。
- [CubeIn：LanLan 12-Axis Tetradecahedral](https://cubein.cn/products/lanlan-12-axis-tetradecahedral-helicopter) 将同款列为十二轴十四面截角直升机，也写明支持 jumbling。营销描述不能用于认证精确准备角或内轨结构。
- [Pinturas do AUwe：Corner Cutted Helicopter 原作者教程页面](https://www.pinturasdoauwe.com.br/2026/07/tutorial-corner-cutted-helicopter-cube.html) 的搜索索引列出恢复外形章节（05:50）。正文／视频本轮未成功打开，故仅记为进一步观看线索，未声称已逐帧确认。

代码 `cube/lanlan_polyhedra.py` 仅十二条棱轴、180°固定槽位。外壳为六个方形区域及八个同色截角三角区域。与上述截角款的身份一致；混转能力不能因为截角而删掉。

### 星寻足球

用户参考图片为 `artifacts/expansion-references/confirmed-2026-10-27/kairis-solved.jpg` 和 `kairis-turned.jpg`。旧实现报告为 `reports/expansion/2026-10-29/star-finder/README.md`。

当前 `cube/star_finder.py` 明确采用照片推导的二十轴深切截角二十面体。切深由相邻六边形轴穿过面中心的假设确定，不是厂家测量值。

检查了 [Kairis 的设计博客](https://kairispuzzles.github.io/) 四页目录，未找到能够直接对应星寻足球的机构说明。博客中的 Hexgram Icosahedron 为三十二轴，不能代替本款二十轴。pCubes 的 Radiolarian 4 / Eitan's Star 虽有相同形式的候选角，也不能当成同一商品的认证。

因此，44.4775°是**当前推导几何的计算结果**，不是已确认的实物许可角。实物内轨、隐藏连接及切深仍待对应资料确认。

### AJ 四阶曲线五魔

- [tribox：AJ 4-Layer Curvy Dinominx](https://store.tribox.com/products/detail.php?product_id=3077) 对应 AJ Lu 的十二面体、Dino 类转角机构；解释虽可看作五层，设计者称其 4x4。
- [ZiiCube：AJ Curvy Dino Megaminx](https://www.ziicube.com/AJ-Curvy-Dino-Megamin) 列出 AJ 品牌、D9001 型号，可用于对应外形和商品身份。
- 本地原始模拟定义 `bin/pCubes/Puzzles/Other forms/Platonic solids/Dodecahedron/Vertex Turning/4x4 Dinominx.xml`：Inventor=AJ，Programmer=Evgeniy Grigoriev，Added=2017-06-04，二十顶点轴、两切深、TurningAngles=2*Pi/3，没有 JumbleAngle。
- 该定义指向 [mf8 设计讨论](http://bbs.mf8-china.com/forum.php?mod=viewthread&tid=107295)，本轮连接失败，未声称读到讨论内容。

pCubes 定义为平面切割，而 App 为球切版本。无 JumbleAngle 不能证明曲面实物禁止全部混转。销售方确认了转角机构，但没有足够的原始设计资料认证任意非标准角度。

## 几何探测结果与边界

`planar-probes.json` 保存两款平切模型的结果，`dinominx-probes.json` 保存 AJ 球切结果。探测包括未上色的内部材料，不只看面片中心或屏幕网格。

- 十四面直升机：完整切分 45 个材料单元；轴 0 准备 70.5287793655°后，轴 3、4 与原选中材料重叠且切面不穿块；邻轴 1、2、5、6 仍被阻挡。
- 星寻足球：完整切分 183 个材料单元；轴 0 准备 44.4775121859°后，轴 3、9、12 出现同类分离位置；轴 1、2、4、10、11、13 仍被阻挡。
- AJ 四阶：球切分区 131 个正体积材料单元；深、浅两层分别准备 44.4775121859°、60°，四个探测均未出现可分离的重叠转层。

这里的“分离位置”只证明在该姿态下候选切面没有贯穿一个完整材料块，并且不只是另转一个无关的层。它不是实物制造认证，也不等于已检查整个转动轨迹的连续碰撞、内部导轨或任意交织状态。没有用这些探测结果开放 App 动作。

## 修正优先级

1. 十四面直升机：混转类别依据充分，适合复用已补的普通直升机整块机构，并使用独立截角外壳与阻挡验证。
2. 星寻足球：先核实实际切深、特殊对齐和内轨，再决定开放的混转动作；当前固定槽位不能称为全机构实现。
3. AJ 四阶：保留双层 120°，继续等待／查找同款实物部分转动证据，不将“没查到”改写为“不会形变”。
