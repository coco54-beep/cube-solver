"""Profile one polyhedral solve and print the hottest functions."""
import cProfile
import io
import pstats
import sys

from cube.polyhedral import PolyhedralPuzzle
from cube.polyhedral_scramble import scramble, scramble_length
from solver.polyhedral import solve_polyhedral


def main():
    kind, n = sys.argv[1], int(sys.argv[2])
    cube = PolyhedralPuzzle.solved(kind, n)
    cube.colors = [s.face for s in cube.geometry.stickers]
    scramble(cube, scramble_length(cube), seed=12345)
    profiler = cProfile.Profile()
    profiler.enable()
    solution = solve_polyhedral(cube)
    profiler.disable()
    print("moves", len(solution))
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("tottime")
    stats.print_stats(20)
    print(stream.getvalue())
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumtime")
    stats.print_stats(20)
    print(stream.getvalue())


if __name__ == "__main__":
    main()
