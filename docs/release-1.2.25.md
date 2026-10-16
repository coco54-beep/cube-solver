# 1.2.25 — 拍照与输入体验 / Photo scan & input polish / 写真と入力の改善

## 中文

- 拍照识别按录入页的面顺序（F→R→U→B→L→D）逐面扫描：按 < / > 切换时提示魔方转动方向，叠加取景框方便对齐，未拍完也可应用到录入；相机预览按设备方向自动校正。
- 各输入页把多余的**校验**按钮换成**赋予初始值**：一键把当前魔方设为已还原态，之后即可使用公式／拧动。粽子、镜子、形状、镜子魔塔等输入页进入时预置中心块，方便对位。
- 首页新增底部操作栏（Σ 公式库 · 相机 · 设置），图标风格统一；「使用说明」弹窗字号随屏幕自适应，并补充公式库、练习、拍照识别三节。
- 打乱步数随魔方规模放大（高阶五魔方、足球），繁花五魔方加长打乱；求解失败的提示改为多语言，不再外露内部字符串。
- 工程增强：应用内 UI 冒烟自检 + 截图基线回归、adb 真机自检脚本、i18n 覆盖审计。

### 安装

- Android：`cubesolver-1.2.25-arm64-v8a-release.apk`（CI 构建的 release 包），Android 8.0 及以上、64 位 ARM 设备。沿用本地签名；不同签名来源无法互相覆盖。
- Windows：`CubeSolver-1.2.25-windows-x64.zip`，完整解压后运行 `CubeSolver/CubeSolver.exe`，保留旁边的 `_internal` 目录，无需安装 Python。
- 拍照仍限五阶以内；普通 N 阶仍支持 6–17 阶。

## English

- Photo scanning follows the input page's face order (F→R→U→B→L→D): switching with < / > shows which way to turn the cube, an alignment guide overlays the preview, and a partial scan can be applied. The camera preview is auto-oriented to the device.
- Every input page replaces its redundant **Validate** button with a one-tap **Set initial** that resets the puzzle to the solved state for use with formulas / manual turning. Mastermorphix, Mirror, shape and Mirror Tower pages pre-place their centre pieces for easier alignment.
- Home gains a bottom action bar (Σ formula library · camera · settings) with matching icon buttons; the Help dialog now scales to the screen and documents the formula library, practice and photo scanning.
- Scrambles scale with puzzle size (higher-order Megaminx, Football); the Blossom Megaminx scrambles longer. Solve-failure messages are localised instead of exposing internal strings.
- Engineering: an in-app UI smoke self-check with screenshot-baseline regression, an ADB device self-check, and an i18n coverage audit.

Download the arm64-v8a release APK (Android 8+) or the Windows x64 portable ZIP; extract the Windows archive completely and retain `_internal`. Photo scanning remains limited to order five; standard N-order solving remains 6–17.

## 日本語

- 写真読み取りが入力画面の面順（F→R→U→B→L→D）に従います。＜／＞での切り替え時にキューブの回転方向を案内し、ガイド枠を重ね、未撮影でも適用できます。カメラ映像は端末の向きに自動補正します。
- 各入力画面の余分な**検証**ボタンを**初期値を設定**に置き換え、ワンタップでパズルを初期（完成）状態に戻します（公式・手動回転に利用）。Mastermorphix／Mirror／形状／Mirror Tower の入力画面は中心ピースを先に置きます。
- ホーム下部に操作バー（Σ 公式集・カメラ・設定）を追加し、アイコンを統一。使い方ダイアログは画面に応じて拡大し、公式集・練習・写真読み取りの説明を追加しました。
- スクランブル手数はパズルの規模に応じて増加（高次 Megaminx・Football）、Blossom Megaminx は長め。求解失敗メッセージを多言語化しました。
- エンジニアリング：アプリ内 UI スモーク自検 + スクリーンショット基準回帰、ADB 実機自検、i18n カバレッジ監査。

Android 8 以上の arm64-v8a release APK、または Windows x64 ポータブル ZIP をご利用ください。Windows 版は全体を展開し `_internal` を残します。写真読み取りは 5 段以下、通常 N 次求解は 6〜17 段のままです。
