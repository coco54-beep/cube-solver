# 1.2.27 — 统一操作与求解界面 / Unified controls and solving / 操作と求解画面の統一

## 中文

- **求解界面统一**：普通魔方、异形和 SQ1 使用同一求解页，显示模型、阶段进度和取消按钮；取消返回原输入，失败统一提示，忽略旧任务的迟到结果。
- **镜头控制统一**：输入、拧动、还原共用锁定与跟随设置；锁定视角会将跟随设为 0，开启跟随会自动解锁，复位视角保留设置。
- **操作行为整理**：动画中避免重复操作，手动走步暂停自动播放，跳转或返回前暂停；批量输入、打乱和拧动返回保留撤销记录。
- **Android 修复**：随机打乱改用独立的轻量模块并保留失败前输入；补齐 APK 中遗漏的 `twophase` 求解代码，避免 `No module named 'twophase.defs'`。
- 本次新界面改动完成语法及包内容核对，尚未进行手机回归。此前模块修复在模拟器上完成三阶与七阶金字塔求解回放核对。

## English

- **Unified solving page** for standard cubes, irregular puzzles and Square-1: model, stage progress and Cancel; cancellation preserves input, errors use one presentation, and late results cannot redirect the UI.
- **Shared camera controls** across input, turning and playback: locking sets follow to zero; enabling follow unlocks the view; resetting the camera preserves these settings.
- **Consistent buttons**: prevent overlapping edits during animation, pause autoplay on manual steps and before navigation confirmations, and retain undo history for bulk entry, scrambles and returning from turning.
- **Android fixes**: lightweight scramble imports preserve entered data on failure; include the missing bundled `twophase` modules to prevent `No module named 'twophase.defs'`.
- New UI changes received syntax and package-content checks, without phone regression testing. Earlier module fixes passed 3×3 and order-seven Pyraminx solve/replay checks in the emulator.

## 日本語

- **求解画面を統一**：通常・変形パズル・SQ1 に同じモデル表示、段階進捗、キャンセルボタンを使用。取消時は入力を保持し、失敗表示を統一。古い処理結果による画面遷移を防止します。
- **カメラ設定を共通化**：入力・回転・再生で共有。視点ロック時は追従を 0 にし、追従を有効にするとロック解除。視点リセットで設定は変わりません。
- **操作整理**：アニメーション中の重複操作を防止。手動ステップと移動確認時に自動再生を停止。一括入力・スクランブル・回転画面から戻る際の取り消し履歴を保持します。
- **Android 修正**：軽量なスクランブル処理と失敗時の入力保持。APK に不足していた `twophase` コードを含め、`No module named 'twophase.defs'` を修正しました。
- 新しい画面変更は構文とパッケージ内容を確認し、実機回帰テストは未実施です。先行するモジュール修正では、エミュレーター上で三階と七階 Pyraminx の求解・再生を確認しました。

