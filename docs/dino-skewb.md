# 两款 Dino Skewb

入口：首页 → 特殊异形。分别列出 `Dino Skewb · TomZ` 与 `Dino Skewb · 大雁`。

## Tom van der Zanden 版

八个角向均有120°的 Dino 浅切和 Skewb 深切。Dino 面的切平面通过相邻顶点，Skewb 平面通过体心。外观包含24个双色块、24个单色中心，共48块、72个贴纸。四个十二块轨道共用实际几何置换。

操作页的两种选项对应真实动作：深切直接带动半个魔方，不需要先点浅切再补一个内层。锁定后的拖动也遵循所选模式。

[原设计者的结构说明及实物照片](https://www.tomvanderzanden.nl/puzzle.php?puz=Dino+Skewb)

## 大雁／Timur Evbatyrov 版

采用不对称 F-Skewb 结构，四条对角线的两端不同。小角端支持 Dino 浅切和较大的深切；对端只有较小的 Skewb 式深切。模型包含4个三色小角、12个双色棱块、12个单色中心，共28块、48个贴纸。

切割比例依据公开商品照片近似，不是厂商 CAD。模型保留一组通过顶点的 Dino 切面，另一组偏置切面没有替换成通过体心的 TomZ 切面。不同端可选择的动作数量也不同。

[制作与销售资料中的结构说明](https://www.puzzlemaster.ca/browse/inventors/evbatyrov/8250-dino-skewb-cube-black-body)

## 输入、求解和教程

输入、拧动、求解、播放使用对应型号自己的块位与置换。求解只读取颜色；每次返回结果前完整回放。预制三循环数据带几何指纹，手机不需临时搜索公式。

`python tools/build_dino_skewb.py` 生成两款独立数据。TomZ 版有8个典型情况教程，大雁版有4个，均包含正反向三循环及位置标注。

尚未进行实物录入核对和手机验证，也未为本次新增型号重新打包 APK。
