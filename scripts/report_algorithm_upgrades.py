"""Generate the reviewable report from completed, replay-checked samples."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'reports/algorithm-upgrades/2026-10-13'
NAMES={'cube':'普通','mastermorphix':'粽子','mirror':'镜面','axis':'变形金刚','fisher':'移棱',
       'windmill':'风火轮','square1':'SQ1','mirror_tower':'镜面魔塔','fto':'转面八面体',
       'skewb':'斜转','pyraminx':'金字塔','moyu':'魔塔','war_drum':'战鼓','blossom':'繁花',
       'dino':'恐龙／格子','clover':'四叶草','eight_petals':'八叶花','megaminx':'五魔方','football':'足球'}

def rows(name):return [json.loads(line) for line in (HERE/name).read_text().splitlines() if line]
def main():
    nxn=rows('nxn-final-certified.jsonl')
    assert {r['order'] for r in nxn}==set(range(6,18))
    audit=json.loads((HERE/'full-audit/results.json').read_text(encoding='utf-8'))
    assert len(audit)==90 and all(r['status']=='pass' for r in audit)
    lines=['# 2026-10-13 求解优化','',
        '普通 N 阶范围：**6–17 阶**。全目录 90 个类型／阶数组合的全轴全层打乱均完整回放通过；'
        '最终共享准备表版本另有 6–17 阶同输入、同三阶核心解的逐阶配对回放。','',
        '专项求解与演示测试 299 项通过；普通高阶／高阶粽子专项 25 项通过；'
        '五阶与候选方案回归 50 项通过。测试组有重叠，不把它们相加作为不同测试数量。','',
        '所有步数采用播放器动作计数，输入重建后求解，不读取打乱历史。'
        '这是模型的样本回放检查，不是全状态证明或实物机构认证。耗时来自桌面，'
        '基准期间有其他检查并行运行、缓存逐渐热起来，不能当成手机耗时或严格冷启动对比。','',
        '## 普通 N 阶','',
        '三种中心策略与原策略完整解比较；两条方案共享同一主体状态和准备动作数据。'
        '只有完整结果更短、仍然还原时才替换原方案。','',
        '| 阶数 | 原策略 | 当前 | 完整回放 |','|---:|---:|---:|---|']
    for r in nxn:lines.append(f"| {r['order']} | {r['before']['steps']} | {r['after']['steps']} | 通过 |")
    lines+=['','固定种子 20261013，全轴／全层覆盖；三阶核心搜索结果在两种方案之间复用，'
            '避免限时三阶搜索选到不同主体解干扰比较。数据：[nxn-final-certified.jsonl](nxn-final-certified.jsonl)。','',
            '## 粽子、镜面与三阶形变类','',
            '粽子、镜面按真实块身份比较更短准备动作，保持形状和朝向要求；'
            '形变三阶比较主体解与可见中心朝向的总长。普通五阶比较降阶与轨道法。','',
            '| 类型／阶数 | 样本种子 | 本次调用原解 | 当前 |','|---|---:|---:|---:|']
    for r in rows('additional.jsonl'):
        lines.append(f"| {NAMES[r['kind']]} {r['order']} | {r['seed']} | {r['before']} | {r['after']} |")
    lines+=['','数据：[additional.jsonl](additional.jsonl)。SQ1 和镜面魔塔有时间限制地比较两阶段总长；'
            '这组样例没有进一步省步，保留原解，不宣称全局最短。','',
            '## 足球与高阶五魔方','',
            '足球用带成本的成对翻棱，再比较两条完整解。相同 24 步打乱下：','',
            '| 类型／阶数 | 种子 | 改动前 | 当前 |','|---|---:|---:|---:|']
    before={(r['kind'],r['order'],r['seed']):r for r in rows('before.jsonl')}
    for r in rows('after-football.jsonl'):
        b=before.get((r['kind'],r['order'],r['seed']))
        if b:lines.append(f"| 足球 {r['order']} | {r['seed']} | {b['steps']} | {r['steps']} |")
    lines+=['','高阶五魔方以紧凑字节状态和批量评分运行相同原生搜索，并读取离线核对的 4–13 阶轨道方案。'
            '重点收益是耗时；相同 24 步打乱的十三阶样例由约 70.3 秒／45.7 秒变为 53.7 秒／20.6 秒。'
            '这不是严格隔离的性能测量，也不代表所有高阶状态。完整全轴打乱的十三阶仍有 15474 步，'
            '这一轮没有解决长解的全部问题。','',
            '搜索阶段的固定路径回归同时验证了批量与纯 Python 回退；完整阶段仍含限时规划，'
            '跨次运行步数可浮动，例如十三阶另一配对样例为 1350→1351 步。'
            '不能把“原生搜索路径一致”描述成“所有最终解完全一致”。','',
            '数据：[after-football.jsonl](after-football.jsonl)、[after-minx-plans.jsonl](after-minx-plans.jsonl)。','',
            '## 多面体完整动作压缩','',
            '对短动作建立完整贴纸作用的等价改写，随后消除回到相同可见状态的往返。'
            '最终仍在录入副本上完整回放；没有变短则保留原解。','',
            '| 类型／阶数 | 同次调用压缩前 | 压缩后 |','|---|---:|---:|']
    for r in rows('compaction.jsonl'):
        lines.append(f"| {NAMES[r['kind']]} {r['order']} | {r['before']} | {r['after']} |")
    lines+=['','五面体 4／5 阶此前的完整动作改写继续保留。候选按各轴真实周期去重，重复输入复用结果。'
            '它仍是限时搜索，固定打乱也会随机器负载浮动；去重没有稳定的省步比例。'
            '探索记录中五阶种子 13 曾从 484 波动到 593，不能把这条记录写成去重必然使步数下降。','',
            '## 二十面体离线公式','',
            '11 条核心关系缩短：三／五阶各 5 条翻棱关系由 51→49，五阶一条扭角关系由 176→174。'
            '核对每条完整核心作用与方向向量，并重新生成方向候选表；原核心资产单独保留。'
            '二阶 360 步关系和四阶关系这次未找到更短的等价改写，继续使用原公式。','',
            '二十面体三／五阶与普通五阶在最终数据生成后又完成独立全层回放。'
            '数据：[icosahedron-words.json](icosahedron-words.json)、[final-assets-audit/report.md](final-assets-audit/report.md)。','',
            '## 复核与 APK','',
            '[全目录回放报告](full-audit/report.md)。1.2.22 使用固定源码快照打包，'
            '包内核对与手机测试状态见 [Android 记录](../../android-test/1.2.22/report.md)。'
            '用户已取消 ADB 安装和手机测试；这次交付只包含桌面检查与 APK 打包。','',
            '目录内 nxn.jsonl、nxn-final.jsonl、nxn-paired.jsonl 和 after-prism.jsonl 是探索或中间版本记录，'
            '普通 N 阶验收使用 nxn-final-certified.jsonl。']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(HERE/'report.md')
if __name__=='__main__':main()
