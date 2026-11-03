"""Complete shortest half-turn search on the ordinary 192-state Floppy."""
from collections import deque
from cube.cuboid import CuboidCube
from solver.messages import tr


def solve_floppy(cube,cancel=None,progress=None):
    def check():
        if cancel and cancel():raise InterruptedError()
    check()
    goal=bytes(CuboidCube.solved('floppy_133').colors);start=bytes(cube.colors)
    if start==goal:return ()
    moves=cube.moves();actions=[cube.geometry.inverse_permutation(m) for m in moves]
    todo=deque((start,));seen={start:None};previous={}
    while todo:
        check();state=todo.popleft()
        for index,action in enumerate(actions):
            child=bytes(state[i] for i in action)
            if child in seen:continue
            seen[child]=state;previous[child]=moves[index]
            if child==goal:
                result=[]
                while seen[child] is not None:result.append(previous[child]);child=seen[child]
                result=tuple(reversed(result));trial=cube.clone()
                for move in result:check();trial.apply_move(move)
                if not trial.is_solved():raise ValueError(tr('cuboid.replay_failed'))
                if progress:progress(1,1)
                return result
            todo.append(child)
    raise ValueError(tr('cuboid.identity_unreachable'))
