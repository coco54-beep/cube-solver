"""Curated algorithms and import exclusions for the offline catalog."""

ALGORITHMS = {
    ('3x3/1LLL02', '1LLL 2 28'): [
        "y F' U' F U r U r' U2 R' F R F' r U r'",
    ],
    ('3x3/1LLL05', '1LLL 5 42'): [
        "y2 F R' F' R U R U' R' F' r U R' U' r' F R U'",
        "y r' R U R' U' F U F' R U' R' F' r",
    ],
    ('Megaminx/MegaminxOLL10', '10A+'): [
        "R U R' U2 R U' R' U2' R' F R F'",
    ],
}

EXCLUDED = {('SQ1/SQ1LinParityPLL', 'Cb')}


def curate(group):
    cases = []
    for item in group['cases']:
        key = (group['id'], item['name'])
        if key in EXCLUDED:
            continue
        if key in ALGORITHMS:
            item['algorithms'] = list(ALGORITHMS[key])
            item.pop('selected', None)
            item.pop('error', None)
        cases.append(item)
    group['cases'] = cases
    return group
