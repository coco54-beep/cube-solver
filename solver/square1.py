"""Cancellable Python adaptation of Shuang Chen's Square-1 two-phase solver.

Copyright (C) 2023 Shuang Chen. Adapted from cs0x7f/sq12phase, GPLv3 or later.
https://github.com/cs0x7f/sq12phase
This file is distributed under the GNU GPLv3 or later, without any warranty.
Phase 1 restores square shape and parity; phase 2 solves the actual pieces.
"""
from array import array
from collections import deque
from functools import lru_cache
from itertools import product,permutations
from threading import Lock
from pathlib import Path
import struct
import sys
import zlib
from time import monotonic

from cube.square1 import Square1Cube,Square1Move

_TABLES=None
_LOCK=Lock()
_FACT=(1,1,2,6,24,120,720,5040)


def _check(cancel):
    if cancel and cancel():
        raise InterruptedError()


def rank(p):
    return sum(sum(b<a for b in p[i+1:])*_FACT[7-i] for i,a in enumerate(p[:-1]))


def _shape_turn(bits,parity,layer):
    top,bottom=bits>>12,bits&4095
    value=top if layer==0 else bottom
    amount=mpar=0
    while True:
        if value&2048:
            amount+=2
            value=(value<<2)^12291
        else:
            amount+=1
            value<<=1
        mpar^=1
        if (value&63).bit_count()%2==0:
            break
    if value.bit_count()&2==0:
        parity^=mpar
    return ((value<<12)|bottom if layer==0 else (top<<12)|value),parity,amount


def _shape_slice(bits,parity):
    top,bottom=bits>>12,bits&4095
    a=top&63
    parity^=(((a.bit_count()& (bottom&4032).bit_count())>>1)&1)
    return ((top&4032)|((bottom>>6)&63))<<12 | (bottom&63)|(a<<6),parity


def _build_tables(cancel=None,progress=None):
    half=(0,3,6,12,15,24,27,30,48,51,54,60,63)
    shapes=sorted(a<<18|b<<12|c<<6|d for a,b,c,d in product(half,repeat=4)
                  if (a.bit_count()+b.bit_count()+c.bit_count()+d.bit_count())==16)
    index={(bits,p):i*2+p for i,bits in enumerate(shapes) for p in (0,1)}
    count=len(shapes)*2
    top,bottom=(array('I',[0])*count for _ in range(2))
    slash=array('H',[0])*count
    for state in range(count):
        _check(cancel) if state%128==0 else None
        bits,p=shapes[state>>1],state&1
        b,q,m=_shape_turn(bits,p,0)
        top[state]=(index[b,q]<<4)|m
        b,q,m=_shape_turn(bits,p,1)
        bottom[state]=(index[b,q]<<4)|m
        b,q=_shape_slice(bits,p)
        slash[state]=index[b,q]
    goals=(0x0db66db,0x1db6db6,0x16db6db,0x06dbdb6)
    shape_dist=array('b',[-1])*count
    queue=deque()
    for value in goals:
        state=index[value&0xffffff,value>>24]
        shape_dist[state]=0
        queue.append(state)
    while queue:
        state=queue.popleft()
        if state%128==0:
            _check(cancel)
        nxts=[slash[state]]
        for table in (top,bottom):
            at=state
            amount=0
            while amount<12:
                step=table[at]
                at=step>>4
                amount+=step&15
                nxts.append(at)
        for nxt in nxts:
            if shape_dist[nxt]<0:
                shape_dist[nxt]=shape_dist[state]+1
                queue.append(nxt)
    if progress:
        progress(1,3)
    pt,pb,ps=(array('H',[0])*40320 for _ in range(3))
    for i,p in enumerate(permutations(range(8))):
        if i%256==0:
            _check(cancel)
        pt[i]=rank(p[1:4]+p[:1]+p[4:])
        pb[i]=rank(p[:4]+p[5:]+p[4:5])
        ps[i]=rank(p[:2]+p[4:6]+p[2:4]+p[6:])
    square_dist=array('b',[-1])*80640
    square_dist[0]=0
    queue=deque([0])
    while queue:
        state=queue.popleft()
        if state%256==0:
            _check(cancel)
        perm,mid=state>>1,state&1
        nxts=[(ps[perm]<<1)|(1-mid)]
        for table in (pt,pb):
            at=perm
            for _ in range(3):
                at=table[at]
                nxts.append((at<<1)|mid)
        for nxt in nxts:
            if square_dist[nxt]<0:
                square_dist[nxt]=square_dist[state]+1
                queue.append(nxt)
    if progress:
        progress(2,3)
    return index,top,bottom,slash,shape_dist,pt,pb,ps,square_dist


def tables(cancel=None,progress=None):
    global _TABLES
    if _TABLES is None:
        while not _LOCK.acquire(timeout=.1):
            _check(cancel)
        try:
            if _TABLES is None:
                _check(cancel)
                _TABLES=_load_tables() or _build_tables(cancel,progress)
        finally:
            _LOCK.release()
    return _TABLES


def _load_tables():
    path=Path(__file__).parent/'data'/'square1_tables.bin'
    if not path.is_file():
        return None
    try:
        data=zlib.decompress(path.read_bytes())
        if data[:8]!=b'SQ1TAB01':
            return None
        count=struct.unpack_from('<I',data,8)[0]
        if count!=3678:
            return None
        offset=12
        values=[]
        for code,length in [('I',count),('I',2*count),('I',2*count),('H',2*count),('b',2*count),
                             ('H',40320),('H',40320),('H',40320),('b',80640)]:
            value=array(code)
            end=offset+length*value.itemsize
            value.frombytes(data[offset:end])
            if sys.byteorder!='little' and value.itemsize>1:
                value.byteswap()
            if len(value)!=length:
                return None
            values.append(value)
            offset=end
        if offset!=len(data):
            return None
        shapes=values.pop(0)
        index={(bits,p):i*2+p for i,bits in enumerate(shapes) for p in (0,1)}
        return (index,*values)
    except (OSError,ValueError,zlib.error,struct.error):
        return None


def solve_square1(cube,cancel=None,progress=None,optimize_budget=.2):
    cube.validate()
    if cube.is_solved():
        return ()
    work=cube.clone()
    prefix=[]
    # A direct entry may be between sliceable alignments. Align each layer
    # without changing its shape before looking up the shape coordinate.
    for axis in (0,1):
        offset=axis*12
        for amount in range(12):
            part=work.slots[offset:offset+12]
            shifted=part[amount:]+part[:amount]
            if shifted[-1]!=shifted[0] and shifted[5]!=shifted[6]:
                if amount:
                    move=Square1Move(axis,amount)
                    prefix.append(move)
                    work.apply_move(move)
                break
        else:
            raise ValueError('square1.error.shape')
    index,st,sb,ss,sd,pt,pb,ps,pd=tables(cancel,progress)
    shape=index.get(work.solver_shape())
    if shape is None or sd[shape]<0:
        raise ValueError('square1.error.shape')
    path=[]
    visits=0
    deadline=None
    total_limit=None
    failed=set()

    class SearchBudgetExpired(Exception):pass

    def tick():
        nonlocal visits
        visits+=1
        if visits%1024==0:
            _check(cancel)
            if deadline is not None and monotonic()>=deadline:
                raise SearchBudgetExpired()

    def phase2(edge,corner,te,be,mid,remaining,last):
        tick()
        if remaining==0:
            return edge==corner==mid==0 and not te and be
        if max(pd[(edge<<1)|mid],pd[(corner<<1)|mid])>remaining:
            return False
        state=(edge,corner,te,be,mid,remaining,last)
        if state in failed:return False
        if last!=0 and te==be:
            e,c,m=ps[edge],ps[corner],1-mid
            if max(pd[(e<<1)|m],pd[(c<<1)|m])<remaining:
                path.append(0)
                if phase2(e,c,te,be,m,remaining-1,0):
                    return True
                path.pop()
        for axis,table,first in ((0,pt,te),(1,pb,be)):
            if last>axis:
                continue
            f=not first
            e=table[edge] if f else edge
            c=corner if f else table[corner]
            amount=1 if f else 2
            while amount<12:
                if max(pd[(e<<1)|mid],pd[(c<<1)|mid])<remaining:
                    path.append(amount if axis==0 else -amount)
                    if phase2(e,c,f if axis==0 else te,f if axis==1 else be,mid,remaining-1,axis+1):
                        return True
                    path.pop()
                f=not f
                if f:
                    e=table[e]
                    amount+=1
                else:
                    c=table[c]
                    amount+=2
        if len(failed)<100000:failed.add(state)
        return False

    def start_phase2():
        d=work.clone()
        for value in path:
            d.apply_move(Square1Move(2) if value==0 else Square1Move(0 if value>0 else 1,abs(value)))
        edges,corners,te,be,mid=d.square_coordinates()
        if set(edges)!=set(range(8)) or set(corners)!=set(range(8)):
            return False
        edge,corner=rank(edges),rank(corners)
        lower=max(pd[(edge<<1)|mid],pd[(corner<<1)|mid])
        # Keep phase two bounded so one difficult square-shape candidate
        # cannot monopolise the search. Phase one tries other candidates.
        upper=17 if total_limit is None else min(17,total_limit-len(path))
        for depth in range(lower,upper+1):
            if phase2(edge,corner,te,be,mid,depth,0):
                return True
        return False

    def phase1(state,remaining,last):
        tick()
        if sd[state]>remaining:
            return False
        if remaining==0:
            return sd[state]==0 and start_phase2()
        if sd[state]==0 and remaining<4:
            return False
        if last!=0 and sd[ss[state]]<remaining:
            path.append(0)
            if phase1(ss[state],remaining-1,0):
                return True
            path.pop()
        for axis,table in ((0,st),(1,sb)):
            if last>axis:
                continue
            at=state
            amount=0
            while True:
                step=table[at]
                at=step>>4
                amount+=step&15
                if amount>=12:
                    break
                if sd[at]<remaining:
                    path.append(amount if axis==0 else -amount)
                    if phase1(at,remaining-1,axis+1):
                        return True
                    path.pop()
        return False

    _check(cancel)
    for depth in range(sd[shape],40):
        if progress:
            progress(depth,40)
        if phase1(shape,depth,-1):
            best=tuple(path)
            if optimize_budget>0:
                deadline=monotonic()+optimize_budget
                try:
                    for shape_depth in range(depth,min(40,depth+4)):
                        while monotonic()<deadline:
                            total_limit=len(best)-1
                            if shape_depth>total_limit:break
                            path.clear()
                            if not phase1(shape,shape_depth,-1):break
                            best=tuple(path)
                except SearchBudgetExpired:
                    pass
            _check(cancel)
            path[:]=best
            solution=tuple(prefix)+tuple(Square1Move(2) if v==0 else Square1Move(0 if v>0 else 1,abs(v)) for v in path)
            replay=cube.clone()
            replay.apply_moves(solution)
            if not replay.is_solved():
                raise ValueError('square1.error.replay')
            return solution
    raise ValueError('square1.error.illegal')
