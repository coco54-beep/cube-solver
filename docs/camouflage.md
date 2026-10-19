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
Manual states have a bounded short search. A complete solver for arbitrary
manual Camouflage input has **not** been implemented. Colour counts alone
do not establish reachability.

Desktop UI exports are in `artifacts/camouflage/`. No Android build or device
verification was performed for this change.

## References

- [Ladislav Dubravský: Bandaged 4x4s — WitEden Camouflage 3×3](https://ladislavdubravsky.wordpress.com/2015/04/04/bandaged-4x4s-witeden-camouflage-3x3/)
- [J. A. Storer: Camouflage Cube 3×3×3 and physical photographs](https://www.cs.brandeis.edu/~storer/JimPuzzles/ZPAGES/zzzCamouflageCube3x3x3.html)
