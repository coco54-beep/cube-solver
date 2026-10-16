"""Labels shared by the algorithm library and timer practice screens."""
from app.i18n import current_language

TEXT = {
    'title': ('进阶公式库', 'Advanced algorithms', '上級公式ライブラリ'),
    'practice': ('公式练习', 'Practice', '公式練習'),
    'practice_help': ('练习说明', 'Practice help', '練習の説明'),
    'practice_ready': ('准备', 'Ready', '準備'),
    'practice_running': ('计时中', 'Timing', '計測中'),
    'practice_stopped': ('已记录', 'Recorded', '記録済み'),
    'practice_assisted': ('已看答案 · 不计成绩', 'Assisted · Unranked', '解答表示済み・集計対象外'),
    'practice_stats': ('{count} 次 · 最快 {best} · ao5 {ao5} · ao12 {ao12}', '{count} solves · Best {best} · ao5 {ao5} · ao12 {ao12}', '{count}回 · 最速 {best} · ao5 {ao5} · ao12 {ao12}'),
    'search': ('搜索编号、情况或公式', 'Search cases, patterns or algorithms', '番号・形・公式を検索'),
    'source': ('来源：SpeedCubeDB', 'Source: SpeedCubeDB', '出典：SpeedCubeDB'),
    'count': ('{count} 个情况 · 第 {page}/{pages} 页', '{count} cases · Page {page}/{pages}', '{count}ケース · {page}/{pages}ページ'),
    'empty': ('没有符合条件的情况', 'No matching cases', '該当するケースがありません'),
    'alternatives': ('备选 {count}', '{count} alternatives', '候補 {count}'),
    'unavailable': ('此条公式暂无法演示：{error}', 'Cannot animate this algorithm: {error}', 'この公式は再生できません：{error}'),
    'source_check': ('来源公式待核对：其切口或适用阶段未通过检查，暂不加入演示和练习。', 'Source algorithm needs review: its slice legality or stage prerequisites did not pass. Animation and practice are unavailable.', '出典の公式は切断条件または適用段階の確認待ちです。再生・練習の対象外です。'),
    'sets': ('选择公式集', 'Choose algorithm sets', '公式セットを選択'),
    'selected': ('已选 {sets} · {count} 题', '{sets} · {count} cases', '{sets} · {count}問'),
    'confirm': ('确定', 'Confirm', '決定'),
    'cancel': ('取消', 'Cancel', 'キャンセル'),
    'next': ('下一题', 'Next case', '次の問題'),
    'start': ('开始计时', 'Start timer', '計測開始'),
    'stop': ('停止计时', 'Stop timer', '計測停止'),
    'ready': ('先观察情况，准备好后开始计时', 'Inspect the case, then start when ready', 'ケースを観察し、準備できたら開始'),
    'running': ('计时中 · 再次点击或按空格停止', 'Timing · Tap again or press Space to stop', '計測中 · 再タップかスペースで停止'),
    'finished': ('已记录用时，可查看答案或进入下一题', 'Time recorded. Reveal the answer or try the next case', '記録しました。解答を確認するか次の問題へ'),
    'assisted': ('已查看答案，本题不计入成绩', 'Answer revealed. This attempt is excluded from results', '解答を表示したため、この問題は記録対象外です'),
    'answer': ('查看答案', 'Reveal answer', '解答を見る'),
    'replay': ('公式演示', 'Play algorithm', '公式を再生'),
    'scramble': ('打乱公式（从还原状态开始）', 'Scramble (start solved)', 'スクランブル（完成状態から）'),
    'hidden': ('答案已隐藏 · 可旋转模型观察', 'Answer hidden · Rotate the model to inspect', '解答は非表示 · モデルを回して観察できます'),
    'stats': ('完成 {count} 题 · 最快 {best} · 平均 {mean}', '{count} completed · Best {best} · Mean {mean}', '{count}問完了 · 最速 {best} · 平均 {mean}'),
    'number': ('第 {number} 题', 'Case {number}', '第{number}問'),
    'select_one': ('请至少选择一个公式集', 'Select at least one algorithm set', '公式セットを1つ以上選択してください'),
    'keys': ('计时：点击按钮；或松开空格开始、按下空格停止。计时不自动判断实物是否还原。', 'Tap the timer button, or release Space to start and press it to stop. Finish confirmation is manual.', 'ボタン、またはスペースを離して開始・押して停止。完成判定は手動です。'),
    'empty_pool': ('当前公式集没有可用题目', 'No playable cases in the selected sets', '選択したセットに出題可能なケースがありません'),
    'new': ('未学', 'New', '未学習'),
    'learning': ('学习中', 'Learning', '学習中'),
    'mastered': ('熟练', 'Mastered', '習得済み'),
    'all': ('全部情况', 'All cases', 'すべて'),
    'weak': ('薄弱优先', 'Weak cases', '苦手を優先'),
    'preferred': ('常用公式', 'Preferred algorithms', 'お気に入り'),
    'prefer_play': ('设为常用并演示', 'Use as preferred and play', 'お気に入りに設定して再生'),
    'progress_help': ('点击学习状态切换：未学 → 学习中 → 熟练', 'Tap learning status: New → Learning → Mastered', '学習状態をタップ：未学習 → 学習中 → 習得済み'),
    'averages': ('ao5 {ao5} · ao12 {ao12}', 'ao5 {ao5} · ao12 {ao12}', 'ao5 {ao5} · ao12 {ao12}'),
    'history': ('最近成绩', 'Recent results', '最近の記録'),
    'penalty_help': ('成绩可标记 OK / +2 / DNF；平均去掉一个最好和最差成绩', 'Mark OK / +2 / DNF. Averages drop the best and worst result', 'OK / +2 / DNFを設定。平均は最良・最悪を除外'),
    'generating': ('正在生成打乱…', 'Generating scramble…', 'スクランブルを生成中…'),
    'learning_status': ('学习状态', 'Learning status', '学習状態'),
}

PUZZLE_LABELS = {
    '2x2': ('二阶', '2×2', '2×2'), '3x3': ('三阶', '3×3', '3×3'),
    '4x4': ('四阶', '4×4', '4×4'), '5x5': ('五阶', '5×5', '5×5'),
    'SQ1': ('SQ1', 'Square-1', 'スクエア1'), 'Skewb': ('斜转', 'Skewb', 'スキューブ'),
    'Pyraminx': ('金字塔', 'Pyraminx', 'ピラミンクス'),
    'Megaminx': ('三阶五魔方', '3-layer Megaminx', '3段メガミンクス'),
}


def msg(key, **values):
    index = {'zh': 0, 'en': 1, 'ja': 2}.get(current_language(), 1)
    return TEXT[key][index].format(**values)


def puzzle_label(puzzle):
    return PUZZLE_LABELS[puzzle][{'zh': 0, 'en': 1, 'ja': 2}.get(current_language(), 1)]
