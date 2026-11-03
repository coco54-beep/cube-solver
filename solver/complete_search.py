"""Cancellable finite-graph cost deepening with resumable explicit stacks."""
from time import monotonic
from solver.search_resume import checkpoint,report,MAX_SEEN


class Exhausted(ValueError):
    """Every reachable branch was exhausted, rather than timed out."""


def deepen(start,goal,children,estimate,*,cancel=None,progress=None,key=None,
           cache_limit=120000,resume_key=None,seconds=None):
    """Retain exact data/cursors on pause; new attempts use new callbacks.

    A full cache stops storing, never removes unexplored branches. Checkpoints
    live only in this process; at most two states are retained. Changed input
    cannot reuse them. No generator, closure or cancellation token is saved.
    """
    key=key or (lambda state:state)
    if resume_key is not None:cache_limit=min(cache_limit,MAX_SEEN)
    with checkpoint(resume_key,start,cancel) as saved:
        begun=monotonic();last_update=-float('inf')
        def guard():
            nonlocal last_update
            if cancel and cancel():raise InterruptedError()
            now=monotonic()
            if seconds is not None and now-begun>=seconds:raise TimeoutError('solver.timeout')
            if now-last_update>=.2:
                if progress:progress(saved.bound,saved.expanded)
                report(bound=saved.bound,expanded=saved.expanded,
                       seconds=saved.elapsed+now-begun,resumed=saved.attempts>1)
                last_update=now
                # A progress handler can request a pause in this very call.
                if cancel and cancel():raise InterruptedError()
        def pop():
            saved.stack.pop()
            if saved.stack:saved.path.pop()
        try:
            if saved.bound is None:saved.bound=estimate(start)
            while True:
                guard()
                if not saved.stack:saved.stack=[[start,0,None,0,None]]
                while saved.stack:
                    guard();entry=saved.stack[-1]
                    state,depth,candidates,cursor,state_key=entry
                    if candidates is None:
                        value=depth+estimate(state)
                        if value>saved.bound:
                            saved.following=min(saved.following,value);pop();continue
                        suffix=goal(state)
                        if suffix is not None:return tuple(saved.path)+tuple(suffix)
                        state_key=key(state)
                        if state_key in saved.active or saved.seen.get(state_key,float('inf'))<=depth:
                            pop();continue
                        # Commit only after generation: cancellation inside
                        # children leaves an unentered frame safe to retry.
                        candidates=list(children(state))
                        candidates.sort(key=lambda item:estimate(item[0]))
                        if len(saved.seen)<cache_limit or state_key in saved.seen:saved.seen[state_key]=depth
                        saved.active.add(state_key);saved.expanded+=1
                        entry[2]=candidates;entry[4]=state_key
                    if entry[3]>=len(candidates):
                        saved.active.remove(state_key);pop();continue
                    child,move=candidates[entry[3]];entry[3]+=1
                    saved.path.append(move);saved.stack.append([child,depth+1,None,0,None])
                if saved.following==float('inf'):raise Exhausted('Search graph exhausted')
                saved.bound=max(saved.bound+1,saved.following)
                saved.following=float('inf');saved.seen.clear();saved.active.clear()
        finally:saved.elapsed+=monotonic()-begun
