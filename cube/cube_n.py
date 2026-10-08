"""Variable order cube, using the same coordinates and moves as orders 2–5."""
from cube.cubie_model import BaseCube, build_solved_cube
from cube.colors import DEFAULT_COLORS

MIN_N = 6
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
