"""Build fixed-anchor projections offline; never run this on a phone."""
import sys
from pathlib import Path
from time import monotonic

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from solver.camouflage_patterns import anchored_model,fingerprint
from solver.cuboid_search import build_patterns


def main():
    started=monotonic()
    # Experimental: this candidate was slower than production in deep-state
    # comparisons. Keep its output outside all application bundles.
    destination=Path(__file__).resolve().parents[1]/'artifacts/development/camouflage_3_anchor_patterns.bin'
    build_patterns('camouflage_3',destination,strong=False,model=anchored_model(),
                   metadata={'anchor_fixed':True,'geometry':fingerprint()},
                   report=lambda *row:print(*row,'seconds',round(monotonic()-started,3),flush=True))
    print('saved',destination.stat().st_size,'bytes',flush=True)


if __name__=='__main__':main()
