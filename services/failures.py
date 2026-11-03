"""Stable failure categories independent of the screen or UI language."""
from functools import lru_cache
import re

INCOMPLETE={'input.missing','poly.error.incomplete','square1.error.incomplete','rigid.incomplete',
 'observe.incomplete','mixup.entry_incomplete','bandage.entry_incomplete','penrose.incomplete','cuboid.entry_incomplete'}
TIMEOUT={'master_clover.regular_only','cuboid.search_budget','cuboid.search_limit','mixup.shape_limit','mixup.search_limit','rigid.search_limit',
 'tilted.group_unresolved','flower.regular_only','twins.regular_only','twins.legacy_entry',
 'copter.shape_unresolved','copter.scramble_timeout','comet.timeout',
 'circle.search_limit','pentacle.search_limit','observe.timeout','observe.limit','solver.timeout'}
ILLEGAL={'poly.error.counts','poly.error.piece','poly.error.orientation','poly.error.illegal','observe.conflict',
 'tilted.fixed_core',
 'copter.invalid_shape',
 'observe.invalid','cuboid.colours','cuboid.identity_unreachable','rigid.invalid','penrose.invalid',
 'shape.error.corner_twist','rex.error.edge_flip','rex.error.orbit_parity',
 'aj.error.fixed_centres','aj.error.orbit_parity','aj.error.edge_flip'}
ENGLISH={
 'Please enter every sticker':'incomplete','Please enter every sticker before solving.':'incomplete',
 'The color counts do not match this puzzle':'illegal','The colour counts do not match this puzzle':'illegal',
 'A piece has an impossible color combination or position':'illegal',
 'A piece has a mirrored or impossible orientation':'illegal','Repeated color on a piece':'illegal',
 'Duplicate piece':'illegal','The entered puzzle is not a legal state':'illegal',
 'The entered pieces violate an orientation or permutation constraint':'illegal',
 'The entered core has an impossible orientation':'illegal','Odd orbit permutation':'illegal',
 'The color counts or numbers do not match this puzzle':'illegal',
 'Numbers belong to the ring; colours belong to the corners':'illegal',
 'A corner has an impossible colour combination':'illegal',
 'A corner has a mirrored orientation':'illegal','A corner has an impossible twist':'illegal',
}


@lru_cache(maxsize=1)
def known_messages():
    result=dict(ENGLISH)
    for keys,category in ((INCOMPLETE,'incomplete'),(TIMEOUT,'timeout'),(ILLEGAL,'illegal')):
        for key in keys:result[key]=category
    try:
        from app.i18n import CATALOG
        for catalog in CATALOG.values():
            for key,value in catalog.items():
                if not isinstance(value,str):continue
                category=('incomplete' if key in INCOMPLETE or key.endswith(('.incomplete','_incomplete')) else
                          'timeout' if key in TIMEOUT or key.endswith(('.timeout','.search_budget','.search_limit','.shape_limit')) else
                          'illegal' if key in ILLEGAL else None)
                if category:
                    result[key]=category
                    result[value]=category
    except ImportError:pass
    from cube.validation import _MESSAGES
    for original,translated in _MESSAGES.items():
        category='incomplete' if original.startswith('缺少面') else 'illegal'
        for template in (original,*translated.values()):result[template]=category
    return result


@lru_cache(maxsize=1)
def formatted_messages():
    patterns=[]
    for text,category in known_messages().items():
        if '{' in text:
            parts=re.split(r'(\{[^{}]+\})',text)
            patterns.append((re.compile(''.join('.+?' if p.startswith('{') else re.escape(p) for p in parts),re.DOTALL),category))
    return patterns


def classify(message='',exception=None,default='internal'):
    if isinstance(exception,InterruptedError):return 'cancelled'
    if isinstance(exception,TimeoutError):return 'timeout'
    # Programming faults must never be presented as a bad physical puzzle.
    if exception is not None and not isinstance(exception,ValueError):return 'internal'
    text=str(message or exception or '').strip()
    messages=known_messages()
    if text in messages:return messages[text]
    for pattern,category in formatted_messages():
        if pattern.fullmatch(text):return category
    for known,category in messages.items():
        if '.' in known and ' ' not in known and text.startswith(known+':'):return category
    return default


def matching_category(status):
    return {'incomplete':'incomplete','ambiguous':'incomplete','conflict':'illegal',
            'timeout':'timeout','limit':'timeout','cancelled':'cancelled','error':'internal'}.get(status,'internal')
