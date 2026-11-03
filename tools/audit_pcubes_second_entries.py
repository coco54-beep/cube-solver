"""Visible shape-card and SQ re-entry without copying source piece IDs."""
import json
from pathlib import Path
import sys
from time import monotonic
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cube.polyhedral_scramble import scramble

OUT=Path('reports/optimization/2026-11-01/pcubes-second')


def freeze(value):return tuple(map(freeze,value)) if isinstance(value,list) else value


def container_entry(seed,length):
    from cube.container import ContainerCube
    from cube.mirror_tower import Piece
    source=ContainerCube.solved();scramble(source,length,seed)
    observations={str(position):source.appearance(p.home,p.frame) for position,p in source.pieces.items()}
    observations=json.loads(json.dumps(observations))
    entered=ContainerCube.solved();used=set();pieces={}
    for position,data in observations.items():
        position=int(position);signature=freeze(data);choices=[]
        for home in entered.pieces:
            if home in used:continue
            for frame in entered.placement_frames(home,position):
                if entered.appearance(home,frame)==signature:choices.append(Piece(home,frame))
        assert choices,position
        piece=choices[0];used.add(piece.home);pieces[position]=piece
    entered.pieces=pieces
    assert all(entered.appearance(p.home,p.frame)==source.appearance(source.pieces[pos].home,source.pieces[pos].frame)
               for pos,p in entered.pieces.items())
    return entered


def square_entry(kind,seed,length):
    from cube.square1 import Square1Cube
    from cube.square_family import SquareFamilyCube,outline
    from cube.square1_entry import Square1Entry
    from cube.square_family_entry import SquareFamilyEntry
    source=Square1Cube() if kind=='square1' else SquareFamilyCube.solved(kind)
    source.scramble(length,seed)
    draft=Square1Entry(empty=True) if kind=='square1' else SquareFamilyEntry(SquareFamilyCube.solved(kind),empty=True)
    data=[]
    for layer,start,width,piece in source.groups():
        cap,sides=source.piece_colors(piece) if kind!='square1' else __import__('cube.square1',fromlist=['piece_colors']).piece_colors(piece)
        shape=source.outline(layer,start,width,piece) if kind!='square1' else ()
        data.append((layer,start,width,(cap,)+sides,shape))
    for layer,start,width,colors,shape in json.loads(json.dumps(data)):
        slot=layer*12+start
        if kind=='square1':
            draft.set_shape(slot,width)
            for field,color in enumerate(colors):draft.paint(slot,field,color)
        else:
            options=[home for home,spec in enumerate(draft.specs)
                     if spec.width==width and spec.colors==tuple(colors)
                     and all(abs(a-b)<1e-8 for p,q in zip(outline(spec,layer,start,draft.layer_count),shape) for a,b in zip(p,q))
                     and (draft.layer_count==2 or spec.pair==int(layer in (1,2)))
                     and all(b.home!=home for b in draft.blocks.values())]
            assert options,(kind,slot,colors)
            draft.choose_piece(slot,options[0])
    draft.middle=source.middle
    entered=draft.to_cube()
    def visible(cube):
        if kind=='square1':return cube.slots
        return tuple((layer,start,width,cube.piece_colors(piece),cube.outline(layer,start,width,piece))
                     for layer,start,width,piece in cube.groups())
    assert visible(entered)==visible(source)
    return entered


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    for kind in ('container','square1','square0','square2','super_square1'):
        for length in (30,100):
            for seed in (20261101,20261102):
                started=monotonic()
                c=container_entry(seed,length) if kind=='container' else square_entry(kind,seed,length)
                if kind=='container':
                    from solver.fisher_skewb import solve_fisher_skewb
                    word=solve_fisher_skewb(c)
                elif kind=='square1':
                    from solver.square1 import solve_square1
                    word=solve_square1(c)
                else:
                    from solver.square_family import solve_square_family
                    word=solve_square_family(c)
                replay=c.clone()
                for move in word:replay.apply_move(move)
                assert replay.is_solved()
                row=dict(kind=kind,seed=seed,scramble_turns=length,moves=len(word),
                         seconds=round(monotonic()-started,4),visible_reentry=True,replay_solved=True)
                rows.append(row);print(json.dumps(row),flush=True)
                (OUT/'additional-entries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')


if __name__=='__main__':main()
