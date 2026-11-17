"""Easing and small tween helpers. Animations are pure functions of time."""
from __future__ import annotations

import math


def clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else 1.0 if x >= 1.0 else x


def ease(x: float) -> float:
    """Ease-in-out cubic on [0, 1]."""
    x = clamp01(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x: float) -> float:
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def progress(t: float, start: float, dur: float) -> float:
    """Eased progress of a tween that starts at `start` and lasts `dur` seconds."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return ease((t - start) / dur)


def lerp(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


def lerp_pt(a, b, p: float):
    return (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)


def lerp_angle(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


def pulse(t: float, period: float = 1.6) -> float:
    """Smooth 0..1..0 pulse used for gentle highlights."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


def stagger(t: float, i: int, start: float, gap: float, dur: float) -> float:
    return progress(t, start + i * gap, dur)
