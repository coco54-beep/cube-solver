# FTO three-order centre formula fix

The reported error was `No independent three-cycle found for these orbits: [3]`.
This is separate from the two-order core omission described in the earlier fix.

Three-order FTO has an edge orbit and two centre orbits. Restricting the
commutator's first turn to one anchor face found no independent cycle for the
opposite centre family. FTO now searches both the anchor and its opposite face.

`scripts/build_fto_cycles.py` generated all three required orbit formulas for
order 3 and all six for order 4. The order 3 primitive lengths are 80, 224 and
224 moves; these are primitive lengths, not full solution lengths. Every
order 4 primitive is eight moves. The compressed asset is 393 bytes.

Runtime loading checks the geometry fingerprint before using the saved words.
The existing Android source extension list includes this `.bin` asset.
Missing or incompatible assets fall back to the expanded formula search.

No scrambled-state solve tests were run, and no APK was packaged in this change.
