"""Audit every selectable puzzle using fresh input states and complete replay.

Each sample runs in an isolated process with a hard timeout. Results are
checkpointed per sample so a failed or interrupted audit remains reviewable.
This checks the implemented model/solver; it is not proof of all-state coverage
or a validation of a physical puzzle's mechanism.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Some solver progress messages import the Kivy translator. Keep Kivy from
# parsing this audit tool's arguments; no window or application is started.
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

NAMES = {
    'cube': '普通魔方', 'pyraminx': '金字塔', 'mastermorphix': '粽子',
    'skewb': '斜转', 'dino': '恐龙／格子', 'megaminx': '五魔方',
    'moyu': '魔塔', 'mirror': '镜面', 'fto': '转面八面体',
    'football': '足球', 'icosahedron': '二十面体', 'war_drum': '战鼓',
    'pentahedron': '五面体', 'eight_petals': '八叶花', 'clover': '四叶草',
    'blossom': '繁花五魔方', 'square1': 'SQ1', 'void_cube': '空心三阶',
    'void_tower': '空心魔塔', 'mirror_tower': '镜面魔塔',
    'axis': '变形金刚', 'pandora': '潘多拉', 'windmill': '风火轮',
    'fisher': '移棱', 'ivy': '枫叶',
}


def catalogue():
    """Read catalogue constants without importing Kivy or launching a window."""
    path = ROOT / 'ui/screens/irregular_directory_screen.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    env = {'tuple': tuple, 'range': range}
    allowed = {'PUZZLES', 'SPECIAL_PUZZLES', 'ORDERS', 'IMPLEMENTED_ORDERS'}
    for node in tree.body:
        assignment = (isinstance(node, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id in allowed for t in node.targets))
        update = (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                  and isinstance(node.value.func, ast.Attribute)
                  and isinstance(node.value.func.value, ast.Name)
                  and node.value.func.value.id == 'ORDERS'
                  and node.value.func.attr == 'update')
        if assignment or update:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), env)
    orders = {**env['ORDERS'], **env['IMPLEMENTED_ORDERS']}
    cases = [('cube', n) for n in range(2, 15)]
    for kind in env['PUZZLES'] + env['SPECIAL_PUZZLES']:
        cases.extend((kind, n) for n in orders.get(kind, (3,)))
    return sorted(set(cases), key=lambda c: (c[1], c[0]))


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt==5:
                raise
            # Windows preview/indexing can briefly hold a destination open.
            time.sleep(0.05)


class Deadline:
    def __init__(self, seconds):
        self.at = time.perf_counter() + seconds

    def is_set(self):
        return time.perf_counter() >= self.at


def cover_generators(cube, seed):
    from cube.polyhedral import Move
    rng = random.Random(seed ^ 0xA11D17)
    atoms = list(cube.moves())
    rng.shuffle(atoms)
    for atom in atoms:
        spec = cube.geometry.spec
        cube.apply_move(Move(atom.axis, atom.layer,
                             spec.step(atom.axis)*rng.randrange(1,spec.order(atom.axis))))
    return len(atoms)


def make_sample(kind, n, seed, cover=False):
    if kind == 'square1':
        from cube.square1 import Square1Cube
        cube = Square1Cube.solved().scramble(20, seed)
        return cube.entered(), 60
    if kind == 'mirror_tower':
        from cube.mirror_tower import MirrorTowerCube
        from solver.polyhedral import scramble
        cube = MirrorTowerCube.solved()
        coverage = cover_generators(cube,seed) if cover else 0
        moves = scramble(cube, 30, seed)
        return cube.entered(), coverage+len(moves)
    if kind in ('cube', 'mastermorphix', 'mirror', 'axis', 'pandora', 'windmill', 'fisher'):
        if kind == 'cube':
            if n == 2:
                from cube.cube2 import Cube2
                cube = Cube2.solved()
            elif n == 3:
                from cube.cube3 import Cube3
                cube = Cube3.solved()
            elif n == 4:
                from cube.cube4 import Cube4
                cube = Cube4.solved()
            elif n == 5:
                from cube.cube5 import Cube5
                cube = Cube5.solved()
            else:
                from cube.cube_n import CubeN
                cube = CubeN.solved(n)
        elif kind == 'mastermorphix':
            from cube.mastermorphix import MastermorphixCube
            cube = MastermorphixCube.solved(n=n)
        elif kind == 'mirror':
            from cube.mirror import MirrorCube
            cube = MirrorCube.solved(n=n)
        else:
            from cube.shape_cube import AxisCube, PandoraCube, WindmillCube, FisherCube
            cube = {'axis': AxisCube, 'pandora': PandoraCube,
                    'windmill': WindmillCube, 'fisher': FisherCube}[kind].solved()
        from cube.scramble import random_scramble
        moves = random_scramble(n, random.Random(seed), kind)
        if cover:
            from cube.scramble import _layers_for, _token
            rng = random.Random(seed ^ 0xA11D17)
            coverage = [_token(face,width,rng.choice(('',"'",'2')))
                        for face in 'URFDLB' for width in _layers_for(n,kind)]
            rng.shuffle(coverage)
            moves = coverage + moves
        cube.apply_moves(moves)
        if kind == 'cube':
            # Paint a fresh cube, discarding the scrambled cubies' home labels.
            from cube.conversion import cubies_to_facelets, facelets_to_cubies
            cubies = facelets_to_cubies(cubies_to_facelets(cube.cubies, n), n)
            if n == 4:
                # Match InputScreen._write_cube(), which reconstructs the
                # four-colour centre homes used by the 4x4 centre solver.
                from solver.solver4 import _rebuild_center_homes
                _rebuild_center_homes(cubies)
            cube = type(cube)(cubies, n) if n >= 6 else type(cube)(cubies)
        else:
            cube = cube.clone()
        return cube, len(moves)
    from cube.polyhedral import PolyhedralPuzzle
    from solver.polyhedral import scramble
    cube = PolyhedralPuzzle.solved(kind, n)
    coverage = cover_generators(cube,seed) if cover else 0
    turns = 30 if n <= 3 else 30 + 2*n
    moves = scramble(cube, turns, seed)
    return cube.entered(), coverage+len(moves)


def worker(args):
    kind, text_n = args.worker.split(':')
    n = int(text_n)
    record = {'kind': kind, 'name': NAMES[kind], 'order': n, 'seed': args.seed,
              'status': 'running', 'phase': 'construct', 'steps': None,
              'sample_mode':('incomplete' if args.incomplete else
                             ('all_generators' if args.cover_generators else 'random'))}
    started = time.perf_counter()
    solve_started = None
    write_json(args.output, record)
    try:
        cube, turns = make_sample(kind, n, args.seed,args.cover_generators)
        if args.incomplete:
            if kind=='square1':
                cube.slots=cube.slots[:-1]
            elif kind=='mirror_tower':
                cube.pieces.pop(next(iter(cube.pieces)))
            elif hasattr(cube,'cubies'):
                cube.cubies.pop(next(iter(cube.cubies)))
            else:
                cube.colors[0]=-1
        record.update(scramble_steps=turns, initial_solved=cube.is_solved(),
                      setup_seconds=round(time.perf_counter()-started, 3), phase='solve')
        write_json(args.output, record)
        token = Deadline(max(1, args.timeout-5))

        def progress(*payload):
            record['progress'] = str(payload)[:500]
            # Do not checkpoint every inner search-node callback.
            if time.perf_counter()-progress.last > 1:
                progress.last = time.perf_counter()
                write_json(args.output, record)
        progress.last = time.perf_counter()

        solve_started = time.perf_counter()
        if kind == 'square1':
            from solver.square1 import solve_square1
            moves = solve_square1(cube, token.is_set, progress)
        elif kind == 'mirror_tower':
            from solver.polyhedral import solve_polyhedral
            moves = solve_polyhedral(cube, token.is_set, progress)
        else:
            from services.solve_service import SolveService
            results = []
            SolveService()._run(cube, results.append, progress, token)
            result = results[0]
            if not result.success:
                raise RuntimeError(result.message)
            moves = result.moves
        moves = list(moves)
        if args.incomplete:
            record.update(status='unexpected_accept',phase='complete',steps=len(moves),
                          error='Incomplete input returned a solution',
                          solve_seconds=round(time.perf_counter()-solve_started,3))
            write_json(args.output,record)
            return
        record.update(steps=len(moves), solve_seconds=round(time.perf_counter()-solve_started, 3),
                      phase='replay')
        write_json(args.output, record)
        replay_started = time.perf_counter()
        replay = cube.entered() if hasattr(cube, 'entered') else cube.clone()
        for move in moves:
            replay.apply_move(move)
        replay_solved = replay.is_solved()
        record.update(replay_solved=replay_solved,
                      replay_seconds=round(time.perf_counter()-replay_started, 3),
                      status='pass' if replay_solved else 'replay_failure', phase='complete')
        # Store the returned solution for reproducing mismatched replay.
        record['solution'] = [([m.axis, m.layer, m.amount] if hasattr(m, 'layer') else
                               [m.axis, m.amount]) if hasattr(m, 'axis') else m for m in moves]
    except Exception as exc:
        timed_out=bool(solve_started and time.perf_counter()-solve_started>=args.timeout-5)
        record.update(status=('timeout' if timed_out else
                              ('rejected' if args.incomplete else 'error')),
                      error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
        if solve_started:
            record['solve_seconds'] = round(time.perf_counter()-solve_started, 3)
    record['total_seconds'] = round(time.perf_counter()-started, 3)
    write_json(args.output, record)


def run_sample(output_dir, kind, n, seed, timeout, cover=False, incomplete=False):
    name = f'{kind}-{n}-seed-{seed}'
    path = output_dir / 'samples' / f'{name}.json'
    log = output_dir / 'logs' / f'{name}.log'
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', f'{kind}:{n}',
               '--seed', str(seed), '--timeout', str(timeout), '--output', str(path)]
    if cover:
        command.append('--cover-generators')
    if incomplete:
        command.append('--incomplete')
    started = time.perf_counter()
    with log.open('w', encoding='utf-8') as stream:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=timeout+15)
            row = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            if row.get('status', 'running') == 'running':
                row.update(status='crash', error=f'worker exit {result.returncode}')
        except subprocess.TimeoutExpired:
            row = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            row.update(status='timeout', error=f'Hard worker timeout after {timeout+15}s')
    row.update(kind=kind, name=NAMES[kind], order=n, seed=seed,
               wall_seconds=round(time.perf_counter()-started, 3), log=str(log))
    write_json(path, row)
    return row


def reports(output_dir, rows, jobs, timeout):
    rows.sort(key=lambda r: (r['kind'], r['order'], r['seed']))
    write_json(output_dir/'results.json', rows)
    with (output_dir/'results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        columns = ['name','kind','order','seed','status','scramble_steps','steps',
                   'solve_seconds','replay_seconds','wall_seconds','error']
        writer = csv.DictWriter(stream, columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    grouped = {}
    for row in rows:
        grouped.setdefault((row['kind'],row['order']), []).append(row)
    if rows and all(r.get('sample_mode')=='incomplete' for r in rows):
        rejected=sum(r['status']=='rejected' for r in rows)
        lines=['# 不完整录入检查','',f'{len(rows)} 个类型／阶数输入，{rejected} 个被求解入口拒绝。','',
               '普通及块形魔方删除一个块，多面体将一个贴纸置为未录入，SQ1 删除一个角度槽位。'
               '这只检查输入完整性，不替代排列奇偶性、块朝向等全部非法状态验证。','',
               '| 类型 | 阶数 | 结果 | 返回信息 |','|---|---:|---|---|']
        for row in sorted(rows,key=lambda r:(list(NAMES).index(r['kind']),r['order'])):
            error=row.get('error','').replace('|','/').replace('\n',' ')
            lines.append(f'| {row["name"]} | {row["order"]} | {row["status"]} | {error} |')
        (output_dir/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        return
    passed = sum(r['status']=='pass' for r in rows)
    modes_present = {r.get('sample_mode','random') for r in rows}
    if modes_present <= {'all_generators'}:
        mode_note = '本报告只含**全部转轴／切层覆盖打乱**样本。'
    elif modes_present <= {'random'}:
        mode_note = '本报告只含**随机打乱**样本。'
    else:
        mode_note = ('本报告同时含两种打乱口径：**随机打乱**与**全部转轴／切层覆盖打乱**。'
                     '两者在表中分行标注，不合并为同一项步数范围。')
    lines = ['# 魔方求解审计', '', f'生成时间：{datetime.now().isoformat(timespec="seconds")}', '',
             f'检查 {len(grouped)} 种类型与阶数组合，共 {len(rows)} 个合法打乱样本，'
             f'{passed} 个完整回放通过。', '',
             f'Windows 桌面 Python，最多 {jobs} 个独立进程并行；每样本求解预算约 {timeout-5:g} 秒，'
             f'进程硬上限 {timeout+15:g} 秒。并行桌面耗时不代表手机性能。', '',
             '输入状态重建后才调用软件实际求解入口，求解不获取打乱动作。'
             '普通魔方额外从贴纸颜色重建，异形保留录入所需块形和朝向。'
             '每个返回动作都独立回放，最后用该模型的还原判定核对。', '',
             '步数按返回动作项统计（与播放器一致）；半圈、合法大转角算一步，'
             'SQ1 上下层转动和切割分别算一步。范围只表示本次样本，不能证明所有状态都可解。'
             '超时表示预算内未拿到解，不表示数学上不可解。', '',
             mode_note, '',
             '部分缩短步骤的搜索带有时间预算，同一状态的步数可能随设备速度和并发负载略有变化。', '',
             '| 类型 | 阶数 | 回放通过／样本 | 步数范围（中位数） | 求解耗时（秒） | 异常 |',
             '|---|---:|---:|---:|---:|---|']
    mode_names = {'random': '随机', 'all_generators': '全轴／切层', 'incomplete': '不完整'}
    for (kind,n), sample_rows in sorted(grouped.items(), key=lambda item:(list(NAMES).index(item[0][0]),item[0][1])):
        by_mode = {}
        for row in sample_rows:
            by_mode.setdefault(row.get('sample_mode','random'), []).append(row)
        for mode in sorted(by_mode, key=lambda m:(m!='random', m)):
            mode_rows = by_mode[mode]
            good = [r for r in mode_rows if r['status']=='pass']
            def span(key):
                values = [r[key] for r in good if key in r]
                if not values:
                    return '—'
                return f'{min(values):g}–{max(values):g}' if min(values)!=max(values) else f'{values[0]:g}'
            bad = sorted({r['status']+': '+r.get('error','回放未还原') for r in mode_rows if r['status']!='pass'})
            issue = '; '.join(bad).replace('|','/').replace('\n',' ') or '—'
            step_text=span('steps')
            if good:
                step_text+=f'（{statistics.median(r["steps"] for r in good):g}）'
            label = f'{n}（{mode_names.get(mode,mode)}）' if len(by_mode)>1 else n
            lines.append(f'| {NAMES[kind]} | {label} | {len(good)}/{len(mode_rows)} | {step_text} | {span("solve_seconds")} | {issue} |')
    lines.extend(['', '原始结果：`results.json`、`results.csv`；每个样本的输入种子、返回动作、'
                  '进度与错误堆栈在 `samples/`，控制台日志在 `logs/`。'])
    (output_dir/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker')
    parser.add_argument('--seed', type=int, default=20261012)
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--cover-generators', action='store_true')
    parser.add_argument('--incomplete', action='store_true')
    parser.add_argument('--output', default='reports/solver-audit/2026-10-12')
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    output_dir = Path(args.output).resolve()
    (output_dir/'samples').mkdir(parents=True, exist_ok=True)
    (output_dir/'logs').mkdir(parents=True, exist_ok=True)
    cases = catalogue()
    if args.case:
        requested = {(kind,int(n)) for kind,n in (c.split(':') for c in args.case)}
        cases = [c for c in cases if c in requested]
        if requested-set(cases):
            raise ValueError(f'Cases absent from catalogue: {requested-set(cases)}')
    tasks = [(kind,n,args.seed+i) for i in range(args.samples) for kind,n in cases]
    rows = []
    print(f'AUDIT {len(cases)} configurations, {len(tasks)} samples, {args.jobs} workers',flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_sample,output_dir,*task,args.timeout,
                               args.cover_generators,args.incomplete) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            compact = {key:row.get(key) for key in ('kind','order','seed','status','steps','solve_seconds','error')}
            print(f'[{len(rows)}/{len(tasks)}] '+json.dumps(compact,ensure_ascii=True),flush=True)
            try:
                reports(output_dir,rows,args.jobs,args.timeout)
            except PermissionError as exc:
                print(f'Intermediate report retry deferred: {exc}',flush=True)
    reports(output_dir,rows,args.jobs,args.timeout)
    print(f'REPORT {output_dir / "report.md"}',flush=True)


if __name__ == '__main__':
    main()
