"""Solve the four-colour Dino Cube.

White and yellow occupy opposite face pairs and red/blue the remaining pair,
so edges with the same two colours are interchangeable. The ordinary
twelve-edge Dino solver needs distinct virtual labels: enumerate the
permutations inside each colour-pair group, skip labelings with odd parity
(the Dino's move group preserves parity), and keep the first labelling whose
optimal solution replays to the four-colour solved state.
"""
import itertools
from collections import defaultdict

from cube.polyhedral import DINO4_FACE_COLORS, PolyhedralPuzzle
from solver.dino import solve_dino


def _solved(cube):
    return all(cube.colors[i]==DINO4_FACE_COLORS[sticker.face]
               for i,sticker in enumerate(cube.geometry.stickers))


def _odd(permutation):
    inversions=0
    for i in range(len(permutation)):
        for j in range(i+1,len(permutation)):
            if permutation[i]>permutation[j]:
                inversions+=1
    return inversions&1


def solve_dino4(cube,cancel=None,progress=None):
    geometry=cube.geometry
    physical=[]
    for index,slots in enumerate(geometry.pieces):
        first,second=slots
        one,two=cube.colors[first],cube.colors[second]
        physical.append((index,first,second,one,two,tuple(sorted((one,two)))))
    virtual_geometry=PolyhedralPuzzle('dino',2).geometry
    virtual=[]
    for index,slots in enumerate(virtual_geometry.pieces):
        first,second=slots
        face_one=virtual_geometry.stickers[first].face
        face_two=virtual_geometry.stickers[second].face
        virtual.append((index,first,second,face_one,face_two,
                        tuple(sorted((DINO4_FACE_COLORS[face_one],
                                      DINO4_FACE_COLORS[face_two])))))
    physical_groups=defaultdict(list)
    virtual_groups=defaultdict(list)
    for edge in physical:
        physical_groups[edge[5]].append(edge)
    for edge in virtual:
        virtual_groups[edge[5]].append(edge)
    keys=sorted(physical_groups)
    if any(len(physical_groups[key])!=len(virtual_groups.get(key,()))
           for key in keys):
        raise ValueError('The entered four-colour state is not legal')
    permutations=[list(itertools.permutations(virtual_groups[key])) for key in keys]
    total=1
    for choices in permutations:
        total*=len(choices)
    tried=0
    if progress:
        progress(0,total)
    for combination in itertools.product(*permutations):
        if cancel and cancel():
            raise InterruptedError()
        tried+=1
        if progress and tried%64==0:
            progress(tried,total)
        labels=[0]*len(cube.colors)
        permutation=[0]*len(physical)
        for key,assigned in zip(keys,combination):
            for physical_edge,virtual_edge in zip(physical_groups[key],assigned):
                index,first,second,one,two,_=physical_edge
                virtual_index,_,_,face_one,face_two,_=virtual_edge
                permutation[index]=virtual_index
                if DINO4_FACE_COLORS[face_one]==one:
                    labels[first]=face_one
                    labels[second]=face_two
                else:
                    labels[first]=face_two
                    labels[second]=face_one
        if _odd(permutation):
            continue
        work=PolyhedralPuzzle('dino',2)
        work.colors=labels
        try:
            word=solve_dino(work)
        except Exception:
            continue
        replay=cube.clone()
        for move in word:
            replay.apply_move(move)
        if _solved(replay):
            return tuple(word)
    raise ValueError('No legal four-colour Dino labelling was found')
