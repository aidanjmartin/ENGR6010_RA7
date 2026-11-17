"""Say x Can for a two-robot team (beat 2.2). The scores are illustrative,
made up to show SayCan's rule: run the step whose usefulness ("Say") times
feasibility ("Can") is highest. Only the shape of the rule comes from Ahn et al.
"""
from __future__ import annotations

import math


def _step(battery: float, reserve: float, width: float = 1.5) -> float:
    """Smooth 0 -> 1 as battery falls below the reserve."""
    return 1.0 / (1.0 + math.exp((battery - reserve) / width))


def scores(battery: float, reserve: float = 30.0, chair_seen: bool = False):
    """Return [(say, can, product)] for the four candidates."""
    low = _step(battery, reserve)
    say = [0.85, 0.55, 0.30 + 0.65 * low, 0.80]
    can = [0.90 * (1 - low) + 0.05 * low,     # scouting needs battery above the reserve
           0.60,                              # the dog can walk there, slowly
           0.95,                              # flying home is always possible
           0.85 if chair_seen else 0.05]      # cannot go to a chair nobody has seen
    return [(s, c, s * c) for s, c in zip(say, can)]


def choice(battery: float, reserve: float = 30.0, chair_seen: bool = False) -> int:
    sc = scores(battery, reserve, chair_seen)
    return max(range(len(sc)), key=lambda i: sc[i][2])
