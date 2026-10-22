"""State-based cuboid restoration with legal replay on the entered model."""
from collections import Counter
from cube.cuboid import CuboidCube, FIXED_SHAPE_KINDS
from solver.polyhedral import inverse_word,simplify


def validate_cuboid(cube):
 from solver.messages import tr
 goal=CuboidCube.solved(cube.puzzle_kind)
 # Compare physical panels, rather than the virtual backing-cell counts.
 values=[cube.colors[i] for i in cube.panels()]
 if any(type(c) is not int or not 0<=c<6 for c in values) or Counter(values)!=Counter(goal.colors[i] for i in goal.panels()):
  raise ValueError(tr('cuboid.colours'))
 for slots in cube._panel_groups(cube.geometry).values():
  if len({cube.colors[i] for i in slots})!=1:raise ValueError(tr('cuboid.colours'))
 return True


def solve_cuboid(cube,cancel=None,progress=None):
 from solver.messages import tr
 if cancel and cancel():raise InterruptedError()
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
 if cube.puzzle_kind in FIXED_SHAPE_KINDS:
  from solver.cuboid_static import solve_fixed_cuboid
  solve=solve_fixed_cuboid
 elif getattr(cube,'panel_anchored',False):
  from solver.cuboid_extended import solve_extended_cuboid
  solve=solve_extended_cuboid
 else:
  from solver.cuboid_search import solve_bandaged_cuboid
  solve=solve_bandaged_cuboid
 try:return solve(cube,cancel,progress)
 except TimeoutError:raise ValueError(tr('cuboid.search_budget')) from None
 except ValueError as error:
  message=str(error)
  if message.startswith('cuboid.'):
   raise ValueError(tr(message)) from None
  raise
