"""Bounded in-process search checkpoints; no callbacks or histories saved."""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass,field
from threading import Lock,local,get_ident

MAX_CHECKPOINTS=2
MAX_SEEN=50000
MAX_STAGE_MOVES=20000
_entries=OrderedDict();_stages=OrderedDict();_lock=Lock();_reporter=local()


@dataclass
class Checkpoint:
    start:object
    bound:object=None
    expanded:int=0
    elapsed:float=0.
    attempts:int=0
    following:float=float('inf')
    seen:dict=field(default_factory=dict)
    active:set=field(default_factory=set)
    path:list=field(default_factory=list)
    stack:list=field(default_factory=list)
    lease:object=field(default_factory=Lock,repr=False)
    owner:object=None


@contextmanager
def reporting(callback):
    previous=getattr(_reporter,'callback',None);_reporter.callback=callback
    try:yield
    finally:_reporter.callback=previous


def report(**values):
    callback=getattr(_reporter,'callback',None)
    if callback:callback(dict(label='solver.continuing',search=values))


@contextmanager
def checkpoint(namespace,start,cancel=None):
    stamp=(namespace,start)
    waiting=False
    with _lock:
        item=_entries.get(stamp) if namespace is not None else None
        if item is None:item=Checkpoint(start)
        if not item.lease.acquire(blocking=False):
            if item.owner==get_ident():
                # Reentrant development calls cannot wait for their own lease.
                item=Checkpoint(start);item.lease.acquire();stamp=None
            else:waiting=True
        elif namespace is not None:
            _entries[stamp]=item;_entries.move_to_end(stamp)
            while len(_entries)>MAX_CHECKPOINTS:_entries.popitem(last=False)
    if waiting:
        # The previous cancelled worker is still unwinding. Wait off the UI
        # thread, instead of silently starting the exact same search afresh.
        while not item.lease.acquire(timeout=.05):
            if cancel and cancel():raise InterruptedError()
        with _lock:
            _entries[stamp]=item;_entries.move_to_end(stamp)
            while len(_entries)>MAX_CHECKPOINTS:_entries.popitem(last=False)
    item.owner=get_ident()
    try:
        item.attempts+=1;yield item
    except (InterruptedError,TimeoutError):raise
    except BaseException:
        discard(stamp,item);raise
    else:discard(stamp,item)
    finally:item.owner=None;item.lease.release()


def discard(stamp,item):
    with _lock:
        if _entries.get(stamp) is item:_entries.pop(stamp,None)


def stage(namespace,payload=None,*,remove=False):
    with _lock:
        if remove:return _stages.pop(namespace,None)
        if payload is not None:
            if len(payload)>MAX_STAGE_MOVES:return _stages.get(namespace)
            _stages[namespace]=payload;_stages.move_to_end(namespace)
            while len(_stages)>MAX_CHECKPOINTS:_stages.popitem(last=False)
        return _stages.get(namespace)


def clear():
    with _lock:_entries.clear();_stages.clear()
