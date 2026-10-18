# 1.2.30 release notes

## New puzzle families

- Petal Tetrahedron and Petal Icosahedron, with and without centres
- SQ-0, SQ-2 and Super SQ-1
- Mirror Windmill / Mirror Fisher unequal-height and offset-cut variants
- Ghost Cube, Skewb Ultimate, Void Megaminx, Four-Colour Dino
- Axis, Windmill and Fisher cubes in order 4

## Solver improvements

- Dedicated Skewb Ultimate solver using a standard-Skewb body projection and an exact centre-flip table; typical solutions are 9-12 moves.
- Full-state Mirror Skewb solver; typical solutions are 10-11 moves.
- SQ-2 uses a one-turn parity fix and two-layer setup prefixes; average solutions are around 246 moves.
- Super SQ-1 tries several alignment starts to avoid hard Square-1 projections.
- Petal Icosahedron uses six-move no-centre petal macros and solves the movable centres last.
- All solutions are replayed before they are shown.

## UI and translations

Updated Chinese, English and Japanese help, About text, puzzle labels and README files. Fixed theme access during screen construction without a running App and restored UIButton.refresh_theme().

## Verification

1,413 tests passed and 4 skipped. New solvers were benchmarked on desktop; Android device timing was not re-run for every family.
