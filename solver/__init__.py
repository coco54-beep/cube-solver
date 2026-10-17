"""求解器包：2x2、3x3、4x4 与 5x5 还原。"""

from importlib import import_module

# Importing an irregular solver or SolveResult must not initialise ordinary
# cube tables. Keep the public exports, loading each only when requested.
_EXPORTS={
    'solve_3x3':'solver.solver3',
    'solve_4x4':'solver.solver4','solve_4x4_facelets':'solver.solver4',
    'solve_2x2':'solver.solver2','solve_2x2_facelets':'solver.solver2',
    'CenterSolveError':'solver.reduction','CenterSolver4':'solver.reduction',
    'solve_centers':'solver.reduction',
    'solve_5x5':'solver.solver5','solve_5x5_facelets':'solver.solver5',
}
__all__=list(_EXPORTS)

def __getattr__(name):
    if name in _EXPORTS:
        value=getattr(import_module(_EXPORTS[name]),name)
        globals()[name]=value
        return value
    raise AttributeError("module 'solver' has no attribute %r" % name)
