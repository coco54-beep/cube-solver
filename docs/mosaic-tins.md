# Mosaic Cube 与 Tins Cube

入口：首页 → 特殊异形 → 对应型号。两款均使用八个角轴，每轴提供浅层、内层两个120°转动层。

## 型号区别

| 型号 | 独立角块 | 其他块 | 贴纸数 |
| --- | --- | --- | --- |
| Mosaic / Fadi Cube | 八个，位置固定、朝向可变 | 24个外围块、12个双色中心块 | 96 |
| Tins Cube | 四个交替分布，位置固定、朝向可变 | 12个三角块、12个五边形块、12个双色中心块 | 84 |

Mosaic 对应 Meffert's / Oskar van Deventer 的 Fadi 结构。Tins 对应 Cho Hyun-Jun 的设计，四个角采用 Dino 式切割，另四个采用 Redi 式角块。Tins 的五层标法与八角均带角块的 Mosaic 四层标法分别保留，两者没有互相替代。

外观比例依据公开商品照片近似；未使用厂商 CAD，也未做实物录入验证。配色采用软件的六色方案，可通过调色设置匹配自己的实物。

## 模型与求解

`cube/mosaic.py` 为两款分别构造面片、角块和合法置换，复用四层 Lattice 的三组十二块轨道。浅层仅带动本角的角块与一组外围块；内层带动另一组外围块及双色中心块。Tins 没有角块的四个角不会产生虚构角块。

求解先调整固定角块朝向，再处理三组十二块轨道；只依据录入颜色，无需打乱历史。预制公式包含角块不被破坏的约束，每次返回结果前从录入状态完整回放。

`python tools/build_mosaic.py` 离线生成两款公式数据。文件为 `solver/data/mosaic_cycles.bin` 和 `solver/data/tins_cycles.bin`，带几何指纹。教程各提供三类三循环的正反向情况，共六例，区分中心、外围块或三角形／五边形。

## 来源

- [Tins Cube，制作与销售方的设计说明](https://www.chewiescustompuzzles.com/puzzleshop/p/tins-cube)
- [Mosaic 实物与双层转动说明](https://fan2cube.fr/mosaic1.php)
- [Mosaic 实物收藏资料](https://www.cs.brandeis.edu/~storer/JimPuzzles/ZPAGES/zzzMosaicCube.html)
