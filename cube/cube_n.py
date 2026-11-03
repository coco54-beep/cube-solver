"""Variable order cube, using the same coordinates and moves as orders 2–5."""
from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS
from cube.coordinates import FACE_AXIS_SIGN, TURNS, layer_values

MIN_N = 4
MAX_N = 17


class CubeN(BaseCube):
    def __init__(self, cubies, n):
        if not MIN_N <= n <= MAX_N:
            raise ValueError(f"Supported higher orders: {MIN_N}–{MAX_N}")
        self.size = n
        super().__init__(cubies)

    @classmethod
    def solved(cls, n, colors=None):
        return cls(build_solved_cube(n, colors or DEFAULT_COLORS), n)

    def clone(self):
        return type(self)({p: c.clone() for p, c in self.cubies.items()}, self.n)

    def _apply_single_quarter(self, label, layers):
        """Turn the affected cubies in place on higher-order cubes.

        ``BaseCube`` clones every moving cubie for every quarter turn.  The
        higher-order reduction performs tens of thousands of turns, and those
        clones dominate its runtime.  Cubies are owned by exactly one cube
        state, so changing them in place is safe here; the rebuilt position
        dictionary preserves the same immutable state contract.
        """
        if label in ("x", "y", "z"):
            return super()._apply_single_quarter(label, layers)
        n_axis, _ = FACE_AXIS_SIGN[label]
        rot = TURNS[label]
        layer_set = set(layer_values(self.n, label, layers=layers))
        cubies = list(self.cubies.values())
        for c in cubies:
            if c.pos[n_axis] not in layer_set:
                continue
            c.pos = rot(*c.pos)
            c.stickers = {rot(*d): color for d, color in c.stickers.items()}
            if getattr(c, 'appearance_frame', None) is not None:
                c.appearance_frame = tuple(rot(*axis) for axis in c.appearance_frame)
        self.cubies = {c.pos: c for c in cubies}
