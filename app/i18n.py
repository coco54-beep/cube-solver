"""多语言（i18n）支持：简体中文 / English / 日本語。

设计：
    * 一个全局 Translator（EventDispatcher）持有当前语言，提供 tr(key, **kw)。
    * CATALOG 按语言存放界面文案；缺键时按 en -> zh -> key 回退。
    * 语言持久化到共享偏好文件（app.prefs），首次启动跟随系统语言。

用法：
    from app.i18n import tr
    label.text = tr("home.help")
    label.text = tr("home.version", version="1.2.4")
"""

import os

from kivy.event import EventDispatcher
from kivy.properties import StringProperty

LANG_ZH = "zh"
LANG_EN = "en"
LANG_JA = "ja"
LANGUAGES = (LANG_ZH, LANG_EN, LANG_JA)

# 语言的自称（语言按钮显示用，保持各自母语写法）
LANGUAGE_NAMES = {
    LANG_ZH: "简体中文",
    LANG_EN: "English",
    LANG_JA: "日本語",
}

_PREFS_KEY = "language"


# ===== 界面文案 =====
CATALOG = {
    LANG_ZH: {
        "app.name": "3D魔方智能还原",
        "face.U": "上", "face.D": "下", "face.F": "前",
        "face.B": "后", "face.R": "右", "face.L": "左",

        "stage.centers": "整理中心",
        "stage.edge_pairing": "棱块配对",
        "stage.orient": "中棱朝向修正",
        "stage.parity": "特殊翻棱处理",
        "stage.reduced_3x3": "按3阶方式还原",
        "stage.done": "完成",

        "home.subtitle": "2 阶 / 3 阶 / 4 阶 / 5 阶魔方 · 智能还原",
        "home.card.2.title": "2 阶魔方",
        "home.card.2.desc": "还原 Pocket Cube",
        "home.card.3.title": "3 阶魔方",
        "home.card.3.desc": "还原 Rubik's Cube",
        "home.card.4.title": "4 阶魔方",
        "home.card.4.desc": "还原 Rubik's Revenge",
        "home.card.5.title": "5 阶魔方",
        "home.card.5.desc": "还原 Professor's Cube",
        "home.help": "使用说明",
        "home.version": "版本 {version}",
        "home.settings": "设置",

        "theme.auto": "自动",
        "theme.light": "浅色",
        "theme.dark": "深色",

        "settings.title": "设置",
        "settings.theme": "主题",
        "settings.language": "语言",
        "settings.about": "关于",
        "settings.about_tagline": "2 阶 / 3 阶 / 4 阶 / 5 阶魔方 · 智能还原",

        "help.title": "使用说明",
        "help.close": "关闭",
        "help.select.title": "选择魔方",
        "help.select.body":
            "首页用卡片选择 2 / 3 / 4 / 5 阶魔方（横屏 1×4、竖屏 2×2）。\n"
            "点卡片进入对应的录入页；下方「使用说明」随时回到本页。",
        "help.input.title": "录入布局",
        "help.input.body":
            "展开图逐格点色即可录入每个面的颜色：先用六色选择器选中颜色，\n"
            "再逐个点格子。也可以点「随机」一键载入一套随机的打乱布局来测试破解；\n"
            "录入完成后可点「校验」检查布局是否合法。",
        "help.solve.title": "一键求解",
        "help.solve.body":
            "录入完成后点「开始求解」，程序在后台计算还原步骤，\n"
            "实时显示当前阶段与进度，可随时取消。",
        "help.playback.title": "3D 回放",
        "help.playback.body":
            "求解结果用 3D 视图逐步演示：拖动旋转视角，滚轮 / 双指缩放；\n"
            "支持上一步 / 下一步 / 自动播放 / 跳到结尾，也可调节播放速度。",
        "help.demo.title": "教学演示",
        "help.demo.body":
            "演示目录按阶数收录了标准案例：2 阶分层法、3 阶七步法、\n"
            "4 阶与 5 阶降阶法。其中 5 阶只聚焦它与 4 阶不同的地方——\n"
            "中心是 3×3（有固定中心点）、每条棱由中棱 + 2 翼三块组成。",
        "help.theme.title": "主题切换",
        "help.theme.body":
            "在首页进入「设置」页，可选择 自动 / 浅色 / 深色 主题；\n"
            "自动模式会跟随系统（Windows / Android）的浅深色设置。",
        "help.notation.title": "颜色与记号",
        "help.notation.body":
            "魔方六色固定：上黄、下白、前蓝、后绿、左橙、右红。\n"
            "常用记号：R L U D F B 转最外层，加 ' 表示逆时针，加 2 表示转 180°；\n"
            "小写（如 r u）表示宽层（一次多转一层），4/5 阶降阶法常用。",
        "help.algo.title": "求解原理（进阶）",
        "help.algo.body":
            "2 阶与 3 阶按两阶段算法（Kociemba）求解，保证步数很少；\n"
            "4 阶与 5 阶用降阶法：先还原中心块，再配对棱块，最后当作 3 阶还原。\n"
            "注：5 阶对很深的随机打乱，配棱阶段可能无法保证完整还原，\n"
            "此时会提示失败而非给出错误解法。",

        "input.back": "←返回",
        "input.title": "录入 {n}x{n}",
        "input.demo": "演示",
        "input.face": "当前面：{face} ({code})",
        "input.pick": "吸色",
        "input.fill": "整面填充",
        "input.undo": "撤销",
        "input.redo": "重做",
        "input.prev": "{arrow}上一步",
        "input.next": "{arrow}下一步",
        "input.twist": "拧魔方",
        "input.random": "随机",
        "input.scramble": "粘贴打乱公式",
        "input.scramble.hint": "如 R U R' U' 或 R,U,R',U'",
        "input.scramble.ok": "应用",
        "input.scramble.loaded": "已按公式打乱（{k} 步）",
        "input.scramble.empty": "请输入打乱公式",
        "input.scramble.error": "无法识别的动作：{tok}",
        "input.clear": "清空",
        "input.check": "校验",
        "input.solve": "开始求解",
        "input.missing": "未填写: {list}",
        "input.valid": "状态合法 ✓",
        "input.filled": "已将 {face} 面填充为 {col}",
        "input.already": "{face} 面已是 {col}",
        "input.undone": "已撤销",
        "input.redone": "已重做",
        "input.picked": "已吸色 {col}，可继续填色",
        "input.random_loaded": "已加载随机布局（{k} 步打乱）",
        "input.cleared": "已清空",
        "input.resumed": "已加载上次布局，直接点「开始求解」可沿用上次方案",
        "input.clear.title": "确认清空",
        "input.clear.msg": "确定要清空全部已录入的颜色吗？",
        "input.cancel": "取消",
        "input.clear.ok": "确定清空",

        "solving.title": "正在求解…",
        "solving.preparing": "准备中",
        "solving.cancel": "取消",
        "solving.cancelling": "正在取消…",
        "solving.pairing": "棱块配对 {done}/12",
        "solving.depth": "中心求解深度 {depth}",

        "playback.total": "共 {k} 步",
        "playback.step": "第 {i}/{t} 步",
        "playback.start": "回到初始",
        "playback.prev": "上一步",
        "playback.play": "播放",
        "playback.pause": "暂停",
        "playback.next": "下一步",
        "playback.end": "跳结尾",
        "playback.reset_view": "还原视角",
        "playback.back": "返回录入",
        "playback.speed": "速度",
        "playback.hold": "停留",

        "demo.back_to_menu": "←目录",
        "demo.no_image": "无图",
        "demo.switch": "切换阶数",
        "demo.playing": "播放中…",
        "demo.case": "案例：{name}",
        "demo.step_n": "第{n}步",
        "demo.title_step": "第{cn}步 · {title}（{i}/{total}）",
        "demo.menu_step": "第{cn}步 · {title}",
        "demo.mode.menu.2": "二阶 · 教学目录",
        "demo.mode.menu.3": "三阶 · 教学目录",
        "demo.mode.menu.4": "四阶 · 教学目录",
        "demo.mode.menu.5": "五阶 · 教学目录",
        "demo.mode.title.2": "二阶 · 分层法",
        "demo.mode.title.3": "三阶 · 七步法",
        "demo.mode.title.4": "四阶 · 降阶法",
        "demo.mode.title.5": "五阶 · 降阶法",

        "twist.done": "完成",
        "twist.lock_on": "卡视角：开",
        "twist.lock_off": "卡视角：关",
        "twist.wide_on": "宽层：开",
        "twist.wide_off": "宽层：关",
        "twist.hint_lock_on": "卡视角开：拖动魔方拧层；滚轮缩放已锁定",
        "twist.hint_lock_off": "卡视角关：拖动转视角，滚轮缩放",
        "twist.hint_wide": "（宽层开：拧最外层时连同内层一起转）",
        "twist.congrats_title": "恭喜还原！",
        "twist.congrats_body": "你已成功还原魔方！",
        "twist.congrats_ok": "继续",
    },

    LANG_EN: {
        "app.name": "3D Cube Solver",
        "face.U": "Up", "face.D": "Down", "face.F": "Front",
        "face.B": "Back", "face.R": "Right", "face.L": "Left",

        "stage.centers": "Solving centers",
        "stage.edge_pairing": "Pairing edges",
        "stage.orient": "Fixing middle-edge orientation",
        "stage.parity": "Parity fix",
        "stage.reduced_3x3": "Solving as a 3×3",
        "stage.done": "Done",

        "home.subtitle": "2×2 / 3×3 / 4×4 / 5×5 Cubes · Smart Solver",
        "home.card.2.title": "2×2 Cube",
        "home.card.2.desc": "Solve the Pocket Cube",
        "home.card.3.title": "3×3 Cube",
        "home.card.3.desc": "Solve the Rubik's Cube",
        "home.card.4.title": "4×4 Cube",
        "home.card.4.desc": "Solve the Rubik's Revenge",
        "home.card.5.title": "5×5 Cube",
        "home.card.5.desc": "Solve the Professor's Cube",
        "home.help": "Help",
        "home.version": "Version {version}",
        "home.settings": "Settings",

        "theme.auto": "Auto",
        "theme.light": "Light",
        "theme.dark": "Dark",

        "settings.title": "Settings",
        "settings.theme": "Theme",
        "settings.language": "Language",
        "settings.about": "About",
        "settings.about_tagline": "Smart solving for 2×2 / 3×3 / 4×4 / 5×5 cubes",

        "help.title": "Help",
        "help.close": "Close",
        "help.select.title": "Choose a cube",
        "help.select.body":
            "Pick a 2 / 3 / 4 / 5 cube from the cards on the home screen "
            "(1×4 in landscape, 2×2 in portrait).\n"
            "Tap a card to open its input page; use Help below to return anytime.",
        "help.input.title": "Enter the layout",
        "help.input.body":
            "Tap cells to set each facelet's color: first pick a color from the "
            "six-swatch selector,\nthen tap the cells. Or press Random to load a "
            "random scramble for testing;\npress Validate to check whether the layout is legal.",
        "help.solve.title": "One-tap solve",
        "help.solve.body":
            "After entering the layout, press Solve; the solver computes the "
            "solution in the background,\nshowing the current stage and progress "
            "in real time. You can cancel at any time.",
        "help.playback.title": "3D playback",
        "help.playback.body":
            "The solution is played back step by step in a 3D view: drag to rotate, "
            "scroll / pinch to zoom;\nuse Prev / Next / Auto-play / Jump to end, "
            "and adjust the playback speed and hold time.",
        "help.demo.title": "Tutorial demos",
        "help.demo.body":
            "The catalog collects standard methods by order: 2×2 layer-by-layer, "
            "3×3 seven-step,\nand 4×4 / 5×5 reduction. The 5×5 section focuses on "
            "what differs from 4×4:\ncenters are 3×3 (with a fixed center) and each "
            "edge has a middle edge plus 2 wings.",
        "help.theme.title": "Theme",
        "help.theme.body":
            "Open Settings from the home screen to choose Auto / Light / Dark.\n"
            "Auto follows your system (Windows / Android) light or dark setting.",
        "help.notation.title": "Colors & notation",
        "help.notation.body":
            "The six colors are fixed: yellow up, white down, blue front, "
            "green back, orange left, red right.\n"
            "Notation: R L U D F B turn the outer layer; ' means counter-clockwise, "
            "2 means 180°;\nlowercase (e.g. r u) means a wide turn (multiple layers "
            "at once), common in 4×4 / 5×5 reduction.",
        "help.algo.title": "How it solves (advanced)",
        "help.algo.body":
            "2×2 and 3×3 use a two-phase algorithm (Kociemba) to keep move counts low;\n"
            "4×4 and 5×5 use reduction: solve centers, pair edges, then solve as a 3×3.\n"
            "Note: for very deep 5×5 scrambles the edge-pairing stage may not "
            "guarantee a full solution;\nit then reports failure instead of giving "
            "a wrong solution.",

        "input.back": "← Back",
        "input.title": "Enter {n}×{n}",
        "input.demo": "Demos",
        "input.face": "Face: {face} ({code})",
        "input.pick": "Eyedropper",
        "input.fill": "Fill face",
        "input.undo": "Undo",
        "input.redo": "Redo",
        "input.prev": "{arrow} Prev",
        "input.next": "{arrow} Next",
        "input.twist": "Twist",
        "input.random": "Random",
        "input.scramble": "Paste scramble",
        "input.scramble.hint": "e.g. R U R' U' or R,U,R',U'",
        "input.scramble.ok": "Apply",
        "input.scramble.loaded": "Scrambled from formula ({k} moves)",
        "input.scramble.empty": "Enter a scramble first",
        "input.scramble.error": "Unrecognized move: {tok}",
        "input.clear": "Clear",
        "input.check": "Validate",
        "input.solve": "Solve",
        "input.missing": "Missing: {list}",
        "input.valid": "Valid state ✓",
        "input.filled": "Filled face {face} with {col}",
        "input.already": "Face {face} is already {col}",
        "input.undone": "Undone",
        "input.redone": "Redone",
        "input.picked": "Picked {col}; keep filling",
        "input.random_loaded": "Loaded a random layout ({k}-move scramble)",
        "input.cleared": "Cleared",
        "input.resumed": "Loaded the previous layout; press Solve to reuse the last solution",
        "input.clear.title": "Confirm clear",
        "input.clear.msg": "Clear all entered colors?",
        "input.cancel": "Cancel",
        "input.clear.ok": "Clear",

        "solving.title": "Solving…",
        "solving.preparing": "Preparing",
        "solving.cancel": "Cancel",
        "solving.cancelling": "Cancelling…",
        "solving.pairing": "Pairing edges {done}/12",
        "solving.depth": "Center search depth {depth}",

        "playback.total": "{k} moves",
        "playback.step": "Move {i}/{t}",
        "playback.start": "Start",
        "playback.prev": "Prev",
        "playback.play": "Play",
        "playback.pause": "Pause",
        "playback.next": "Next",
        "playback.end": "End",
        "playback.reset_view": "Reset view",
        "playback.back": "Back to input",
        "playback.speed": "Speed",
        "playback.hold": "Hold",

        "demo.back_to_menu": "← Catalog",
        "demo.no_image": "No image",
        "demo.switch": "Switch order",
        "demo.playing": "Playing…",
        "demo.case": "Case: {name}",
        "demo.step_n": "Step {n}",
        "demo.title_step": "Step {n} · {title} ({i}/{total})",
        "demo.menu_step": "Step {n} · {title}",
        "demo.mode.menu.2": "2×2 · Tutorial Catalog",
        "demo.mode.menu.3": "3×3 · Tutorial Catalog",
        "demo.mode.menu.4": "4×4 · Tutorial Catalog",
        "demo.mode.menu.5": "5×5 · Tutorial Catalog",
        "demo.mode.title.2": "2×2 · Layer-by-Layer",
        "demo.mode.title.3": "3×3 · Seven-Step Method",
        "demo.mode.title.4": "4×4 · Reduction Method",
        "demo.mode.title.5": "5×5 · Reduction Method",

        "twist.done": "Done",
        "twist.lock_on": "Lock view: On",
        "twist.lock_off": "Lock view: Off",
        "twist.wide_on": "Wide: On",
        "twist.wide_off": "Wide: Off",
        "twist.hint_lock_on": "View locked: drag the cube to turn layers; zoom is locked",
        "twist.hint_lock_off": "View free: drag to rotate the view, scroll to zoom",
        "twist.hint_wide": "(Wide on: turning the outer layer also turns the inner layer)",
        "twist.congrats_title": "Congratulations!",
        "twist.congrats_body": "You solved the cube!",
        "twist.congrats_ok": "Continue",
    },

    LANG_JA: {
        "app.name": "3Dルービックキューブ ソルバー",
        "face.U": "上", "face.D": "下", "face.F": "前",
        "face.B": "後", "face.R": "右", "face.L": "左",

        "stage.centers": "センターを揃える",
        "stage.edge_pairing": "エッジをペアリング",
        "stage.orient": "中エッジの向きを修正",
        "stage.parity": "パリティ処理",
        "stage.reduced_3x3": "3×3 として解く",
        "stage.done": "完了",

        "home.subtitle": "2×2 / 3×3 / 4×4 / 5×5 キューブ · スマート攻略",
        "home.card.2.title": "2×2 キューブ",
        "home.card.2.desc": "ポケットキューブを解く",
        "home.card.3.title": "3×3 キューブ",
        "home.card.3.desc": "ルービックキューブを解く",
        "home.card.4.title": "4×4 キューブ",
        "home.card.4.desc": "ルービックリベンジを解く",
        "home.card.5.title": "5×5 キューブ",
        "home.card.5.desc": "プロフェッサーキューブを解く",
        "home.help": "使い方",
        "home.version": "バージョン {version}",
        "home.settings": "設定",

        "theme.auto": "自動",
        "theme.light": "ライト",
        "theme.dark": "ダーク",

        "settings.title": "設定",
        "settings.theme": "テーマ",
        "settings.language": "言語",
        "settings.about": "アプリについて",
        "settings.about_tagline": "2×2 / 3×3 / 4×4 / 5×5 キューブのスマートソルバー",

        "help.title": "使い方",
        "help.close": "閉じる",
        "help.select.title": "キューブを選ぶ",
        "help.select.body":
            "ホーム画面のカードから 2 / 3 / 4 / 5 キューブを選びます"
            "（横向き 1×4、縦向き 2×2）。\n"
            "カードをタップすると入力ページへ移動します。下の「使い方」でいつでも戻れます。",
        "help.input.title": "配置を入力",
        "help.input.body":
            "セルをタップして各面の色を入力します：先に6色セレクターで色を選び、\n"
            "セルを順にタップします。「ランダム」でスクランブルを読み込んで試せます。\n"
            "入力後は「検証」で配置が正しいか確認できます。",
        "help.solve.title": "ワンタップで解く",
        "help.solve.body":
            "入力が終わったら「解く」を押すと、バックグラウンドで解法を計算します。\n"
            "現在の段階と進捗をリアルタイム表示し、いつでもキャンセルできます。",
        "help.playback.title": "3D 再生",
        "help.playback.body":
            "解法を 3D ビューで順番に再生します：ドラッグで回転、"
            "スクロール / ピンチでズーム。\n"
            "前へ / 次へ / 自動再生 / 最後へジャンプに対応し、"
            "再生速度と停止時間も調整できます。",
        "help.demo.title": "チュートリアル",
        "help.demo.body":
            "目次には階数ごとの標準的な手順を収録しています：2×2 レイヤー法、"
            "3×3 七手順法、\n4×4 / 5×5 縮約法。5×5 は 4×4 との違いに注目します——\n"
            "センターは 3×3（固定センターあり）で、"
            "各エッジは中エッジ + 2 ウィングの3つで構成されます。",
        "help.theme.title": "テーマ",
        "help.theme.body":
            "ホーム画面から「設定」を開き、自動 / ライト / ダーク を選べます。\n"
            "自動はシステム（Windows / Android）の明暗設定に従います。",
        "help.notation.title": "色と記号",
        "help.notation.body":
            "6色は固定です：上が黄、下が白、前が青、後ろが緑、左が橙、右が赤。\n"
            "記号：R L U D F B は外層を回し、' は反時計回り、2 は 180° を表します；\n"
            "小文字（r u など）はワイド（複数層を同時に回す）で、"
            "4×4 / 5×5 の縮約法でよく使います。",
        "help.algo.title": "解法のしくみ（上級）",
        "help.algo.body":
            "2×2 と 3×3 は二段階アルゴリズム（Kociemba）で手数を抑えます；\n"
            "4×4 と 5×5 は縮約法：センターを揃え、エッジをペアリングし、"
            "最後に 3×3 として解きます。\n"
            "注：5×5 の非常に深いスクランブルでは、エッジのペアリング段階で\n"
            "完全な解法を保証できない場合があります。その際は誤った解法ではなく"
            "失敗を通知します。",

        "input.back": "← 戻る",
        "input.title": "入力 {n}×{n}",
        "input.demo": "デモ",
        "input.face": "面：{face} ({code})",
        "input.pick": "スポイト",
        "input.fill": "面を塗る",
        "input.undo": "元に戻す",
        "input.redo": "やり直す",
        "input.prev": "{arrow} 前へ",
        "input.next": "{arrow} 次へ",
        "input.twist": "回す",
        "input.random": "ランダム",
        "input.scramble": "スクランブルを貼り付け",
        "input.scramble.hint": "例: R U R' U' または R,U,R',U'",
        "input.scramble.ok": "適用",
        "input.scramble.loaded": "スクランブルを適用しました（{k} 手）",
        "input.scramble.empty": "スクランブルを入力してください",
        "input.scramble.error": "認識できない手順: {tok}",
        "input.clear": "クリア",
        "input.check": "検証",
        "input.solve": "解く",
        "input.missing": "未入力: {list}",
        "input.valid": "状態は有効 ✓",
        "input.filled": "面 {face} を {col} で塗りました",
        "input.already": "面 {face} はすでに {col} です",
        "input.undone": "元に戻しました",
        "input.redone": "やり直しました",
        "input.picked": "{col} をスポイトしました。続けて入力できます",
        "input.random_loaded": "ランダム配置を読み込みました（{k} 手スクランブル）",
        "input.cleared": "クリアしました",
        "input.resumed": "前回の配置を読み込みました。「解く」で前回の解法を再利用できます",
        "input.clear.title": "クリアの確認",
        "input.clear.msg": "入力した色をすべてクリアしますか？",
        "input.cancel": "キャンセル",
        "input.clear.ok": "クリアする",

        "solving.title": "求解中…",
        "solving.preparing": "準備中",
        "solving.cancel": "キャンセル",
        "solving.cancelling": "キャンセル中…",
        "solving.pairing": "エッジをペアリング {done}/12",
        "solving.depth": "センター探索の深さ {depth}",

        "playback.total": "全 {k} 手",
        "playback.step": "{i}/{t} 手目",
        "playback.start": "最初へ",
        "playback.prev": "前へ",
        "playback.play": "再生",
        "playback.pause": "一時停止",
        "playback.next": "次へ",
        "playback.end": "最後へ",
        "playback.reset_view": "視点を戻す",
        "playback.back": "入力へ戻る",
        "playback.speed": "速度",
        "playback.hold": "停止時間",

        "demo.back_to_menu": "← 目次",
        "demo.no_image": "画像なし",
        "demo.switch": "階数を切り替え",
        "demo.playing": "再生中…",
        "demo.case": "ケース：{name}",
        "demo.step_n": "ステップ{n}",
        "demo.title_step": "ステップ{n} · {title}（{i}/{total}）",
        "demo.menu_step": "ステップ{n} · {title}",
        "demo.mode.menu.2": "2×2 · チュートリアル一覧",
        "demo.mode.menu.3": "3×3 · チュートリアル一覧",
        "demo.mode.menu.4": "4×4 · チュートリアル一覧",
        "demo.mode.menu.5": "5×5 · チュートリアル一覧",
        "demo.mode.title.2": "2×2 · レイヤー法",
        "demo.mode.title.3": "3×3 · 七手順法",
        "demo.mode.title.4": "4×4 · 縮約法",
        "demo.mode.title.5": "5×5 · 縮約法",

        "twist.done": "完了",
        "twist.lock_on": "視点固定：オン",
        "twist.lock_off": "視点固定：オフ",
        "twist.wide_on": "ワイド：オン",
        "twist.wide_off": "ワイド：オフ",
        "twist.hint_lock_on": "視点固定オン：キューブをドラッグして層を回します。ズームはロック",
        "twist.hint_lock_off": "視点固定オフ：ドラッグで視点回転、スクロールでズーム",
        "twist.hint_wide": "（ワイドオン：外層を回すと内層も一緒に回ります）",
        "twist.congrats_title": "おめでとうございます！",
        "twist.congrats_body": "キューブを完成させました！",
        "twist.congrats_ok": "続ける",
    },
}


class Translator(EventDispatcher):
    """持有当前语言并提供 tr()。语言变更时派发 on_language。"""

    lang = StringProperty(LANG_ZH)

    __events__ = ("on_language",)

    def tr(self, key, **kwargs):
        table = CATALOG.get(self.lang, {})
        text = table.get(key)
        if text is None:
            text = CATALOG[LANG_EN].get(key)
        if text is None:
            text = CATALOG[LANG_ZH].get(key)
        if text is None:
            return key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def on_language(self, *args):
        pass


_translator = Translator()


# ===== 模块级便捷接口 =====
def translator() -> Translator:
    return _translator


def tr(key, **kwargs) -> str:
    return _translator.tr(key, **kwargs)


def current_language() -> str:
    return _translator.lang


def set_language(lang: str):
    if lang in LANGUAGES:
        _translator.lang = lang


def cycle_language(lang: str = None) -> str:
    """返回下一个语言代码（循环 zh -> en -> ja -> zh）。"""
    cur = lang or _translator.lang
    try:
        idx = LANGUAGES.index(cur)
    except ValueError:
        idx = 0
    return LANGUAGES[(idx + 1) % len(LANGUAGES)]


def language_name(lang: str) -> str:
    return LANGUAGE_NAMES.get(lang, lang)


# ===== 系统语言检测与持久化 =====
def system_language() -> str:
    """尽力检测系统语言；无法判断时回退 English。"""
    locales = []
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var)
        if val:
            locales.append(val)
    try:
        import locale as _locale
        loc = None
        try:
            loc = _locale.getlocale()[0]
        except Exception:
            loc = None
        if not loc:
            loc = _locale.getdefaultlocale()[0]
        if loc:
            locales.append(loc)
    except Exception:
        pass

    for raw in locales:
        low = str(raw).lower()
        if low.startswith("zh"):
            return LANG_ZH
        if low.startswith("ja"):
            return LANG_JA
        if low.startswith("en"):
            return LANG_EN
    return LANG_EN


def load_saved_language():
    """读取上次保存的语言；不存在时返回 None。"""
    try:
        from app.prefs import get
        lang = get(_PREFS_KEY)
        return lang if lang in LANGUAGES else None
    except Exception:
        return None


def save_language(lang: str):
    try:
        from app.prefs import set as _set
        _set(_PREFS_KEY, lang)
    except Exception:
        pass


def init() -> str:
    """初始化语言：已保存优先，否则跟随系统。返回最终语言。"""
    lang = load_saved_language() or system_language()
    _translator.lang = lang
    return lang
