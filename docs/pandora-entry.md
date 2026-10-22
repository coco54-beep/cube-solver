# Pandora colour entry

Pandora now opens the shared face-colour input screen. Each face displays its
actual eight triangular panels and square centre. Select a colour and tap a
panel; use the existing arrows to move between faces. Face fill, colour pick,
undo, redo, clear, random input and formula input remain available.

The display uses a logical 3×3 facelet carrier with Pandora-specific polygons
and polygon picking. The ordinary square-grid picker is not used for these
triangles. This carrier is only for editing; it never replaces the physical
Pandora solver model.

`cube/pandora_entry.py` shares the existing photo profile's colour-to-piece
conversion. Committing complete input constructs a real `PandoraCube`, preserving
the centre-based holding orientation and physical palette. Returning from the
Pandora turn screen converts the updated physical pieces back into face colours.
Photo input, tutorials and solution playback return to the same colour entry page.

Pandora's cached face colours use a separate key from ordinary 3×3 input. Session
capture includes the colour page when the selected puzzle is Pandora.

Desktop previews are in `artifacts/pandora-entry/`. The preview generator exercised
a scrambled colour input, physical-model conversion, and writeback after a turn.
No automated test suite, Android build or device check was run for this change.
