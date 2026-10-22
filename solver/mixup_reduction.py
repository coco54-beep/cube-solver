"""History-independent Mixup reduction using physical geometry states."""
from functools import lru_cache
from heapq import heappop,heappush
from itertools import count
from time import monotonic

from cube.articulated import frame_key,multiply,turn_frame,proper_poses
from cube.appearance import transform_frame
from cube.articulated_observation import polygon_key
from cube.mixup import MixupCube,MixupSliceMove,_panel_bounds
from cube.polyhedral import Move,CUBE,dot


class ReductionLimit(ValueError):
    def __init__(self,frames,path):
        super().__init__('mixup.shape_limit')
        self.frames=tuple(frames);self.path=tuple(path)


class ReductionGeometry:
    def __init__(self,kind):
        self.cube=MixupCube(kind);self.kind=kind
        self.cuts=self.cube._bands()[1]
        self.slabs=tuple((a,l) for a,cut in enumerate(self.cuts) for l in range(len(cut)+1))
        self.spans=tuple((a,tuple(range(1,len(cut)))) for a,cut in enumerate(self.cuts) if len(cut)>2)
        primary=tuple((a,(l,)) for a,l in self.slabs)+self.spans
        self.search_ranges=frozenset(primary)
        self.ranges=primary+tuple((a,tuple(range(first,last+1))) for a,cut in enumerate(self.cuts)
                          for first in range(len(cut)+1) for last in range(first,len(cut)+1)
                          if (a,tuple(range(first,last+1))) not in self.search_ranges)
        self.slabs=tuple((a,layers[0]) for a,layers in self.ranges)
        self.all_mask=(1<<len(self.slabs))-1
        self.ids={};self.features={};self.turns={}
        self.goals={self.shape(home,0) for home in range(len(self.cube.solids))}

    def shape(self,home,pose):
        solid=self.cube.solids[home]
        faces=self.cube.placed_faces(home,pose)
        panels=tuple(sorted(polygon_key(poly) for poly,c in faces if c>=0))
        # Black display closures neither define a cut nor a solved sticker.
        # Retain the real pose for replay, but quotient only by the coloured
        # boundary and anchor, which determine every legal move here.
        body=()
        anchor=tuple(round(v,6) for v in transform_frame(self.cube.orientations[pose],solid.anchor))
        key=solid.role,panels,body,anchor
        if key not in self.ids:self.ids[key]=len(self.ids)
        return self.ids[key]

    def feature(self,home,pose):
        k=home,pose
        if k in self.features:return self.features[k]
        cube=self.cube;solid=cube.solids[home]
        anchor=transform_frame(cube.orientations[pose],solid.anchor)
        bins=tuple(sum(anchor[a]>bound+1e-7 for bound in cut) for a,cut in enumerate(self.cuts))
        bounds=_panel_bounds(self.kind,home,pose);allowed=0;selected=0
        for bit,(axis,layers) in enumerate(self.ranges):
            cut=self.cuts[axis];low=cut[layers[0]-1] if layers[0] else float('-inf')
            high=cut[layers[-1]] if layers[-1]<len(cut) else float('inf')
            lo,hi=bounds[axis];moving=bins[axis] in layers
            if moving:selected|=1<<bit
            if any(lo<b-1e-7 and hi>b+1e-7 for b in (low,high)):continue
            if moving and (lo<low-1e-7 or hi>high+1e-7):continue
            if not moving and lo<high-1e-7 and hi>low+1e-7:continue
            allowed|=1<<bit
        shape=self.shape(home,pose)
        frame=cube.orientations[pose]
        bad=any(not any(dot(transform_frame(frame,CUBE[colour]),n)>1-1e-7 for n in CUBE)
                for poly,colour in solid.faces if colour>=0)
        result=shape,int(bad)*(1 if solid.role=='inner_edge' else 100),allowed,selected
        self.features[k]=result;return result

    def next_pose(self,axis,amount,pose):
        k=axis,amount,pose
        if k not in self.turns:
            axis_vector=tuple(float(i==axis) for i in range(3))
            import math
            turn=turn_frame(axis_vector,amount*math.pi/4)
            self.turns[k]=self.cube._pose_index.get(frame_key(multiply(turn,self.cube.orientations[pose])))
        return self.turns[k]

    def describe(self,frames):
        features=tuple(self.feature(h,p) for h,p in enumerate(frames))
        return features,tuple(sorted(f[0] for f in features)),sum(f[1] for f in features)

    def children(self,frames,features,last=None,guard=None):
        available=self.all_mask
        for f in features:available&=f[2]
        proper=proper_poses('mixup')
        for bit,(axis,layers) in enumerate(self.ranges):
            if guard:guard()
            if (axis,layers) not in self.search_ranges:continue
            layer=layers[0]
            if not available>>bit&1 or (axis,layers)==last:continue
            selected=[h for h,f in enumerate(features) if f[3]>>bit&1]
            if not selected:continue
            step=2 if 0 in layers or len(self.cuts[axis]) in layers else 1
            for amount in range(step,8,step):
                child=list(frames);valid=True
                for home in selected:
                    pose=self.next_pose(axis,amount,frames[home])
                    if pose is None or self.cube.solids[home].role=='corner' and pose not in proper:
                        valid=False;break
                    child[home]=pose
                if valid:yield tuple(child),(Move(axis,layer,amount) if len(layers)==1 else MixupSliceMove(axis,layer,amount,layers))

    def apply(self,frames,features,move):
        layers=getattr(move,'layers',()) or (move.layer,)
        bit=self.ranges.index((move.axis,tuple(layers)));flag=1<<bit
        if any(not f[2]&flag for f in features):return None
        child=list(frames);proper=proper_poses('mixup')
        selected=False
        for home,f in enumerate(features):
            if not f[3]&flag:continue
            selected=True;pose=self.next_pose(move.axis,move.amount,frames[home])
            if pose is None or self.cube.solids[home].role=='corner' and pose not in proper:return None
            child[home]=pose
        if not selected:return None
        child=tuple(child);return child,self.describe(child)[0]

    def macro_children(self,frames,features,guard=None,compound=False):
        for a,move_a in self.children(frames,features,guard=guard):
            if move_a.amount not in (1,7):continue
            fa=self.describe(a)[0]
            for b,move_b in self.children(a,fa,guard=guard):
                if move_b.amount!=4 or move_b.axis==move_a.axis:continue
                result=self.apply(b,self.describe(b)[0],move_a.inverse(8))
                if result is not None:yield result[0],result[1],(move_a,move_b,move_a.inverse(8))
            for b,move_b in self.children(a,fa,guard=guard):
                if move_b.amount not in ((1,7) if compound else (2,6)) or move_b.axis==move_a.axis:continue
                fb=self.describe(b)[0]
                for c,move_c in self.children(b,fb,guard=guard):
                    if move_c.amount not in (2,4,6) or move_c.axis==move_b.axis:continue
                    fc=self.describe(c)[0]
                    d=self.apply(c,fc,move_b.inverse(8))
                    if d is None:continue
                    e=self.apply(*d,move_a.inverse(8))
                    if e is not None:yield e[0],e[1],(move_a,move_b,move_c,move_b.inverse(8),move_a.inverse(8))
                    d2=self.apply(*d,move_c.inverse(8))
                    if d2 is None:continue
                    e2=self.apply(*d2,move_a.inverse(8))
                    if e2 is not None:yield e2[0],e2[1],(move_a,move_b,move_c,move_b.inverse(8),move_c.inverse(8),move_a.inverse(8))

    def long_macro_children(self,frames,features,guard=None):
        for child,fs,word in self.macro_children(frames,features,guard):
            if len(word)!=5:continue
            inverse=tuple(m.inverse(8) for m in reversed(word))
            # Conjugate a proper turn by a Mixup insertion. This turns the
            # wedge itself and can repair Plus inner-edge orientation.
            b=word[1];d=b.inverse(8)
            opposite=len(self.cuts[b.axis])-b.layer
            for middle in ((d,), (d,Move(b.axis,opposite,b.amount)),(d,Move(b.axis,opposite,d.amount))):
                trial=child,fs
                for move in middle+inverse:
                    trial=self.apply(*trial,move)
                    if trial is None:break
                if trial is not None:yield trial[0],trial[1],word+middle+inverse

    def proper_macro_children(self,frames,features,long=False):
        for a,ma in self.children(frames,features):
            if ma.amount not in (2,6):continue
            fa=self.describe(a)[0]
            for b,mb in self.children(a,fa):
                if mb.amount not in (2,6) or mb.axis==ma.axis:continue
                fb=self.describe(b)[0]
                if not long:
                    trial=self.apply(b,fb,ma.inverse(8))
                    if trial is not None:trial=self.apply(*trial,mb.inverse(8))
                    if trial is not None:yield trial[0],trial[1],(ma,mb,ma.inverse(8),mb.inverse(8))
                    continue
                for c,mc in self.children(b,fb):
                    if mc.amount not in (2,4,6) or mc.axis==mb.axis:continue
                    word=(ma,mb,mc,mb.inverse(8),ma.inverse(8),mb,mc.inverse(8),mb.inverse(8))
                    trial=c,self.describe(c)[0]
                    for move in word[3:]:
                        trial=self.apply(*trial,move)
                        if trial is None:break
                    if trial is not None:yield trial[0],trial[1],word


def greedy_geometry(cube,cancel=None,seconds=30.):
    model=geometry(cube.puzzle_kind);started=monotonic();s=cube.frames;f,_,_=model.describe(s);path=[]
    def score(features):return sum(v[1] for v in features)
    bad=score(f)
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>seconds:raise ReductionLimit(s,path)
    for it in range(100):
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>seconds:raise ReductionLimit(s,path)
        if bad==0:
            work=cube.clone();work.apply_moves(path);return tuple(path),work,it
        if bad in (2,4,6,8) and 'mixup_plus_' in cube.puzzle_kind:
            trial=cube.clone();trial.colors=s
            try:finish,work=finish_inner_orientation(trial,cancel,seconds=min(20.,max(.1,seconds-(monotonic()-started))))
            except ValueError:pass
            else:
                replay=cube.clone();replay.apply_moves(tuple(path)+finish)
                return tuple(path)+finish,replay,it
        best=(bad,100,None)
        for child,mv in model.children(s,f):
            fs,_,_=model.describe(child);b=score(fs)
            if (b,1)<best[:2]:best=(b,1,(child,fs,(mv,)))
        if best[0]>=bad:
            for child,fs,word in model.macro_children(s,f,guard=guard):
                b=score(fs)
                if (b,len(word))<best[:2]:best=(b,len(word),(child,fs,word))
                if b<bad and cube.puzzle_kind=='mixup_plus_444':break
        if best[0]>=bad:
            for child,fs,word in model.macro_children(s,f,guard=guard,compound=True):
                b=score(fs)
                if b<bad:best=(b,len(word),(child,fs,word));break
        if best[0]>=bad:
            for child,fs,word in model.long_macro_children(s,f,guard=guard):
                b=score(fs)
                if (b,len(word))<best[:2]:best=(b,len(word),(child,fs,word))
                if b<bad and cube.puzzle_kind=='mixup_plus_444':break
        if best[0]>=bad:
            # Neutral setup turns relocate isolated tilted strips. An odd
            # turn may exchange which strip is tilted without increasing it.
            setups=[(s,f,())];visited={tuple(s)}
            for setup_depth in range(2):
                next_setups=[]
                for state,fs,prefix in setups:
                    if cancel and cancel():raise InterruptedError()
                    if monotonic()-started>seconds:raise ValueError('mixup.shape_limit')
                    for child,move in model.children(state,fs):
                        ff,_,_=model.describe(child);key=tuple(child);value=score(ff)
                        if value!=bad or key in visited:continue
                        visited.add(key);word=prefix+(move,)
                        next_setups.append((child,ff,word))
                        for dest,df,tail in model.macro_children(child,ff,guard=guard):
                            b=score(df)
                            if b<bad:best=(b,len(word+tail),(dest,df,word+tail));break
                        if best[0]>=bad:
                            for dest,df,tail in model.long_macro_children(child,ff,guard=guard):
                                b=score(df)
                                if b<bad:best=(b,len(word+tail),(dest,df,word+tail));break
                        if best[0]<bad:break
                    if best[0]<bad:break
                if best[0]<bad:break
                setups=next_setups
            if best[0]>=bad:
                raise ReductionLimit(s,path)
        bad,_,(s,f,word)=best;path.extend(word)


    raise ValueError('mixup.shape_limit')

@lru_cache(maxsize=2)
def geometry(kind):return ReductionGeometry(kind)


def restore_layout(cube,cancel=None,seconds=45.,limit=150000,macros=True):
    """Meet in the colourless graph of cube-shaped layer partitions."""
    model=geometry(cube.puzzle_kind);started=monotonic()
    from itertools import chain
    # A manually held cuboid has no privileged long axis. Align that axis
    # before searching local partitions; whole rotations remain physical moves.
    orientation,aligned=align_layout_axes(cube,cancel)
    start=tuple(aligned.frames);goal=(0,)*len(start)
    sf,sk,_=model.describe(start);gf,gk,_=model.describe(goal)
    if sk==gk:return orientation,aligned,0
    parents=[{sk:(None,())},{gk:(None,())}];targets=[set(gk),set(sk)]
    fronts=[[],[]];serial=count();nodes=0
    for side,(frames,fs,k) in enumerate(((start,sf,sk),(goal,gf,gk))):
        score=sum(f[0] not in targets[side] for f in fs)
        heappush(fronts[side],(score,0,next(serial),frames,fs,k))
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>seconds or sum(map(len,parents))>limit:raise ValueError('mixup.shape_limit')
    while all(fronts):
        direction=nodes%2;other=1-direction
        _,depth,_,frames,features,key=heappop(fronts[direction])
        if cancel and cancel():raise InterruptedError()
        if monotonic()-started>seconds or sum(map(len,parents))>limit:raise ValueError('mixup.shape_limit')
        nodes+=1
        singles=((ch,model.describe(ch)[0],(mv,)) for ch,mv in model.children(frames,features) if mv.amount in (2,4,6))
        for child,fs,word in chain(singles,model.macro_children(frames,features,guard) if macros else ()):
            if any(f[1] for f in fs):continue
            ck=model.describe(child)[1]
            if ck in parents[direction]:continue
            parents[direction][ck]=key,word
            if ck in parents[other]:
                def path(side):
                    here=ck;chunks=[]
                    while parents[side][here][0] is not None:
                        here,w=parents[side][here];chunks.append(w)
                    return tuple(m for chunk in reversed(chunks) for m in chunk)
                forward=path(0);back=path(1)
                result=forward+tuple(m.inverse(8) for m in reversed(back))
                result=orientation+result
                work=cube.clone();work.apply_moves(result)
                if model.describe(work.frames)[1]!=gk:raise ValueError('mixup.replay_failed')
                return result,work,nodes
            score=sum(f[0] not in targets[direction] for f in fs)
            cost=depth+len(word)
            heappush(fronts[direction],(score+cost*.15,cost,next(serial),child,fs,ck))
    raise ValueError('mixup.shape_limit')


def align_layout_axes(cube,cancel=None):
    from collections import deque
    model=geometry(cube.puzzle_kind)
    root=tuple(cube.frames);queue=deque([(root,())]);seen={root[0]};best=None
    while queue:
        frames,path=queue.popleft()
        if cancel and cancel():raise InterruptedError()
        fs,_,_=model.describe(frames);score=sum(f[0] not in model.goals for f in fs)
        if best is None or (score,len(path))<best[:2]:best=(score,len(path),frames,path)
        for axis in range(3):
            child=tuple(model.next_pose(axis,2,p) for p in frames)
            if child[0] in seen:continue
            seen.add(child[0]);layers=tuple(range(len(model.cuts[axis])+1))
            queue.append((child,path+(MixupSliceMove(axis,0,2,layers),)))
    work=cube.clone();work.apply_moves(best[3])
    return best[3],work


def restore_composite_layout(cube,cancel=None):
    """Use the 3x3 mechanism to position whole or subdivided assemblies."""
    from solver.mixup_group import load_group
    from cube.articulated import MIXUP_MODELS
    from pathlib import Path
    import json,math
    plus=MIXUP_MODELS[cube.puzzle_kind][1]
    group=load_group('mixup_plus_333' if plus else 'mixup_333')
    model=geometry(cube.puzzle_kind);root=model.cube
    word=group.transport_values(composite_counts(cube,group),composite_counts(root,group),cancel)
    path=[];work=cube.clone()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        size=len(work.geometry.layers[move.axis])
        source_layers=getattr(move,'layers',()) or (move.layer,)
        layers=tuple(l for src in source_layers for l in ((0,) if src==0 else (size-1,) if src==2 else tuple(range(1,size-1))))
        mapped=Move(move.axis,layers[0],move.amount) if len(layers)==1 else MixupSliceMove(move.axis,layers[0],move.amount,layers)
        work.apply_move(mapped);path.append(mapped)
    # Core-identity words turn a rectangular centre seam without disturbing
    # the now correctly positioned edge and inner-edge assemblies.
    table=json.loads((Path(__file__).resolve().parents[1]/'assets/mixup_center_finish.json').read_text())
    goal=model.describe((0,)*len(root.solids))[1]
    from solver.mixup import translate_token
    for mask,tokens in sorted(table['words'].items(),key=lambda item:len(item[1])):
        if cancel and cancel():raise InterruptedError()
        frames=list(work.frames);mask=int(mask)
        for h,solid in enumerate(work.solids):
            if solid.role!='centre':continue
            c=next(c for p,c in solid.faces if c>=0);frame=work.orientations[frames[h]]
            normal=transform_frame(frame,CUBE[c]);face=max(range(6),key=lambda f:dot(normal,CUBE[f]))
            if mask>>face&1:frames[h]=work._pose_index[frame_key(multiply(turn_frame(CUBE[face],math.pi/2),frame))]
        if model.describe(frames)[1]!=goal:continue
        for token in tokens:
            if cancel and cancel():raise InterruptedError()
            for move in translate_token(work,token,3):work.apply_move(move);path.append(move)
        if model.describe(work.frames)[1]!=goal:raise ValueError('mixup.replay_failed')
        return tuple(path),work,0
    raise ValueError('mixup.shape_limit')


def composite_counts(cube,group):
    template=[]
    for home in range(len(group.model.cube.solids)):
        for poly,c in group.model.cube.placed_faces(home):
            if c>=0:template.append(tuple((min(p[a] for p in poly),max(p[a] for p in poly)) for a in range(3)))
    def counts(state):
        values=[0]*len(template)
        for home in range(len(state.solids)):
            for poly,c in state.placed_faces(home):
                if c<0:continue
                bounds=tuple((min(p[a] for p in poly),max(p[a] for p in poly)) for a in range(3))
                slots=[i for i,box in enumerate(template) if all(lo>=box[a][0]-1e-7 and hi<=box[a][1]+1e-7 for a,(lo,hi) in enumerate(bounds))]
                if len(slots)!=1:raise ValueError('mixup.shape_limit')
                values[slots[0]]+=1
        if any(v==0 for v in values):raise ValueError('mixup.shape_limit')
        return values
    return counts(cube)


def repair_inner_layout(cube,cancel=None):
    from solver.mixup_group import load_group
    group=load_group('mixup_plus_333');root=geometry(cube.puzzle_kind).cube
    word=group.inner_pattern_word(composite_counts(cube,group),composite_counts(root,group),cancel)
    path=[];work=cube.clone()
    for move in word:
        if cancel and cancel():raise InterruptedError()
        size=len(work.geometry.layers[move.axis]);sources=getattr(move,'layers',()) or (move.layer,)
        layers=tuple(l for src in sources for l in ((0,) if src==0 else (size-1,) if src==2 else tuple(range(1,size-1))))
        mapped=Move(move.axis,layers[0],move.amount) if len(layers)==1 else MixupSliceMove(move.axis,layers[0],move.amount,layers)
        work.apply_move(mapped);path.append(mapped)
    return tuple(path),work


def finish_inner_orientation(cube,cancel=None,seconds=20.,limit=20000):
    """Meet a legal inner-flip primitive through ordinary setup turns."""
    model=geometry(cube.puzzle_kind);begun=monotonic();root=(0,)*len(cube.solids)
    target=model.describe(cube.frames)[1];wanted=set(target);rf=model.describe(root)[0]
    frontier=[];parents={};forward={};serial=count()
    def guard():
        if cancel and cancel():raise InterruptedError()
        if monotonic()-begun>seconds or len(parents)+len(forward)>limit:raise ValueError('mixup.shape_limit')
    for frames,fs,word in model.long_macro_children(root,rf,guard):
        if not any(f[1] for f in fs) or any(f[1] and cube.solids[h].role!='inner_edge' for h,f in enumerate(fs)):continue
        key=model.describe(frames)[1]
        if key in parents:continue
        parents[key]=(None,word)
        heappush(frontier,(sum(f[0] not in wanted for f in fs),len(word),next(serial),frames,fs,key))
    forward={target:(None,())};ff=model.describe(cube.frames)[0]
    fronts=[[(0,0,next(serial),tuple(cube.frames),ff,target)],frontier]
    trees=[forward,parents];nodes=0
    while all(fronts):
        guard();side=nodes%2;other=1-side;nodes+=1
        _,cost,_,frames,fs,key=heappop(fronts[side])
        if key in trees[other]:
            def collect(which):
                here=key;chunks=[]
                while here is not None:here,word=trees[which][here];chunks.append(word)
                return tuple(m for chunk in reversed(chunks) for m in chunk)
            prefix=collect(0);back=collect(1)
            word=prefix+tuple(m.inverse(8) for m in reversed(back));work=cube.clone();work.apply_moves(word)
            if any(f[1] for f in model.describe(work.frames)[0]):raise ValueError('mixup.replay_failed')
            return word,work
        singles=((ch,model.describe(ch)[0],(mv,)) for ch,mv in model.children(frames,fs))
        from itertools import chain
        macros=model.long_macro_children(frames,fs,guard) if side==0 and nodes==1 else ()
        for child,cf,word in chain(singles,macros):
            _,ck,_=model.describe(child)
            if sum(f[1] for f in cf) not in (2,4):continue
            if ck in trees[side]:continue
            trees[side][ck]=(key,word)
            heuristic=sum(f[0] not in wanted for f in cf) if side else 0
            heappush(fronts[side],(heuristic+(cost+len(word))*.05,cost+len(word),next(serial),child,cf,ck))
    raise ValueError('mixup.shape_limit')


def restore_plus_layout(cube,cancel=None):
    # The core partitions obey the ordinary model. Whole inner assemblies
    # are independently cycled away from any obstructed half-layer cut.
    ordinary_kind=cube.puzzle_kind.replace('mixup_plus_','mixup_')
    frames=[p for h,p in enumerate(cube.frames) if cube.solids[h].role!='inner_edge']
    core=MixupCube(ordinary_kind,frames)
    core_word,_,_=restore_composite_layout(core,cancel) if ordinary_kind.endswith('334') else restore_layout(core,cancel,seconds=30.)
    work=cube.clone();path=[]
    for move in core_word:
        if cancel and cancel():raise InterruptedError()
        if not work.can_apply(move):
            preparation,work=repair_inner_layout(work,cancel);path.extend(preparation)
        work.apply_move(move);path.append(move)
    preparation,work=repair_inner_layout(work,cancel);path.extend(preparation)
    goal=geometry(cube.puzzle_kind).describe((0,)*len(cube.solids))[1]
    if geometry(cube.puzzle_kind).describe(work.frames)[1]!=goal:raise ValueError('mixup.shape_limit')
    return tuple(path),work,0
