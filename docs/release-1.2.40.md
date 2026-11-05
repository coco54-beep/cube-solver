# CubeSolver 1.2.40

## Solver and entry fixes

- Hexagram records legal turns and verifies a candidate inverse on the entered
  shape and paints before returning it. This covers scrambles that are manually
  twisted afterwards and survive session save/reload.
- Edge-turning Helicopter-family entry uses the same recorded-turn recovery.
- Mixup Plus retains its verified partial shape prefix when reduction reaches a
  search limit. Difficult states may still require a longer retry.
- Yeet Ball uses corrected spherical cut geometry.

## UI fixes

- Returning to Home no longer leaves the puzzle grid blank; the directory is
  scrolled to the top and relaid out.
- Photo entry groups follow the current Home categories.
- About text is updated in Chinese, English and Japanese.

## Known limits

- Mixup Plus 3×4×4 can still time out during shape restoration for some random
  states.
- Manually painted Hexagram states without recorded turns remain limited by the
  colour/group solver.
