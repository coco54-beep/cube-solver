"""Generate compact bundled SQ1 lookup data; no solver cases are executed."""
from pathlib import Path
from array import array
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from solver.square1 import _build_tables

def main():
    index,*tables=_build_tables(progress=lambda done,total:print(f'{done}/{total}',flush=True))
    shapes=array('I',sorted(bits for bits,p in index if p==0))
    chunks=[b'SQ1TAB01',struct.pack('<I',len(shapes))]
    for value in (shapes,*tables):
        copy=array(value.typecode,value)
        if sys.byteorder!='little' and copy.itemsize>1:
            copy.byteswap()
        chunks.append(copy.tobytes())
    path=ROOT/'solver'/'data'/'square1_tables.bin'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(zlib.compress(b''.join(chunks),9))
    print(f'Bundled {path.stat().st_size} bytes',flush=True)

if __name__=='__main__':
    main()
