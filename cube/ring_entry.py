"""Shared cursor and non-destructive placement rules for SQ input drafts."""

def next_empty(slots, start):
    """Continue around this layer, then the following layers."""
    layer=start//12
    for offset in range(1,13):
        slot=layer*12+(start%12+offset)%12
        if slots[slot] < 0:
            return slot
    for offset in range(1,len(slots)//12):
        following=(layer+offset)%(len(slots)//12)
        for slot in range(following*12,following*12+12):
            if slots[slot]<0:return slot
    return start


def placement(slots, slot, width):
    """Replacing the selected block is explicit; neighbouring blocks are kept."""
    old = slots[slot]
    targets = [slot//12*12+(slot%12+i)%12 for i in range(width)]
    if any(slots[i] not in (-1, old) for i in targets):
        raise ValueError('sq.entry_occupied')
    return targets, old
