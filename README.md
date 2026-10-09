# 3D Cube Solver

**Solve a cube you can see, then follow every move in 3D.**

Enter colors, generate a scramble, or paste a move sequence. Validate the state, solve it, and replay the solution one turn at a time.

**2x2-5x5 | 3x3 Mastermorphix | Experimental 6x6-17x17**

[Get the latest Android APK](https://github.com/coco54-beep/cube-solver/releases/latest) | [中文说明](README.zh-CN.md) | [All releases](https://github.com/coco54-beep/cube-solver/releases)

## See it in action

<p align="center">
<img src="assets/screenshots/home.png" width="150" alt="Puzzle selection" />
<img src="assets/screenshots/input_3x3.png" width="150" alt="Cube entry" />
<img src="assets/screenshots/mastermorphix_input.png" width="150" alt="Mastermorphix entry" />
<img src="assets/screenshots/input_6x6.png" width="150" alt="6x6 entry" />
<img src="assets/screenshots/playback_stepping.png" width="150" alt="3D playback" />
</p>

## Choose your puzzle

| Puzzle | Features |
| --- | --- |
| **2x2-5x5** | Enter colors, validate, solve, and replay. Generate a scramble or paste move notation. |
| **3x3 Mastermorphix** | Shape-aware entry and validation, solving, and 3D replay. |
| **6x6-17x17** | Higher-order entry, scrambling, and solving. This feature is experimental. |

## How to solve

1. Choose a puzzle and size.
2. Enter colors, paste notation, or generate a scramble.
3. Validate the state and start solving.
4. Rotate and zoom the 3D cube, step through moves, or adjust playback speed.

The app also offers simple and advanced entry, undo/redo, demos, Chinese/English/Japanese languages, portrait/landscape layouts, and light/dark themes.

## Download and run

### Android

Download the latest [Android release](https://github.com/coco54-beep/cube-solver/releases/latest). Builds target **arm64-v8a**.

### Desktop

Requires Python 3.10 or newer.

```bash
git clone https://github.com/coco54-beep/cube-solver.git
cd cube-solver
python -m pip install -r requirements.txt
python run_desktop.py
```

If the 4x4 solver table is missing, install Git LFS and run `git lfs pull`.

## Solver overview

| Puzzle | Approach |
| --- | --- |
| 2x2/3x3 | Kociemba two-phase search |
| 4x4/5x5 | Reduce to 3x3, then solve |
| Mastermorphix | Shape-aware state conversion and a dedicated 3x3 path |
| 6x6-17x17 | Experimental solver; coverage and performance are still being evaluated |

Random-state coverage, performance across devices, and Android behavior for 6x6-17x17 have not been comprehensively benchmarked. Treat these results as experimental.

## Contribute

Run tests with `python -m pytest`. See [N x N notes](docs/nxn.md) and [Mastermorphix notes](docs/mastermorphix.md). Contributions are welcome. Licensed under [GPL-3.0](LICENSE).
