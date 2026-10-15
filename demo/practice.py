"""Case selection and a monotonic practice timer, independent of the UI."""
import random
import time
import math

from demo.algorithm_library import groups, prepare_case, family
from demo.solutions import inverse_demo_move
from demo.learning import LearningProgress, FILTERS, case_key

PRACTICE_PUZZLES = ('3x3', '2x2', 'SQ1', 'Pyraminx')
DEFAULT_SETS = {'3x3': 'OLL', '2x2': 'OrtegaOLL', 'SQ1': 'SQ1CO', 'Pyraminx': 'L3E'}


def format_time(seconds):
    if seconds is None:
        return '—'
    if not math.isfinite(seconds):
        return 'DNF'
    hundredths = int(max(0., seconds) * 100)
    minutes, remainder = divmod(hundredths, 6000)
    seconds, decimals = divmod(remainder, 100)
    return f'{minutes}:{seconds:02d}.{decimals:02d}' if minutes else f'{seconds}.{decimals:02d}'


class PracticeSession:
    def __init__(self, history=None, rng=None, clock=None, progress=None):
        self.history = [record for record in history if isinstance(record, dict)] if isinstance(history, list) else []
        self.rng = rng or random.Random()
        self.clock = clock or time.perf_counter
        self.puzzle = None
        self.selected = ()
        self.pool = []
        self._bag = []
        self.question = None
        self.number = 0
        self.state = 'ready'
        self.elapsed = 0.
        self.assisted = False
        self.progress = progress or LearningProgress()
        self.filter = 'all'
        self.last_record = None

    def configure(self, puzzle, selected):
        if puzzle not in PRACTICE_PUZZLES:
            raise ValueError('Unsupported practice puzzle')
        selected = tuple(dict.fromkeys(selected))
        available = groups(puzzle)
        selected = tuple(name for name in selected if any(g['id'] == name for g in available))
        if not selected:
            raise ValueError('Select at least one algorithm set')
        self.puzzle, self.selected = puzzle, selected
        self._eligible = [(group, item) for group in available if group['id'] in selected
                     for item in group['cases'] if 'error' not in item]
        if not self._eligible:
            raise ValueError('No playable practice cases')
        self.pool = self._filtered(self.filter)
        if not self.pool:
            self.filter = 'all'
            self.pool = list(self._eligible)
        self._bag = []
        self.question = None
        self.number = 0
        self.abort()

    def _case_times(self, item):
        identity = case_key(self.puzzle, item)
        return [record for record in self.history if record.get('puzzle') == self.puzzle
                and (record.get('case_key') == identity or (not record.get('case_key')
                     and record.get('set') == family(item['set_id']) and record.get('case') == item['name']))]

    def _weight(self, item):
        recent = self._case_times(item)[-5:]
        valid = [self._time_value(r) for r in recent if self._time_value(r) is not None]
        average = self.stats()['mean'] or 1.
        slow = min(4., sum(valid) / len(valid) / average) if valid else 1.
        return 1. + slow + 3 * sum(r.get('penalty') == 'DNF' for r in recent) + (2 if self.progress.status(self.puzzle, item) == 'learning' else 0)

    def _filtered(self, mode):
        if mode == 'all':
            return list(self._eligible)
        if mode == 'weak':
            ranked = sorted(self._eligible, key=lambda pair: self._weight(pair[1]), reverse=True)
            slow = {case_key(self.puzzle, item) for _, item in ranked[:max(1, len(ranked) // 4)] if self._case_times(item)}
            return [(g, item) for g, item in self._eligible if self.progress.status(self.puzzle, item) != 'mastered'
                    or case_key(self.puzzle, item) in slow]
        if mode == 'preferred':
            return [(g, item) for g, item in self._eligible if self.progress.preferred(self.puzzle, item) is not None]
        return [(g, item) for g, item in self._eligible if self.progress.status(self.puzzle, item) == mode]

    def set_filter(self, mode):
        if mode not in FILTERS or self.state == 'running':
            raise ValueError('Invalid practice filter')
        pool = self._filtered(mode)
        if not pool:
            raise ValueError('No matching practice cases')
        self.filter, self.pool, self._bag = mode, pool, []

    def next_question(self):
        if self.state == 'running':
            raise ValueError('Finish the current attempt first')
        if not self._bag:
            self._bag = list(range(len(self.pool)))
            if self.filter == 'weak':
                weights = {i: self._weight(self.pool[i][1]) for i in self._bag}
                self._bag.sort(key=lambda i: self.rng.random() ** (1 / weights[i]))
            else:
                self.rng.shuffle(self._bag)
            if self.question and len(self._bag) > 1 and self.pool[self._bag[-1]][1] is self.question['item']:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        group, item = self.pool[self._bag.pop()]
        preferred = self.progress.preferred(self.puzzle, item)
        alternatives = [preferred] if preferred is not None else list(range(len(item['algorithms'])))
        if preferred is None:
            self.rng.shuffle(alternatives)
        case = None
        for alternative in alternatives:
            try:
                case = prepare_case(group, item, alternative)
                break
            except ValueError:
                continue
        if case is None:
            case = prepare_case(group, item)
        from demo.practice_scramble import vary_case
        case = vary_case(self.puzzle, case, self.rng)
        self.question = {'group': group, 'item': item, 'case': case}
        self.last_record = None
        self.number += 1
        self.abort()
        return self.question

    def start(self):
        if self.state != 'ready' or not self.question or self.assisted:
            return False
        self._started = self.clock()
        self.elapsed = 0.
        self.state = 'running'
        return True

    def time(self):
        return max(0., self.clock() - self._started) if self.state == 'running' else self.elapsed

    def stop(self):
        if self.state != 'running':
            return None
        self.elapsed = self.time()
        self.state = 'stopped'
        record = {'puzzle': self.puzzle, 'set': self.question['group']['id'],
                  'case': self.question['item']['name'], 'seconds': self.elapsed,
                  'case_key': case_key(self.puzzle, self.question['item']),
                  'penalty': 'OK', 'date': time.time()}
        self.history.append(record)
        self.history = self.history[-500:]
        self.last_record = record
        return record

    def penalty(self, value):
        if value not in ('OK', '+2', 'DNF') or self.last_record is None:
            return False
        self.last_record['penalty'] = value
        return True

    def reveal(self):
        if self.state == 'running':
            self.elapsed = self.time()
        if self.state != 'stopped':
            self.assisted = True
            self.state = 'assisted'

    def abort(self):
        self.state = 'ready'
        self.elapsed = 0.
        self.assisted = False

    def stats(self):
        records = self.records()
        times = [self._time_value(record) for record in records if self._time_value(record) is not None]
        return {'count': len(records), 'best': min(times) if times else None,
                'mean': sum(times) / len(times) if times else None}

    def records(self):
        return [r for r in self.history if r.get('puzzle') == self.puzzle and r.get('set') in self.selected
                and isinstance(r.get('seconds'), (int, float)) and math.isfinite(r['seconds']) and r['seconds'] >= 0]

    @staticmethod
    def _time_value(record):
        value = record.get('seconds')
        if record.get('penalty') == 'DNF' or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return None
        return value + (2 if record.get('penalty') == '+2' else 0)

    def average(self, count):
        records = self.records()[-count:]
        if len(records) < count:
            return None
        values = sorted(float('inf') if self._time_value(r) is None else self._time_value(r) for r in records)
        trimmed = values[1:-1]
        return sum(trimmed) / len(trimmed) if all(math.isfinite(v) for v in trimmed) else float('inf')

    def setup_text(self):
        from demo.irregular_cases import token
        case = self.question['case']
        if case.get('scramble_text'):
            return case['scramble_text']
        cube = case['initial']
        spec = getattr(getattr(cube, 'geometry', None), 'spec', None)
        return ' '.join(token(inverse_demo_move(move, cube), spec) for move in reversed(case['moves']))
