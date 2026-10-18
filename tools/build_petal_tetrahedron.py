"""Prepare the exact small stabilizer tables for the regular petal tetrahedron."""
import json
from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cube.polyhedral import PolyhedralPuzzle
from solver.lattice_data import geometry_key
from solver.polyhedral import StabilizerChain, apply_word, simplify


def build(kind='petal_tetrahedron'):
    if kind not in ('petal_tetrahedron', 'petal_tetrahedron_nocentre'):
        raise ValueError('Unsupported edge-turn tetrahedron variant')
    cube = PolyhedralPuzzle(kind, 3)
    chain = StabilizerChain(cube)
    stages = []
    examples = {}
    for table in chain.trans:
        stage = {}
        for position, (permutation, word) in table.items():
            expanded = tuple(word.flatten(2))
            if apply_word(cube.geometry, expanded) != permutation:
                raise ValueError('Prepared stabilizer word does not match its permutation')
            stage[str(position)] = dict(permutation=permutation,
                                       word=[(m.axis, m.layer, m.amount) for m in expanded])
            short = simplify(expanded, 2)
            affected = tuple(sorted({cube.geometry.stickers[i].piece
                                     for i, j in enumerate(permutation) if i != j}))
            if 2 <= len(short) <= 16 and affected:
                example = dict(word=[(m.axis, m.layer, m.amount) for m in short],
                               affected=affected)
                if affected not in examples or len(short) < len(examples[affected]['word']):
                    examples[affected] = example
        stages.append(stage)
    path = Path(__file__).resolve().parents[1] / 'solver/data' / (kind + '_chain.bin')
    path.write_bytes(zlib.compress(json.dumps(dict(
        geometry=geometry_key(cube.geometry), stages=stages,
        examples=sorted(examples.values(),key=lambda r:(len(r['affected']),len(r['word'])))[:3]),
        separators=(',', ':')).encode(), 9))
    print(f'{sum(map(len, stages))} prepared transversals; {path}')


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv)>1 else 'petal_tetrahedron')
