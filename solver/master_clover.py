"""Observed regular double-layer states, including the bonded corner fields."""
from functools import lru_cache
from cube.master_clover import MasterCloverCube,placement_maps
from cube.master_clover_aligned import AlignedMasterClover,generators,source_key,expand,observed_colors
from solver.rigid_colours import MaterialSolver


class MasterColourSolver(MaterialSolver):
    @lru_cache(maxsize=1)
    def local_patterns(self):
        g=self.aligned().geometry;result=[set() for _ in g.pieces]
        for slots in g.pieces:
            for mapping in placement_maps():
                home=g.stickers[mapping[slots[0]]].piece
                if {g.stickers[mapping[s]].piece for s in slots}!={home}:raise ValueError('Split bonded corner')
                paints={mapping[s]:g.stickers[s].face for s in slots}
                result[home].add(tuple(paints[s] for s in g.pieces[home]))
        return tuple(map(frozenset,result))


_profile=MasterColourSolver(MasterCloverCube,AlignedMasterClover,generators,source_key,expand,observed_colors,
                           'master_clover_colour_group.bin',complete_group=False)
validate=_profile.validate
solve_colours=_profile.solve_colours
solve=_profile.solve
