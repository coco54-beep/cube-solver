# Optional solver data

Some historical solver tables are also available as separate GitHub release
assets. Availability as a separate download does not mean that a table is
unused or safe to omit from an offline application.

Current data release: `data-v1.2.34`

| File | Size | Used by |
|---|---:|---|
| `twobar_table.bin` | 18 MB | Retired Two-Bar distance shell; excluded from new bundles |
| `bandaged_c_table.bin` | 25 MB | Retired Bandaged C distance shell; excluded from new bundles |
| `circle2_table.bin` | 41 MB | Retired Circle 2 distance shell; excluded from new bundles |
| `fused_table.bin` | 11 MB | Retired Fused distance shell; excluded from new bundles |

Download URL pattern:

`https://github.com/coco54-beep/cube-solver/releases/download/data-v1.2.34/<file>`

For source-based development, place downloaded files in `solver/data/`.
There is no production download UI or automatic private-directory lookup for
these files. Active tables are shipped locally for offline solving. These are
data files only; do not execute them as code.

## Retired tables excluded from Android and Windows (2026-10-24)

| Old table | Current production data |
|---|---|
| `twobar_table.bin` | `two_bar_shapes.bin` + `two_bar_group.bin` |
| `bandaged_c_table.bin` | `bandaged_c_shapes.bin` + `bandaged_c_group.bin` |
| `circle2_table.bin` | `circle2_group.bin` |
| `fused_table.bin` | `fused_group.bin` |
| `ai_cube_patterns.bin` | `ai_shapes.bin` + `ai_group.bin` |
| `burr_cube_patterns.bin` | `burr_shapes.bin` + `burr_group.bin` |
| `cuboid_442_patterns.bin`, `cuboid_442_endgame.bin` | `cuboid_442_orientations.bin` + `cuboid_442_group.bin` |

These eight files total **110,822,026 bytes (110.82 MB / 105.69 MiB)** in the
current checkout. They remain locally available for legacy builders and explicit
experimental search APIs, but normal solve-service dispatch uses their replacements.
This is a raw asset reduction; the final APK/ZIP difference requires a rebuild.

The additional Two-Bar, Bandaged C and BiCube complete layout/group tables
total **9,502 bytes**. The two large distance shells they replace total
43,619,201 bytes; the source files remain available for legacy tools.

`buildozer.spec` excludes these exact paths. Windows asset collection and its
post-build verification share `scripts/bundle_assets.py`; that script also checks
Android exclusions and verifies that all other `solver/data/*.bin` tables remain
included. Run `python scripts/bundle_assets.py` for the inventory.

The main remaining assets include `p4_table.bin` (315.32 MB), `joint_dist.bin`
(51.48 MB), and the ordinary 3×3 two-phase solver's `twophase/` lookup files.
These are still used and have not been removed. Camouflage's pattern/endgame
tables and the new Tangram Extreme shape table are also active.


## 加载和开发资源（2026-10-25）

应用启动不再预热普通两阶段及四阶求解器，实际求解时按需导入。四阶 `joint_dist.bin` 以共享只读文件映射访问，避免先读取整表再复制成可变数组；活动表仍完整离线分发。

Windows 分发不再带开发文档及未被产品引用的 `assets/demo.gif`；Android 排除开发文档。源码构建快照也跳过已经退役的八张表和这些开发文件，保留工作区原文件。额外减少约 2.4 MB 原始开发资源，最终 APK/ZIP 差异待重新构建后测量。检查记录在 `reports/optimization/2026-10-25/phase-2-6/`。
