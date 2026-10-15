"""Refresh the offline algorithm catalog from SpeedCubeDB public set pages.

Only case identifiers, group names, functional move sequences and source URLs
are imported. Illustrations, prose, videos and community profiles are excluded.
Run from the repository root. Downloaded pages are cached under ignored tmp/.
"""
import concurrent.futures
from datetime import date
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
try:
    from .formula_catalog_rules import curate
except ImportError:
    from formula_catalog_rules import curate

BASE = 'https://www.speedcubedb.com/'
PUZZLES = ('2x2', '3x3', '4x4', '5x5', 'SQ1', 'Skewb', 'Pyraminx', 'Megaminx')
CACHE = Path('tmp/formula-source')
OUTPUT = Path('demo/data/speedcubedb.json')


def plain(value):
    return ' '.join(html.unescape(re.sub('<[^>]+>', '', value)).split())


class SetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.current = None
        self.words = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and 'search-category' in a.get('class', '').split():
            href = a.get('href', '').lstrip('/')
            if re.fullmatch(r'a/[^/]+/[^/#?]+', href):
                self.current = href[2:]
                self.words = []

    def handle_data(self, data):
        if self.current:
            self.words.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.current:
            self.links[self.current] = ' '.join(' '.join(self.words).split())
            self.current = None


def fetch(path):
    cached = CACHE / (path.replace('/', '-') + '.html')
    previous = Path('reports/speedcubedb-' + path.replace('/', '-') + '.html')
    if cached.exists():
        return cached.read_text(encoding='utf-8')
    if previous.exists():
        body = previous.read_text(encoding='utf-8')
    else:
        url = BASE + 'a/' + urllib.parse.quote(path, safe='/')
        request = urllib.request.Request(url, headers={'User-Agent': 'CubeSolver-formula-catalog/1.0'})
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read().decode('utf-8')
    cached.write_text(body, encoding='utf-8')
    return body


def extract(path):
    body = fetch(path)
    links = SetLinks()
    links.feed(body)
    puzzle = path.split('/')[0]
    children = {p: name for p, name in links.links.items() if p.startswith(puzzle + '/')}
    starts = list(re.finditer(r'<div\b[^>]*class="[^"]*\bsinglealgorithm\b[^"]*"[^>]*>', body))
    cases = []
    for i, start in enumerate(starts):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', start.group()))
        name = html.unescape(attrs.get('data-alg', ''))
        block = body[start.end():starts[i + 1].start() if i + 1 < len(starts) else len(body)]
        alternatives = list(dict.fromkeys(plain(a) for a in re.findall(
            r'class="formatted-alg"[^>]*>(.*?)</div>', block, re.S)))
        alternatives = [a for a in alternatives if a]
        setup_block = re.search(r'class="setup-case[^>]*>\s*<div>setup:</div>(.*?)</div>', block, re.S)
        if setup_block and puzzle == 'SQ1':
            # The source occasionally has a typo in the printed formula while
            # its simulator link contains the corrected functional sequence.
            for href in re.findall(r'href="([^"]+)"', setup_block[1]):
                parsed = urllib.parse.urlparse(html.unescape(href))
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.hostname == 'cubedb.net' and query.get('type') == ['alg'] and query.get('alg'):
                    linked = urllib.parse.unquote(query['alg'][0])
                    if linked and linked not in alternatives:
                        alternatives.append(linked)
        if not name or not alternatives:
            continue
        cases.append({'name': name, 'group': html.unescape(attrs.get('data-subgroup', '')),
                      'algorithms': alternatives,
                      'url': BASE + 'a/' + urllib.parse.quote(path + '/' + name.replace(' ', '_'), safe='/')})
    title = plain(re.search(r'<title>(.*?)</title>', body, re.S).group(1)).split(' - Speed Cube')[0]
    return curate({'id': path, 'puzzle': puzzle, 'name': title, 'cases': cases}), children


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    pending = set(PUZZLES)
    visited = set()
    sets = {}
    failures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch = sorted(pending - visited)
            if not batch:
                break
            visited.update(batch)
            pending = set()
            jobs = {pool.submit(extract, path): path for path in batch}
            for job in concurrent.futures.as_completed(jobs):
                path = jobs[job]
                try:
                    item, children = job.result()
                    pending.update(children)
                    if item['cases']:
                        sets[path] = item
                    print(path, len(item['cases']), flush=True)
                except Exception as exc:
                    failures[path] = str(exc)
                    print('FAILED', path, str(exc), flush=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {'version': 1, 'source': BASE, 'retrieved': date.today().isoformat(),
               'sets': [sets[key] for key in sorted(sets)], 'fetch_failures': failures}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('Saved', len(sets), 'sets,', sum(len(s['cases']) for s in sets.values()), 'cases', flush=True)
    if failures:
        raise SystemExit('Some pages failed; inspect fetch_failures before release')


if __name__ == '__main__':
    main()
