# Fixed-layout bandaged entry

## One screen: shape, colour, pivot and rotation

Entry starts with a full 3×3 or 4×4 grid. Select a physical plate size
(1×1, 2×1, 2×2), select a colour, and tap the cell that will serve as the
rotation pivot. A cyan ring marks that cell centre. The 90° control rotates
the proposed plate clockwise around that cell, including 180° and 270°.
For 2×2 plates this changes the occupied quadrant; the pivot stays fixed.
Tap the check button to confirm both the connection and its colour.

A tap or a rotation only updates the preview. It never changes entered data.
Confirmed cells cannot be overwritten by a new plate. Out-of-bounds placement
and sizes exceeding the selected model's plate inventory are rejected.
Plates may occupy scrambled positions, rather than only their solved slots.
Undo/redo restores the connection and colours as one operation.
Changing the viewed face cancels the unconfirmed preview.

Full validation fits colours and seams to rigid groups from the selected
model, assigning a shared proper rotation to every cubie in a bonded group.
It rebuilds home identities, positions and frames without a scramble history.
The preset's fixed bonds remain the mechanical constraints; this does not
create arbitrary custom bandages. Entry is committed before opening twist.
The size steps advance when complete, skip missing sizes, and add extra sizes
where needed (Two-Bar, for example, includes 3×1). Imported scrambles retain
their already known physical layout.

## Layout checks

- Solved and legally scrambled states of all six current bandaged presets
  partition every face into plates without missing or duplicated cells.
- BiCube and Bandaged Cube C match the stored reference partitions on all six faces.
- Colour equality never determines which cells are bonded.
- Previewing does not modify colours or mechanical groups.
- Rotation uses the clicked cell centre for bars and squares.
- Overlap, out-of-bounds, wrong inventories and incompatible cross-face
  connections are rejected. Valid moved plates are accepted.
- Confirmation and undo/redo preserve both colours and connections together.
- Render caches include confirmed bonds so grid seams update correctly.

Tests are in `tests/test_bandaged_entry.py`. Desktop previews and size inventories
are in `artifacts/bandaged-entry/` and `artifacts/input-audit/`.
Rigid matching and ordinary cube validation do not prove reachability under
bandage restrictions. The current solver still has limited support for manual
bandaged states; an ordinary cube solution is accepted only after legal replay.
No APK was built for this change.
