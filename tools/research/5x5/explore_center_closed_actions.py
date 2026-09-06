"""探索"中心闭合动作子空间"（精简可行版）。

中心闭合宏 = color_off 起点0→终点0、固定面心保持、对棱非平凡。
只生成：外层动作 + `2X A 2X'`（A 为长度 0..max_outer 的纯外层序列）。
用 compact 状态验证（不克隆整立方体）。宏级 beam 搜索装配目标棱。

用法：python explore_center_closed_actions.py <max_outer> <depth> <beam> [lengths]
"""

import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import random

from cube.cube5 import Cube5

from solver.edge5.compact_state import (
    MOVES,
    color_off,
    matched,
    state_of,
    step,
    work_paired,
)
from solver.edge5.positions import SLOT_NAMES, color_pair_of_slot
from solver.edge5.state import face_colors

_OUTER = [m for m in MOVES if not m[:1].isdigit()]
_WIDE = [m for m in MOVES if m[:1].isdigit()]


def _inv(mv):
    if mv.endswith("'"):
        return mv[:-1]
    if mv.endswith("2"):
        return mv
    if mv.endswith("3"):
        return ""
    return mv + "'"


_IDENT = lambda st: (st.middle == tuple(range(len(st.middle)))
                     and st.wing == tuple(range(len(st.wing))))


def build_macro_library(max_outer):
    """返回 (宏列表[每项为动作元组], 元信息)。用 compact 状态验证。"""
    start = state_of(Cube5.solved())
    lib = []

    def _check(seq):
        st = start
        for mv in seq:
            st = step(st, mv)
        return color_off(st) == 0 and not _IDENT(st)

    # 外层动作
    for mv in _OUTER:
        lib.append((mv,))
    # 宽层闭合对
    seqs = [[]]
    for _ in range(max_outer):
        newseqs = []
        for s in seqs:
            for o in _OUTER:
                if s and _inv(s[-1]) == o:
                    continue
                newseqs.append(s + [o])
        seqs.extend(newseqs)
    for w in _WIDE:
        wq = _inv(w)
        for A in seqs:
            seq = tuple([w] + A + [wq])
            if _check(seq):
                lib.append(seq)
    return lib


def _scramble(cube, length, rng):
    prev = None
    for _ in range(length):
        mv = rng.choice(MOVES)
        while prev and mv.lstrip("0123456789")[0] == prev.lstrip("0123456789")[0]:
            mv = rng.choice(MOVES)
        cube.apply_move(mv)
        prev = mv


def run_search(cube, target, work_slot, lib, depth, beam_width):
    from solver.edge5.compact_state import target_home_slot

    original = cube.clone()
    tgt_home = target_home_slot(original, target)
    if tgt_home is None:
        return None, 0
    start = state_of(original)
    beam = [(start, ())]
    nodes = 0
    for _depth in range(depth):
        nxt = []
        for st, path in beam:
            m = matched(st, tgt_home, work_slot)
            co = color_off(st)
            if m == 3 and co == 0 and work_paired(st, work_slot):
                return list(path), nodes
            for macro in lib:
                nodes += 1
                ns = st
                for mv in macro:
                    ns = step(ns, mv)
                np = path + macro
                m2 = matched(ns, tgt_home, work_slot)
                co2 = color_off(ns)
                score = (1 if (m2 == 3 and co2 == 0 and work_paired(ns, work_slot)) else 0,
                         m2, -co2, -len(np))
                nxt.append((score, ns, np))
                if m2 == 3 and co2 == 0 and work_paired(ns, work_slot):
                    return list(np), nodes
        # 去重 + beam
        seen = {}
        for score, st, path in nxt:
            key = st.key
            if key in seen and seen[key][0] >= score:
                continue
            seen[key] = (score, st, path)
        pool = sorted(seen.items(), key=lambda kv: kv[1][0], reverse=True)
        beam = [(item[1][1], item[1][2]) for item in pool[:beam_width]]
        if not beam:
            return None, nodes
    return None, nodes


def main():
    max_outer = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    beam_width = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    lengths = [int(x) for x in (sys.argv[4].split(",") if len(sys.argv) > 4 else ["5"])]

    t0 = time.time()
    lib = build_macro_library(max_outer)
    print(f"宏库({max_outer}) = {len(lib)} 条, 构建时间 {time.time()-t0:.1f}s")
    from collections import Counter
    print("宏长度分布:", dict(sorted(Counter(len(m) for m in lib).items())))

    for length in lengths:
        rng = random.Random(42)
        ok = 0
        total = 10
        t1 = time.time()
        for i in range(total):
            cube = Cube5.solved()
            _scramble(cube, length, rng)
            fc = face_colors(cube)
            work_slot = rng.choice(SLOT_NAMES)
            target = color_pair_of_slot(work_slot, fc)
            path, nodes = run_search(cube, target, work_slot, lib, depth, beam_width)
            if path is not None:
                ok += 1
        print(f"len={length}  success={ok}/{total}  耗时{time.time()-t1:.1f}s")


if __name__ == "__main__":
    main()
