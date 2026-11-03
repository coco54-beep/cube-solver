# Camouflage 3×3

## Mechanism and exterior

The WitEden Camouflage looks like a three-layer cube, but uses an asymmetric
bandaged 4×4 mechanism. Each axis groups mechanical cells as `(2,1,1)`;
the visible widths are `(2,1,2)`. The pivot lies at the first visible cut,
not the centre of the exterior cube. Physical boxes span `[-2,0,1,3]` on
each axis. This supplies the large square, thin rectangle and small square
panels visible on the real puzzle.

The implementation in `cube/cuboid.py` uses rigid piece rotations and rejects
cuts that split a bonded piece. `renderer/cuboid_view.py` draws those same
physical pieces, including exposed black cut walls. Input, turns, playback,
undo and session checkpoints retain both piece frames and colours.

The obsolete ordinary-3×3 approximation and its arbitrary exterior mapping
have been removed. Its saved sessions are rejected instead of reinterpreted
as the new mechanism.

## Current solver scope

App-generated scrambles can be restored from their retained legal move history;
the returned solution is replayed on the complete physical state before use.
Manual states use pattern distances, a precomputed endgame shell and a portfolio
of bounded legal searches. The orderings include total pattern distance,
maximum pattern distance and the number of misplaced physical pieces. The
short initial attempts switch to complete cost deepening when exhausted;
the application no longer stops automatically at 45 seconds. The complete
search caps its transposition cache at 50000 entries without dropping search
branches, uses an explicit stack and supports cancellation. Developer calls
can still request an explicit time budget. Each result is replayed on the original entered
model before it is returned. In the 2026-10-23 regression, all twelve 100-turn
scrambles reconstructed through visible six-view rectangles solved, including
four cases that previously timed out. See
`reports/solver-audit/2026-10-23/camouflage-deep-final-tests.xml`.
This is a complete finite-model search, rather than a fast constructive
algorithm for arbitrary manual Camouflage input. Its worst-case runtime can
be very large. Colour counts alone do not establish reachability. Cancellation
or an explicitly requested timeout is not a proof that an input is unsolvable.

Desktop UI exports are in `artifacts/camouflage/`. No Android build or device
verification was performed for this change.

## Search optimization (2026-10-24)

The unique eight-cell corner brick is now aligned first and held fixed during
search. Each bonded span stays on one side of the mechanical zero planes,
under all 24 proper rotations. Two complementary half-cube turns therefore
implement an actual legal whole rotation. After alignment, a slab turn which
moves the anchor can be expressed as its complementary slab turn in the
anchor frame. This quotients the 24 global holdings without losing reachable
solutions. Alignment is included in the returned physical move sequence;
the complete word is replayed on the original input.

Alignment uses at most four actual slab turns. The final twelve-case desktop
run took approximately 0.04–11.10 seconds per solve (median 1.52 seconds),
excluding visible-input matching. These timings are for those cases only.

An independent check covers every piece pose and legal slab transition,
and all 24 global holdings. Pattern distances remain the existing relaxed
distances; no new large table is needed. `camouflage-anchor-proof.json`
records the full complement and whole-rotation checks.

Different fast search orderings share normalization and bounded caches of
state estimates and verified endgame lookups. Their visited sets remain
separate, so a discarded fast-search branch cannot poison the complete
fallback. A byte-transform fast path also avoids per-edge generators, and
duplicate children are rejected before evaluating their pattern estimates.
The complete fallback keeps its cancellation support and has no automatic
time/depth/node failure cutoff.

Twelve 100-turn scrambles were rebuilt from visible six-view rectangles,
with no history, solved and independently replayed after this change.
These are desktop model checks, not a phone performance guarantee.
Records are in `reports/solver-audit/2026-10-24/camouflage-anchor-cases.json`.
No release package was generated.

## Deep-state shortcut (2026-10-24)

The solver now first searches modulo the always-legal half-cube rotation
group. All physical bricks stay in mechanical octants; the eight corner
owners determine the rigid frame of each octant. A tiny corner-group table
materializes normalization as actual half-cube turns. The remaining search
therefore avoids repeatedly exploring those corner arrangements.

An offline catalogue enumerates 68,040 projected setups and stores 2,295
distinct corner-preserving physical macros. Fifteen exact relaxed distance
tables guide this macro search. The three active files together occupy
683,891 bytes (about 0.68 MB); development needs NumPy/SymPy, runtime does
not. Rebuild with `tools/build_camouflage_octants.py`, followed by
`tools/build_camouflage_quotient_patterns.py`.

This is a bounded, nonoptimal shortcut: at most three seconds and 12,000
records, retaining 32 promising successors per expansion. Failure falls
through to the existing full search with its independent visited sets and
remaining shared deadline. No failure in this shortcut establishes that
the entered state is unreachable. Every accepted macro route is checked
against packed transitions and independently replayed on the entered cube.

The same twelve 100-turn visible-only reentries now took 0.047–1.985 seconds,
median 0.3205 seconds, versus the earlier median of 1.516 seconds. A 1,000-turn
case (seed 223) which previously exceeded 45 seconds completed in 1.765
seconds. These are desktop solve times excluding input matching, and the
solutions can use more moves. Seventeen of eighteen attempted end-to-end
cases completed; another 1,000-turn case (seed 2) was stopped by the audit
after 30 seconds while continuing full search. Arbitrary deep-state speed
is still not guaranteed.

The new catalogue was recomposed on 644,895 feasible piece poses; 100
independent half-cube scrambles checked corner normalization. Cancellation,
forced continuation to the original complete search, active bundle assets,
and 33 related existing regression cases passed. Reports:
`reports/solver-audit/2026-10-24/deep-camouflage-cases.json`,
`camouflage-octant-proof.json`, `deep-search-fallback-and-assets.json`,
and `deep-search-regression.xml`. No release was packaged or phone tested.

## References

- [Ladislav Dubravský: Bandaged 4x4s — WitEden Camouflage 3×3](https://ladislavdubravsky.wordpress.com/2015/04/04/bandaged-4x4s-witeden-camouflage-3x3/)
- [J. A. Storer: Camouflage Cube 3×3×3 and physical photographs](https://www.cs.brandeis.edu/~storer/JimPuzzles/ZPAGES/zzzCamouflageCube3x3x3.html)
# 镜面迷彩三阶（2026-11-02）

镜面系列新增 `mirror_camouflage_3`。它按本地 pCubes 的偏移外壳与三处选择性细分单独建模，不复用有色迷彩的尺寸布局。有色 `camouflage_3` 保留。

银色形状通过现有六视图录入：记录面片切缝、银色、黑色塑料与空位；有歧义时补充高亮面片的可见高度。匹配完成后可拧动或求解。求解使用独立的实体搜索、回形宏公式和原生回放，不依赖打乱历史。

详见 `reports/optimization/2026-11-02/bicube-mirror-floppy/README.md`。

