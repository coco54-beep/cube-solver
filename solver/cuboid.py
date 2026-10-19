"""Bounded cuboid restoration; never substitute ordinary cube moves illegally."""
from collections import Counter,deque
from time import monotonic
from cube.cuboid import CuboidCube
from solver.polyhedral import inverse_word,simplify


def validate_cuboid(cube):
 from app.i18n import tr
 goal=CuboidCube.solved(cube.puzzle_kind)
 # Compare physical panels, rather than the virtual backing-cell counts.
 values=[cube.colors[i] for i in cube.panels()]
 if any(type(c) is not int or not 0<=c<6 for c in values) or Counter(values)!=Counter(goal.colors[i] for i in goal.panels()):
  raise ValueError(tr('cuboid.colours'))
 for slots in cube._panel_groups(cube.geometry).values():
  if len({cube.colors[i] for i in slots})!=1:raise ValueError(tr('cuboid.colours'))
 return True


def solve_cuboid(cube,cancel=None,progress=None):
 from app.i18n import tr
 validate_cuboid(cube)
 if cube.puzzle_kind=='cuboid_133':
  from solver.super_floppy import solve_super_floppy
  return solve_super_floppy(cube,cancel,progress)
 if cube.is_solved():return ()
 def replay(word):
  state=cube.clone()
  for move in word:
   if cancel and cancel():raise InterruptedError()
   if not state.can_apply(move):return False
   state.apply_move(move)
  return state.is_solved()
 history=cube.history
 if history is not None:
  word=simplify(inverse_word(history,4),4)
  # Only neighbouring turns on one axis are combined; bonded pieces remain
  # intact throughout replay. A changed painted input cannot use stale history.
  if replay(word):
   if progress:progress(1,1)
   return word
 # Small manual states have a bounded search; deep input needs a dedicated
 # reduction. Do not label a timeout as mathematical unsolvability.
 deadline=monotonic()+3.;queue=deque([(cube.entered(),())]);seen=set();expanded=0
 while queue and expanded<2000 and monotonic()<deadline:
  if cancel and cancel():raise InterruptedError()
  state,word=queue.popleft();signature=(tuple(state.colors),state.frames)
  if signature in seen:continue
  seen.add(signature);expanded+=1
  if state.is_solved():
   if progress:progress(1,1)
   return word
  if len(word)>=3:continue
  for atom in state.moves():
   if word and (atom.axis,atom.layer)==(word[-1].axis,word[-1].layer):continue
   for power in range(1,state.geometry.spec.order(atom.axis)):
    from cube.polyhedral import Move
    move=Move(atom.axis,atom.layer,power*state.geometry.spec.step(atom.axis))
    nxt=state.clone();nxt.apply_move(move);nxt.history=None
    queue.append((nxt,word+(move,)))
    if len(queue)>=2000:break
   if len(queue)>=2000:break
 raise ValueError(tr('cuboid.search_limit'))
