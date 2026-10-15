# 1.2.23 — 拍照识别 / Photo scanning / 写真読み取り

## 中文

### 下载

- Android arm64-v8a：`cubesolver-1.2.23-arm64-v8a-debug.apk` 为本次本地打包的试用安装包，包含新增异形拍照识别。
- Windows x64：`CubeSolver-1.2.23-windows-x64.zip` 由标签发布流程构建并上传。完整解压后运行 `CubeSolver/CubeSolver.exe`，保留 `_internal`。
- 标签发布流程还会独立构建 Android release APK；文件名中的 `debug` 和 `release` 区分两种构建。不同签名的安装包不能直接互相覆盖。

### 新增与修正

- 首页拍照入口可选择普通魔方和 15 个异形系列，共 31 个异形类型／阶数组合，全部限制在五阶以内。
- 支持斜转 3／5 阶、恐龙 2 阶、格子 4 阶、四叶草、八叶花、常春藤、空心三阶、潘多拉三阶、金字塔 2–5 阶、魔塔 3–5 阶、空心魔塔三阶、转面八面体 2–4 阶、二十面体 2–5 阶、五魔方 2–5 阶、繁花五魔方三阶及足球 3／5 阶。
- 使用模型的真实色块轮廓取色，空洞不参与识别；三角形、正方形、五边形和六边形有各自的顶点对齐框。
- 小模型在停稳时正对当前面，左右箭头播放整体翻面，帮助保持拍摄朝向。未确定颜色保留为空，允许点模型逐块修正。
- 新增取色校准，重新处理已定位的各面照片并保留手动改色。二十面体、足球分别提供 20、32 色编号。
- 支持从异形录入页进入拍照并回填。潘多拉在六面完整后校验块组合并重建块及方向；其他多面体可以先应用部分结果再补录。
- Android 照片导入使用系统选择器；相机显示区域、传感器方向与识别框共用图像坐标，切换应用时释放并恢复相机。

### 验证范围与限制

- 本次新增实现做过源码语法检查；APK 会核对打包源码、字节码与求解资源。没有把旧版本的求解检查数量作为新识别功能的通过数量。
- **新增异形的实拍准确率尚未验证，也没有执行本次新增功能的手机操作测试。** 反光、阴影、近似色仍可能需要校准与手动修正。
- 三角面使用三点仿射映射，需要尽量正对面拍摄。模板只覆盖模型支持的正常拼形状态；镜面、曲面外壳、明显形变及错层玩法不在本次范围。
- 五阶上限只适用于拍照识别。普通 N 阶求解仍支持 6–17 阶，原有求解与演示范围保持不变。

详见[拍照支持清单和操作说明](https://github.com/coco54-beep/cube-solver/blob/v1.2.23/docs/photo-scan.md)。

## English

Adds photo scanning through order five for standard cubes and 15 irregular families (31 irregular type/order combinations), including Icosahedron orders 2–5. Model-derived sticker regions, vertex/cut alignment, whole-puzzle turn animation, numbered color calibration, manual correction, and transfer to existing puzzle input are included. Android uses the system photo picker and corrected camera/frame coordinates. The local arm64 debug APK is a testing build; Windows portable files and an Android release build are produced separately by the tag workflows. Builds with different signing keys cannot overwrite each other.

**Real-photo accuracy for the new irregular profiles and phone interaction have not been validated in this release task.** Source syntax and package contents are checked separately from recognition accuracy. Similar colors, glare and shadows may require calibration or editing. Triangular faces should be photographed straight on. Curved/changing shells, mirror finishes and jumbling states are outside the fixed-face templates. Standard N-order solving remains 6–17; the order-five limit applies only to scanning.

## 日本語

通常のキューブと15系統・31種類／段数の変形パズルに、5段以下の写真読み取りを追加しました。二十面体は2〜5段に対応します。モデルのステッカー領域、頂点と切れ目の位置合わせ、全体回転アニメーション、番号付きの色校正、手動修正、既存入力画面への反映を提供します。Android はシステム写真選択画面と修正済みカメラ座標を利用します。ローカルの arm64 debug APK は試用版です。Windows 便携版と Android release APK はタグの公開フローで別途生成されます。署名が異なるビルド同士は上書きできません。

**新しい変形テンプレートの実写精度と今回のスマートフォン操作は未検証です。** 構文・パッケージ内容の確認と認識精度は別扱いです。近い色、反射、影は校正または手動修正が必要な場合があります。三角面は正面から撮影してください。曲面、変形する外形、鏡面、ジャンブリング状態は対象外です。通常の N 次求解は6〜17段のままで、5段の上限は写真読み取りだけに適用します。
