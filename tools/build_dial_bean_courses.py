"""Append only the three new original courses, preserving existing lessons."""
import json,zlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    from cube.polyhedral import PolyhedralPuzzle
    from cube.polyhedral_scramble import scramble
    from cube.dial_beans import KINDS
    from solver.dial_beans import solve
    from solver.result import SolveResult
    from demo.course import record
    path=Path('demo/data/expanded_courses.bin')
    data=json.loads(zlib.decompress(path.read_bytes()))
    selected=set(sys.argv[1:])
    if selected-set(KINDS):raise ValueError('Unknown course model')
    for kind,n in KINDS.items():
        if selected and kind not in selected:continue
        source=PolyhedralPuzzle(kind,n);scramble(source,30,20261109)
        source=source.entered();word=solve(source)
        result=SolveResult(True,list(word),'',0,len(word),[])
        data['models'][kind]=record(source,result)
        print(kind,len(word),flush=True)
    path.write_bytes(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9))


if __name__=='__main__':main()
