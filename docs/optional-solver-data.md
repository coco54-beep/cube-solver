# Optional solver data

Large precomputed solver tables are available as separate GitHub release
assets, so the application package does not have to carry every optional
table.

Current data release: `data-v1.2.34`

| File | Size | Used by |
|---|---:|---|
| `twobar_table.bin` | 18 MB | Two-Bar offline shell |
| `bandaged_c_table.bin` | 25 MB | Bandaged C offline shell |
| `circle2_table.bin` | 41 MB | Circle 2 legacy distance shell |
| `fused_table.bin` | 11 MB | Fused legacy distance shell |

Download URL pattern:

`https://github.com/coco54-beep/cube-solver/releases/download/data-v1.2.34/<file>`

Place downloaded files in `solver/data/` beside the application source, or in
the application's private data directory when a download UI is enabled.
These are data files only; do not execute them as code.
