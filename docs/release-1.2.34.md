# 1.2.34 release notes

## Manual solving

- Added history-free state solvers for Fused, AI, Burr, Bandaged C, Two-Bar and BiCube.
- Added visible-state solvers for Circle 2 and the Crazy Planet series.
- Added visible-state solving for Tangram and Tangram Extreme, including shape restoration and a compressed algorithm table.
- Retained the 1.2.33 Mixup and special-puzzle entry work.

## Validation and input

- Standard 2×2–5×5 validation now rejects impossible corner twists, mirrored corners, flipped wings/midges and cross-orbit centre states.
- Valid even-order wing parity cases remain accepted.
- Re-tested input buttons, swatches, piece/block picking, palette settings and Mixup inner-edge choices.

## Verification

- Full test suite: **2225 passed, 8 skipped**.
- No physical Android device test was performed in this release.
