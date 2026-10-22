"""Mixup reduction: restore the real shell, then invoke 3x3/4x4 solving."""
from time import monotonic
from cube.articulated import MIXUP_MODELS,frame_key
from cube.appearance import ROTATIONS,transform_frame
from cube.polyhedral import Move,CUBE,mean
from solver.result import SolveResult,SolveStage

FACES=('U','R','F','D','L','B')


def valid_center_frame(facelets):
    """A 3x3 handoff needs a proper spatial centre arrangement."""
    from cube.colors import DEFAULT_COLORS
    colours={v:i for i,v in enumerate(DEFAULT_COLORS[f] for f in FACES)}
    try:centres=[colours[facelets[f][1][1]] for f in FACES]
    except (KeyError,IndexError):return False
    return any(all(sum(a*b for a,b in zip(transform_frame(rotation,CUBE[colour]),CUBE[face]))>1-1e-7
                   for face,colour in enumerate(centres)) for rotation in ROTATIONS)

def project_cube(cube,verify=True):
    """A single virtual facelet must contain one colour across ALL panels.

    Mixed 334/344 models first join their split inner pieces, then reduce to
    3x3. A genuine 444 model retains its four layers and reduces to 4x4.
    """
    from cube.mixup import _area,skins_cross
    faces=[[] for _ in range(6)]
    for home,pose in enumerate(cube.frames):
        frame=cube.orientations[pose]
        for poly,colour in cube.placed_faces(home):
            if colour<0:continue
            direction=transform_frame(frame,CUBE[colour])
            face=next((f for f,n in enumerate(CUBE) if sum(a*b for a,b in zip(direction,n))>1-1e-7),None)
            if face is None or any(abs(v)>1+1e-7 for p in poly for v in p):raise ValueError('mixup.shape_first')
            faces[face].append((poly,colour))
    for panels in faces:
        if abs(sum(_area(poly) for poly,colour in panels)-4)>1e-6:raise ValueError('mixup.shape_first')
        if any(skins_cross((p,),(q,)) for i,p in enumerate(panels) for q in panels[i+1:]):raise ValueError('mixup.shape_first')
    dimensions,plus=MIXUP_MODELS[cube.puzzle_kind];n=4 if dimensions==(4,4,4) else 3
    from cube.cube3 import Cube3
    from cube.cube4 import Cube4
    from cube.coordinates import coord_values
    from cube.colors import DEFAULT_COLORS
    virtual=Cube4.solved() if n==4 else Cube3.solved();values=coord_values(n)
    depth=(2*2**.5-1)/7 if plus else 2**.5-1
    bounds=(-depth,0.,depth) if n==4 else (-depth,depth);cells={}
    for home,pose in enumerate(cube.frames):
        frame=cube.orientations[pose]
        for polygon,color in cube.placed_faces(home):
            if color<0:continue
            normal=tuple(round(x) for x in transform_frame(frame,CUBE[color]));point=mean(polygon)
            for axis in range(3):
                if normal[axis]:continue
                lo=min(p[axis] for p in polygon);hi=max(p[axis] for p in polygon)
                if any(lo<b-1e-7 and hi>b+1e-7 for b in bounds):raise ValueError('mixup.pair_first')
            pos=tuple(normal[a]*values[-1] if normal[a] else values[sum(point[a]>b+1e-7 for b in bounds)] for a in range(3))
            cells.setdefault((pos,normal),set()).add(DEFAULT_COLORS[FACES[color]])
    for pos,cubie in virtual.cubies.items():
        for normal in cubie.stickers:
            colors=cells.get((pos,normal),())
            if len(colors)!=1:raise ValueError('mixup.pair_first')
            cubie.stickers[normal]=next(iter(colors))
    if n==3 and verify:
        from cube.conversion import cubies_to_facelets
        from solver.solver3 import verify_3x3
        try:
            facelets=cubies_to_facelets(virtual.cubies,3)
            valid=valid_center_frame(facelets) and verify_3x3(facelets)[0]
        except (KeyError,ValueError):valid=False
        if not valid:raise ValueError('mixup.pair_first')
    elif n==4:
        # The 4x4 centre solver uses colour-derived home faces. Merely
        # painting a solved Cube4 leaves incorrect home metadata behind.
        from solver.solver4 import _rebuild_center_homes
        _rebuild_center_homes(virtual.cubies)
    return virtual

def _restore_shape(cube,cancel,progress):
    def ready(state):
        try:return project_cube(state)
        except ValueError:return None
    virtual=ready(cube)
    if virtual is not None:return (),cube.clone(),virtual
    work=cube.clone();prefix=[]
    # Use a valid recorded path only to reach the reduction boundary. Never
    # return its complete inverse as a substitute for ordinary colour solving.
    if cube.history and cube.frames==cube._history_snapshot:
        try:
            for move in reversed(cube.history):
                if cancel and cancel():raise InterruptedError()
                inverse=move.inverse(8);work.apply_move(inverse);prefix.append(inverse)
                virtual=ready(work)
                if virtual is not None:return tuple(prefix),work,virtual
        except ValueError:pass
    from solver.mixup_reduction import (greedy_geometry,restore_layout,
        restore_composite_layout,restore_plus_layout,ReductionLimit)
    from solver.mixup_group import load_group,compact
    try:
        prefix,work,_=greedy_geometry(cube,cancel,seconds=120.)
    except ReductionLimit as limit:
        prefix=list(limit.path)
        work=cube.clone()
        for move in prefix:
            if cancel and cancel():raise InterruptedError()
            work.apply_move(move)
    virtual=ready(work)
    if virtual is not None:return tuple(prefix),work,virtual
    if progress:progress({'label':'mixup.restoring'})
    try:layout,work,_=restore_composite_layout(work,cancel)
    except ValueError:
        if MIXUP_MODELS[cube.puzzle_kind][1]:layout,work,_=restore_plus_layout(work,cancel)
        else:layout,work,_=restore_layout(work,cancel,seconds=60.)
    prefix=prefix+layout
    virtual=ready(work)
    if virtual is not None:return compact(prefix),work,virtual
    paired,work,virtual=load_group(cube.puzzle_kind).restore_colours(
        work,cancel,ready=project_cube,seconds=30.)
    return compact(prefix+paired),work,virtual


def translate_token(cube,token,order):
    from cube.mixup import MixupSliceMove
    from cube.notation import parse_move_full
    from cube.coordinates import FACE_AXIS_SIGN
    label,width,count=parse_move_full(token)
    if label in ('x','y','z'):axis='xyz'.index(label);sign=1;indices=range(len(cube.geometry.layers[axis]))
    else:
        axis,sign=FACE_AXIS_SIGN[label];size=len(cube.geometry.layers[axis])
        if width==order:indices=range(size)
        elif order==3 and width==2:indices=range(1,size) if sign>0 else range(size-1)
        else:indices=range(size-width,size) if sign>0 else range(width)
    indices=tuple(indices);amount=(-2*sign*count)%8
    if len(indices)>1:return (MixupSliceMove(axis,indices[0],amount,indices),)
    return tuple(Move(axis,l,amount) for l in indices)


def align_centres(cube,cancel=None):
    """Restore rectangular centre seams with genuine core-identity words."""
    if cube.is_solved():return ()
    import json,math
    from pathlib import Path
    from cube.articulated import turn_frame,multiply
    table=json.loads((Path(__file__).resolve().parents[1]/'assets/mixup_center_finish.json').read_text(encoding='utf-8'))
    for mask,word in sorted(table['words'].items(),key=lambda item:len(item[1])):
        if cancel and cancel():raise InterruptedError()
        mask=int(mask);frames=list(cube.frames)
        for home,solid in enumerate(cube.solids):
            if solid.role!='centre':continue
            colour=next(c for p,c in solid.faces if c>=0)
            frame=cube.orientations[frames[home]];normal=transform_frame(frame,CUBE[colour])
            face=next((i for i,n in enumerate(CUBE) if sum(a*b for a,b in zip(n,normal))>1-1e-7),None)
            if face is None:raise ValueError('mixup.replay_failed')
            if mask>>face&1:
                frames[home]=cube._pose_index[frame_key(multiply(turn_frame(CUBE[face],math.pi/2),frame))]
        probe=cube.clone();probe.colors=frames
        if not probe.is_solved():continue
        result=[]
        for token in word:
            if cancel and cancel():raise InterruptedError()
            for move in translate_token(cube,token,3):cube.apply_move(move);result.append(move)
        if not cube.is_solved():raise ValueError('mixup.replay_failed')
        return tuple(result)
    raise ValueError('mixup.replay_failed')

def solve_mixup(cube,cancel=None,progress=None):
    started=monotonic()
    if progress:progress({'label':'mixup.restoring'})
    prefix,work,virtual=_restore_shape(cube,cancel,progress)
    from solver.mixup_group import erase_coloured_loops
    shorter=erase_coloured_loops(cube,prefix,cancel)
    if len(shorter)<len(prefix):
        work=cube.clone()
        for move in shorter:
            if cancel and cancel():raise InterruptedError()
            work.apply_move(move)
        virtual=project_cube(work);prefix=shorter
    n=virtual.n
    if cancel and cancel():raise InterruptedError()
    if progress:progress({'label':'mixup.core4' if n==4 else 'mixup.core3'})
    if n==3:
        from cube.conversion import cubies_to_facelets
        from solver.solver3 import solve_3x3
        result=solve_3x3(cubies_to_facelets(virtual.cubies,3))
    else:
        from solver.solver4 import solve_4x4
        class Cancel:
            def is_set(self):return bool(cancel and cancel())
        result=solve_4x4(virtual,cancel_event=Cancel(),progress_callback=progress)
    if not result.success:raise ValueError(result.message)
    tail=[]
    for text in result.moves:
        for token in text.split():
            if cancel and cancel():raise InterruptedError()
            for move in translate_token(work,token,n):work.apply_move(move);tail.append(move)
    # The ordinary projection is only a bridge: the real Mixup must finish
    # with every coloured panel AND its shape restored.
    finish=align_centres(work,cancel)
    tail.extend(finish)
    if not work.is_solved():raise ValueError('mixup.replay_failed')
    moves=tuple(prefix)+tuple(tail)
    replay=cube.clone()
    for move in moves:
        if cancel and cancel():raise InterruptedError()
        replay.apply_move(move)
    if not replay.is_solved():raise ValueError('mixup.replay_failed')
    stages=[SolveStage('mixup_shape','mixup.restoring',list(prefix)),
            SolveStage('mixup_core'+str(n),'mixup.core'+str(n),tail)]
    return SolveResult(True,list(moves),'',int((monotonic()-started)*1000),len(moves),stages)
