# High-order Megaminx mobile memory changes

Thirteenth-order solving was reported to exit the Android app after a long
wait. No crash log is available, so Android memory termination is a suspected
cause, not a confirmed diagnosis.

Changes:

- Native beam search retains the best beam after each parent expansion, rather
  than storing all parents' complete candidate states until the level ends.
  Stable score sorting keeps first-seen tie ordering.
- NumPy lookup tables use 16-bit indices when the position count permits it;
  redundant Python lookup copies are released after conversion.
- Primitive discovery retains at most two orbit transport trees. Evicted trees
  can be rebuilt if needed; the tradeoff is extra computation on cache misses.
- MemoryError propagates to the existing solve failure handler instead of
  starting a second, expensive solver pipeline under memory pressure.
- Transport expansion and move shortening check cancellation more often.
- Playback-word loop reduction also uses compact permutation indices.

This preserves the solver's full replay validation. These edits have received
syntax and whitespace checks only; no solve benchmark, Android reproduction,
memory measurement or APK build has been performed for this change.

## Follow-up: shared high-order planning

- High-minx shallow-state reduction reuses the probe's working state and move
  word instead of repeating the identical native beam from the original state.
- Orbit alternatives score joins using only touching axis blocks. Both words
  are simplified first; when an entire boundary block cancels, scoring proceeds
  to the newly exposed boundary. This produces the exact join length without
  rescanning a long unchanged prefix on each proposal.
- Greedy orbit ordering uses the same boundary scoring and keeps its prefix
  simplified after accepting a word. This covers high minxes, reduced minxes
  and the generic tetrahedral-family orbit path.
- Single-colour orbit planning also compares a decomposition of the inverse
  target, inverted back into a word for the original target. It shares the
  existing search deadline and is accepted only when shorter than the best
  candidate so far. Football and icosahedron centre orbits use this shared
  planner too. This is a local optimisation, not a new global solving method.

No measured speed or move-count improvements are claimed for this follow-up;
runtime replay checks remain in the solver but have not been run for these
edits. Replacing time-budgeted search proposals may change the chosen word.

## Desktop verification, 2026-10-18

Subsequent desktop regression and deep-scramble replay checks have now run;
see `desktop-verification-2026-10-18.md` for results. They supersede the
syntax-only status above. Android process memory and the reported phone crash
remain unverified without a device/log. No new APK has been built.

The subsequent Android emulator run did reproduce LOW_MEMORY termination.
The remaining unbounded primitive-word cache and boxed deferred permutations
were fixed, followed by prepared core-protecting orbit plans for orders 4–13.
The final source replay passed on Android 13 x86_64 with a 310736 KiB process
VmHWM. Physical-device behaviour is still unverified. See
`solver-memory-audit-1.2.29.md` for the later results and APK checks.
