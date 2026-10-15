"""Audit every imported case against the application's actual puzzle models."""
import json
from pathlib import Path
import sys
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.algorithm_library import prepare_algorithm, verify_case_scope
from scripts.formula_catalog_rules import curate


def main():
    path = Path('demo/data/speedcubedb.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    counts = Counter()
    failures = []
    for group in data['sets']:
        curate(group)
        puzzle = group['puzzle']
        for item in group['cases']:
            errors = []
            for index, algorithm in enumerate(item['algorithms']):
                try:
                    cube, moves = prepare_algorithm(puzzle, algorithm)
                    verify_case_scope(puzzle, group['id'].split('/')[1], cube)
                    for move in moves:
                        cube.apply_move(move)
                    if not cube.is_solved():
                        raise ValueError('Replay did not restore its initial solved reference')
                    item['selected'] = index
                    item.pop('error', None)
                    counts[puzzle] += 1
                    break
                except (ValueError, KeyError, IndexError) as exc:
                    errors.append(f'{algorithm}: {exc}')
            else:
                item.pop('selected', None)
                item['error'] = errors[0].split(': ', 1)[-1] if errors else 'No compatible alternative'
                failures.append({'set': group['id'], 'name': item['name'], 'errors': errors})
        print(group['id'], counts[puzzle], flush=True)
    report = {'playable': dict(counts), 'failures': failures}
    destination = Path('reports/formula-library/2026-10-16.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    from scripts.build_formula_finishes import build
    build()
    print(json.dumps({'playable': dict(counts), 'failures': len(failures)}), flush=True)


if __name__ == '__main__':
    main()
