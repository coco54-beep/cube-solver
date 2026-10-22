"""Generate colour-preserving centre-grid alignment words from the 3x3 core."""
import json
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.cube3 import Cube3
from cube.conversion import cubies_to_facelets
from solver.solver3 import solve_3x3


def main():
    rng=random.Random(1702);faces='URFDLB';words={0:[]};kernels=[]
    for sample in range(80):
        scramble=[rng.choice(faces)+rng.choice(('','2',"'")) for _ in range(25)]
        cube=Cube3.solved();cube.apply_moves(scramble)
        result=solve_3x3(cubies_to_facelets(cube.cubies,3))
        if not result.success:continue
        word=scramble+[token for item in result.moves for token in item.split()]
        cube.apply_moves(word[len(scramble):])
        if not cube.is_solved():raise ValueError('Core replay failed')
        mask=0
        for token in word:
            if '2' not in token:mask^=1<<faces.index(token[0])
        if not mask:continue
        kernels.append((mask,word))
        changed=True
        while changed:
            changed=False
            for source,prefix in list(words.items()):
                for delta,addition in kernels:
                    dest=source^delta
                    if dest not in words or len(words[dest])>len(prefix)+len(addition):
                        words[dest]=prefix+addition;changed=True
        if len(words)==32:break
    if len(words)!=32:raise ValueError('Centre-orientation basis incomplete: '+str(len(words)))
    path=Path('assets/mixup_center_finish.json')
    path.write_text(json.dumps({'version':1,'words':words},separators=(',',':')),encoding='utf-8')
    print('centre masks',len(words),'maximum word',max(map(len,words.values())))


if __name__=='__main__':main()
