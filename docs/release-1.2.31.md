# 1.2.31 release notes

## New puzzle families

- Cuboid series: 3×3×2, 2×2×3, 3×3×4, 2×2×4, 4×4×2, 2×3×4, 1×3×3 Super Floppy, 3×3×5 and 4×4×6.
- Circle / Crazy Planet: Circle 2×2 and eight planet variants.
- Bandaged / fused: Fused Cube, Two-Bar Cube, Bandaged C, BiCube, AI Cube, Burr Cube and Camouflage.
- Penrose 2×2, Penrose 3×3 and Penrose 4×4.
- Super Ivy, Mosaic, Tins, Dino Skewb, Dayan Dino Skewb, Fisher Skewb, Pyraminx Duo, Ghost Pyramid, Coin Tetrahedron, Helicopter and order-5 FTO.

## Solver work

- Super Floppy is solved by a complete 3,041,280-state distance table, so app-generated scrambles return shortest solutions.
- App-generated scrambles for long reduction puzzles keep a legal inverse path; typical output drops from 100–450 moves to about 30.
- Petal Tetrahedron solutions were shortened significantly.
- SQ playback and randomisation crashes were fixed.
- Geometry and appearance layers were added for cuboid, bandaged, Penrose, circle and the new special puzzles.

## Known limitations

- Deep manually entered cuboid and bandaged states use bounded search; some states still require a dedicated full reduction solver.
- Real-camera validation for every new irregular profile has not been repeated on a physical phone in this release.
