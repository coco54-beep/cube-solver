# 1.2.33 release notes

## New puzzle families

- **Mixup** 3×3, 3×3×4, 3×4×4 and 4×4×4, plus the Mixup Plus variants (3×3, 3×3×4, 3×4×4, 4×4×4). Each model has its own geometry-aware shape/core reduction pipeline (`cube/mixup.py`, `solver/mixup_reduction.py`, `solver/mixup_group.py`) and precomputed group assets, so entered states are solved without relying on the scramble history.
- **Tangram**, **Tangram Extreme**, **O2**, **Pentacle** and **Ancient Coin**, with geometry, renderer, solver and input screens.
- **Penrose** and **Pandora** entry screens.

## Entry and palettes

- Six-view direct entry for shape/cuboid puzzles and articulated-observation entry for the new families.
- Piece-palette and cube-palette screens.

## Fixes

- **Mixup Plus 3×4×4 no longer aborts.** The shape search could raise its reduction limit and the whole solve failed. The limit is now caught, the partial shape frame is used, and the layout/colour fallbacks run.
- The inner-edge flip finish in the shape stage now runs for **every** Plus model, not just Mixup Plus 4×4×4.
- The 1.2.32 shape-piece frame fix (Mastermorphix, Ghost, Mirror) is included.

## Verification

- Mixup and entry-screen regression tests are included under `tests/test_mixup_*.py`.
- Solutions are replay-checked against the puzzle's legal move model before being returned.

## Windows packaging fix (re-uploaded exe)

- The portable Windows build crashed on start with `TypeError: expected str, bytes or os.PathLike object, not NoneType`. The `kivy_deps` packages call `os.path.join(site.USER_BASE, ...)` while Kivy imports, but PyInstaller never runs `site.main()` so `site.USER_BASE` is `None`. `app/desktop_runtime.py` now fills it in before Kivy loads.
- Kivy's `get_deps_minimal` lists the image providers as `kivy.core.image.image_*`, but the real modules are `img_*`; none were bundled and Kivy aborted with "Unable to get any Image provider". `packaging/windows.spec` now adds `img_dds`, `img_pil`, `img_sdl2` and `img_tex` explicitly.
- The re-uploaded `CubeSolver-1.2.33-windows-x64.zip` starts the GUI, loads the image/text/window providers and passes the frozen self-check (sha256 `7393d59cb6f89f10907b027e7ea79f48c4e616cb3654550ccd5903f28405fea4`).
