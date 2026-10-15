"""Per-case learning state shared by the offline library and practice."""
import json

STATUSES = ('new', 'learning', 'mastered')
FILTERS = ('all', 'new', 'learning', 'weak', 'preferred')


def case_key(puzzle, item):
    return json.dumps([puzzle, item['set_id'], item['name']], ensure_ascii=False, separators=(',', ':'))


class LearningProgress:
    def __init__(self, records=None):
        self.records = {k: dict(v) for k, v in records.items() if isinstance(k, str) and isinstance(v, dict)} if isinstance(records, dict) else {}

    def get(self, puzzle, item):
        return self.records.get(case_key(puzzle, item), {})

    def status(self, puzzle, item):
        status = self.get(puzzle, item).get('status', 'new')
        return status if status in STATUSES else 'new'

    def cycle(self, puzzle, item):
        record = self.records.setdefault(case_key(puzzle, item), {})
        record['status'] = STATUSES[(STATUSES.index(self.status(puzzle, item)) + 1) % len(STATUSES)]
        return record['status']

    def prefer(self, puzzle, item, alternative):
        if not isinstance(alternative, int) or not 0 <= alternative < len(item['algorithms']):
            raise ValueError('Invalid alternative')
        self.records.setdefault(case_key(puzzle, item), {})['preferred'] = alternative

    def preferred(self, puzzle, item):
        value = self.get(puzzle, item).get('preferred')
        return value if isinstance(value, int) and 0 <= value < len(item['algorithms']) else None
