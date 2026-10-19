# 1.2.32 release notes

## Fix

- The appearance-layer change added `appearance_frame` to the base cubie type. Subclasses that append their own `frame` field (Mastermorphix, Ghost and Mirror shape pieces) were still constructed positionally, so the real frame was written into `appearance_frame` and the subclass frame stayed at identity.
- This affected scramble initialization, shape normalization, center-orientation generators and several Mirror/Mastermorphix/Ghost solve paths.
- Constructors now pass `frame=` explicitly. The full test suite passes: 1502 passed, 4 skipped.
