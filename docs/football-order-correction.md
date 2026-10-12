# Football catalogue correction

The user clarified that the football family should offer orders 3 and 5.
The former order 2 and order 4 entries have been removed. The specification
now rejects unsupported orders, and geometry no longer routes football through
the even-order surface reconstruction.

The removed reconstruction projected retained stickers into nearest-centroid
face regions. Those Voronoi boundaries were not actual turning cuts, so a
closed sticker permutation did not establish that the rendered pieces could
turn along those seams.

The catalogue now lists 3 and 5. Both entries are enabled. Earlier 2/3/4
claims in the catalogue implementation notes are superseded by this correction.

## Order 5 implementation

The former .87/.94 cut depths generated 812 pieces and 1292 stickers,
including additional split hexagon edges. The revised .9/.95 pair generates
722 pieces and 1112 stickers: each pentagon has 31 stickers and each hexagon
37. These depths retain the classical Tuttminx inner cut and divide its
outer cap into two turnable bands. This is a planar model of the Rayminx
structure; it does not reproduce manufacturer plastic clearances or internals.

There are 32 fixed centre pieces, six 60-piece single-colour centre orbits,
four 60-piece two-colour edge orbits, 60 three-colour corners and one 30-piece
central hexagon/hexagon edge orbit. Every axis has two bands. Pentagon steps
are 72 degrees and hexagon steps 120 degrees.

The entry, customization, reset colours, scramble, undo, validation and
solution playback use the existing 32-colour football screens. The five-order
solver now restores its central edge positions and flips before reducing all
11 remaining movable orbits. Formula discovery includes both pentagon and
hexagon anchors and permits cancellation using other isolated centre cycles.

`scripts/build_football_cycles.py --orders 5` produced all 11 independent
orbit cycles (8 to 50 moves each), a central-edge position cycle and 29
independent even-flip relations. The bundled asset preserves the order 3
record and removes the discontinued order 2 and 4 records. Runtime checks
both the geometry fingerprint and complete orbit coverage before solving.

Formula generation and a native input preview were completed. No scrambled
state solver tests were run, and no APK was built for this change.

Manufacturer reference:
[VeryPuzzle Rayminx](https://www.verypuzzle.com/product/61-rayminx/) describes
Rayminx as a double-layered Tuttminx. This establishes the family relationship,
not the exact dimensions of the currently coded cut planes.

No tests were run and no APK was built for this catalogue correction.
