# CubeSolver 1.2.39

## Highlights

- Home search across puzzle families, orders and variants.
- Image cards and responsive 3–6 column pickers.
- Settings moved to the top-right; search occupies the previous bottom-right slot.
- Consistent names and order-first labels in Chinese, English and Japanese.
- Removed Master Clover and LanLan Pisces from the catalogue and assets.

## Stability

- Fixed input-screen crashes caused by a stale draft after an order change or resize.
- Guarded local entry checks against mismatched facelet dimensions.
- Session restore now ignores screens/puzzles that no longer exist.
- Fixed Twins/Pisces rendering import and frame-count failures.
- Fixed scramble-button repeat clicks and stale solve-result reuse for shaped puzzles.

## Solver and playback

- Higher-order cubes avoid per-quarter-turn Cubie cloning.
- Mastermorphix/Mirror compare centre plans from a shared core/wing prefix.
- Reduced low-yield Pentahedron/War Drum improvement budgets.
- Tangram Extreme verification uses fast frame transitions.
- Twins 120°/180° turns use angle-aware playback duration.

## Verification

- Automated suite: **4398 passed, 23 skipped**.
- Android package: arm64-v8a, API 26+, debug test build for this release candidate.
