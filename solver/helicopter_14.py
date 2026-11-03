"""Shape repair and state-only colour solving with real truncated Helicopter moves."""
from functools import lru_cache
from cube.edge_jumbling import Helicopter14Cube
from cube.helicopter_14_aligned import AlignedHelicopter14,generators,source_key,expand,observed_colors
from cube.rigid_placements import placements
from solver.rigid_colours import MaterialSolver


class FourteenSolver(MaterialSolver):
    @lru_cache(maxsize=1)
    def local_patterns(self):
        c=Helicopter14Cube();g=self.aligned().geometry;result=[set() for s in c.solids]
        for home in range(len(c.solids)):
            for destination,frame,mapping in placements(Helicopter14Cube,home):
                paint={target:c.paints[source] for source,target in mapping}
                result[destination].add(tuple(paint[s] for s in g.pieces[destination]))
        return tuple(map(frozenset,result))


_profile=FourteenSolver(Helicopter14Cube,AlignedHelicopter14,generators,source_key,expand,observed_colors,
                       'helicopter_14_jumbling_group.bin',complete_group=False)
ASSET=_profile.asset
validate=_profile.validate
solve=_profile.solve
