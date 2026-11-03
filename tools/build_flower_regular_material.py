"""Rebuild the hidden and visible sphere/plane cells offline."""
import sys,json,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.flower_material import build_masks,fingerprint

if __name__=='__main__':
    masks=build_masks()
    data=dict(version=1,source=fingerprint(),masks=masks)
    target=Path('cube/data/flower_regular_material.bin')
    target.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))
    print(len(masks),'closed Boolean cells;',target.stat().st_size,'bytes')
