"""Export the same original text/formulas shown in the in-app teaching book."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('KIVY_NO_ARGS','1')
from candidate_puzzles import REQUESTED
from demo.expanded_curriculum import chapters
from demo.expanded_tutorials import tutorial,lessons
from demo.cases import localized


def main():
    lines=['# 新增魔方原创分步教程','',
           '本教材按本项目的 32 个实际模型编写，与应用内“原创分步教程”的章节和三维案例对应。',
           '每款含机构识别、主体处理、余块工具和逐面验收四章。公式的起始状态必须在三维案例中核对；完整还原演示则从独立打乱状态求解。',
           '三块循环工具由合法转层推导并检查完整作用范围；核心公式同样按块位和方向检查，不转载外部教程或链接。','']
    inventory=[]
    for entry in REQUESTED:
        lines.extend([f'## {entry.name}','',tutorial(entry.kind).intro,''])
        units=chapters(entry.kind)
        for chapter in units:
            lines.extend([f'### {chapter.title}','','**识别**：'+chapter.recognize,''])
            lines.extend(f'{i}. {action}' for i,action in enumerate(chapter.actions,1))
            lines.extend(['','**完成条件**：'+chapter.done,'','**容易出错**：'+chapter.pitfall,''])
        count=0;cycles=0
        for step in lessons(entry.kind,entry.n):
            lines.extend([f'### {localized(step["title"],"zh")}','',localized(step['desc'],'zh'),''])
            for case in step['cases']:
                lines.extend(['**'+localized(case['name'],'zh')+'**','','`'+localized(case['text'],'zh')+'`','',localized(case['tip'],'zh'),''])
                count+=1;cycles+=bool(case.get('original'))
        inventory.append(dict(kind=entry.kind,name=entry.name,chapters=len(units),examples=count,
                              isolated_cycles=cycles,external_links=False))
    target=Path('docs/expanded-original-tutorials.md');target.write_text('\n'.join(lines),encoding='utf-8')
    out=Path('reports/demo-audit/2026-10-24');out.mkdir(parents=True,exist_ok=True)
    (out/'original-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    print(dict(models=len(inventory),chapters=sum(r['chapters'] for r in inventory),examples=sum(r['examples'] for r in inventory),
               isolated_cycles=sum(r['isolated_cycles'] for r in inventory),bytes=target.stat().st_size))


if __name__=='__main__':main()
