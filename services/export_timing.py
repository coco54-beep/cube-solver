"""Honest progress estimates: no device-speed assumption before measured work."""
import math


def remaining_seconds(elapsed,completed,total):
    if not all(math.isfinite(v) for v in (elapsed,completed,total)):return None
    if total<=0 or completed<3 or elapsed<1:return None
    return max(0.,elapsed*(total-min(total,completed))/completed)
