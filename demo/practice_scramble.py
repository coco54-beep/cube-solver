"""Case-preserving variations and independently solved practice scrambles."""
from time import monotonic

from demo.formula_notation import compile_algorithm, FormulaCube
from demo.solutions import inverse_demo_move
from demo.irregular_cases import token


def move_text(word, cube):
    spec = getattr(getattr(cube, 'geometry', None), 'spec', None)
    return ' '.join(token(m, spec) for m in word)


def vary_case(puzzle, case, rng):
    case = dict(case)
    cube = case['initial'].clone()
    if puzzle in ('2x2', '3x3'):
        from cube.notation import suffix_for_count
        labels = [(face, rng.randrange(4)) for face in ('U', 'y')]
        text = ' '.join(face + suffix_for_count(count) for face, count in labels if count)
        adjustment = compile_algorithm(puzzle, text) if text else ()
    elif puzzle == 'SQ1':
        top, bottom = rng.randrange(4)*3, rng.randrange(4)*3
        adjustment = compile_algorithm(puzzle, f'{top},{bottom}') if top or bottom else ()
    else:
        count = rng.randrange(3)
        adjustment = compile_algorithm(puzzle, 'y' + ('2' if count == 2 else '')) if count else ()
    for move in adjustment:
        cube.apply_move(move)
    undo = tuple(inverse_demo_move(m, cube) for m in reversed(adjustment))
    case['original_text'] = case['text']
    case['initial'] = cube
    case['moves'] = undo + tuple(case['moves'])
    if undo:
        case['text'] = move_text(undo, cube) + ' ' + case['text']
    return case


def generate_scramble(puzzle, case, cancelled):
    """Return a legal setup matching the visible state, or retain its fallback.

    Run off the UI thread. The independent solve has a bounded search budget;
    a timeout never exposes a different case or an unverified scramble.
    """
    from cube.conversion import cubies_to_facelets
    from demo.algorithm_library import solved
    initial = case['initial']
    deadline = monotonic() + 1.5
    cancel = lambda: cancelled() or monotonic() >= deadline
    if puzzle in ('2x2', '3x3'):
        faces = cubies_to_facelets(initial.cubies, initial.n)
        hold = ()
        if puzzle == '3x3':
            from solver.solver3 import solve_3x3
            result = solve_3x3(faces, timeout=.3)
            reference = FormulaCube(3)
            queue = [(reference, ())]
            seen = set()
            for cube, path in queue:
                if cancel():
                    return None
                f = cubies_to_facelets(cube.cubies, 3)
                centers = tuple(f[name][1][1] for name in faces)
                if centers in seen:
                    continue
                seen.add(centers)
                if all(f[name][1][1] == faces[name][1][1] for name in faces):
                    hold = path
                    break
                for rotation in ('x', 'y'):
                    child = cube.clone()
                    child.apply_move(rotation)
                    queue.append((child, path + (rotation,)))
            else:
                return None
        else:
            from cube.colors import DEFAULT_COLORS
            from demo.cases import TEACHING_COLORS
            from solver.solver2 import solve_2x2_facelets
            color_map = {TEACHING_COLORS[f]: DEFAULT_COLORS[f] for f in TEACHING_COLORS}
            converted = {f: [[color_map[c] for c in row] for row in grid] for f, grid in faces.items()}
            result = solve_2x2_facelets(converted, time_limit=.4)
        if not result.success or cancel():
            return None
        word = hold + tuple(inverse_demo_move(m, initial) for m in reversed(result.moves))
    elif puzzle == 'SQ1':
        from solver.square1 import solve_square1
        result = solve_square1(initial.clone(), cancel=cancel, optimize_budget=0)
        word = tuple(m.inverse() for m in reversed(result))
    else:
        # Pyraminx source notation couples tip and body turns. Retain the
        # varied, verified source setup rather than inventing a native label.
        return None
    if cancel():
        return None
    replay = solved(puzzle)
    for move in word:
        replay.apply_move(move)
    if puzzle in ('2x2', '3x3'):
        if cubies_to_facelets(replay.cubies, replay.n) != cubies_to_facelets(initial.cubies, initial.n):
            return None
    elif replay.slots != initial.slots or replay.middle != initial.middle:
        return None
    return move_text(word, initial)
