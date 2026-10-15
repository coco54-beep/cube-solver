# 1.2.24 — 进阶公式与练习 / Advanced algorithms and practice / 上級公式と練習

## 中文

- 离线公式库覆盖普通2–5阶、SQ1、斜转、金字塔和三阶五魔方，共43个合并公式集、6,060个可演示情况。包含典型情况、阶段前提、备选公式和原生3D演示；来源为普通标签。
- 二阶、三阶、SQ1、金字塔支持自选公式集练习，加入随机对位与拿法、常用公式、学习状态、薄弱情况优先。打乱直接显示，演示使用当前题目。
- 二阶、三阶、SQ1尝试在后台通过独立求解生成打乱，核对与题目一致后采用；超时或不可用时使用合法备用打乱。金字塔使用公式备选与拿法变化。
- 练习新增OK／+2／DNF、ao5／ao12和最近成绩；完成前查看答案的题目不计成绩。学习进度与常用公式保存于本机。
- 三阶、三阶五魔方和SQ1使用公式收尾候选，只有完整回放还原且总步数更少时才替换原解；不会保证每个局面都缩短。
- 修复SQ1连续括号转层的解析，以及部分高阶金字塔与异形三阶教程加载问题。

### 安装

- Android：`cubesolver-1.2.24-arm64-v8a-debug.apk`，Android 8.0及以上、64位ARM设备，沿用本地debug签名。只要已安装版本签名相同即可覆盖更新；不同来源签名无法互相覆盖。
- Windows：`CubeSolver-1.2.24-windows-x64.zip`，完整解压后运行`CubeSolver/CubeSolver.exe`，保留旁边的`_internal`目录，无需安装Python。
- 发布资产包含SHA-256校验文件与安装包验证摘要。Windows便携包在冻结环境中检查求解器、公式数据及练习模块；APK核对源码字节码和随包资源。本次不执行ADB安装或手机操作测试。

拍照仍限五阶以内，普通N阶仍支持6–17阶。手机实拍识别精度与新练习界面的真机操作不属于本次桌面及包内容验证的结论。

## English

Adds an offline advanced library with 43 consolidated sets and 6,060 cases for standard orders 2–5, Square-1, Skewb, Pyraminx and 3-layer Megaminx. Includes stage prerequisites, alternatives and native 3D playback, with plain source attribution.

Practice supports 2×2, 3×3, Square-1 and Pyraminx: set selection, varied holds/alignment, preferred algorithms, learning status, weak-case prioritization, inline scrambles, OK/+2/DNF, ao5/ao12 and recent results. Revealing an answer before finishing excludes that attempt. Playback matches the actual question. Independent setup search runs in the background for 2×2/3×3/Square-1, with a verified legal fallback; Pyraminx uses source alternatives and varied holds.

Native formula finishes are used only when full replay solves the input with fewer moves. Fixes Square-1 adjacent parenthesized turns and loading of certain irregular tutorials. Shorter solutions are not guaranteed for every state.

Download the arm64-v8a debug APK (Android 8+) or Windows x64 portable ZIP. Extract the Windows archive completely and retain `_internal`. The APK retains the existing local debug signing key; differently signed packages cannot overwrite one another. Package verification summaries and SHA-256 files accompany the downloads. No ADB installation or phone interaction tests are performed in this release task. Photo scanning remains limited to order five; standard N-order solving remains 6–17.

## 日本語

通常2〜5段、Square-1、Skewb、Pyraminx、3段Megaminx向けのオフライン上級公式集を追加しました。43セット・6,060ケースで、適用段階、代替公式、ネイティブ3D再生を提供します。出典は通常のラベルです。

2×2・3×3・Square-1・Pyraminxの練習に、セット選択、向きと位置合わせの変化、お気に入り公式、学習状態、苦手優先、画面内スクランブル、OK/+2/DNF、ao5/ao12、最近の記録を追加しました。終了前に解答を表示した試行は成績対象外です。再生は現在の問題と一致します。2×2・3×3・Square-1はバックグラウンドで別解からのスクランブル生成を試み、時間切れ時は合法な代替手順を使います。Pyraminxは代替公式と持ち方の変化を使います。

公式による終盤短縮は完全再生で復元でき、総手数が減る場合のみ採用します。Square-1の連続括弧付き回転と、一部変形パズルの教材読み込みを修正しました。すべての状態で短縮する保証はありません。

Android 8以上のarm64-v8a debug APK、またはWindows x64のポータブルZIPをご利用ください。Windows版は全体を展開し、`_internal`を残します。APKは既存のローカルdebug署名を継続し、異なる署名のアプリへは上書きできません。SHA-256とパッケージ検証概要を添付します。今回はADBのインストールや実機操作テストを行いません。写真読み取りは5段以下、通常N次求解は6〜17段のままです。
