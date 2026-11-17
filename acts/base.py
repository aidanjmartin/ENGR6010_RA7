"""Beat and Act base classes shared by every act.

A beat is one idea on one screen. A stepped beat reveals its parts one key press
at a time. Animation is a pure function of time since each step started, so
replay and screenshots are deterministic.
"""
from __future__ import annotations

import pygame

from core import theme as T
from core import widgets as Wg
from core.anim import progress

FAR_PAST = -1e6
NEVER = 1e12


class Beat:
    key = "0.0"
    steps = 1
    step_durations = (2.0,)   # used to chain steps when replaying

    def __init__(self, facts):
        self.F = facts
        self.txt = facts.beat(self.key)
        self.t = 0.0
        self.step = 0
        self.starts = [0.0] + [NEVER] * (self.steps - 1)

    # ---------------------------------------------------------------- lifecycle
    def enter(self, at_end: bool = False):
        self.t = 0.0
        if at_end:
            self.step = self.steps - 1
            self.starts = [FAR_PAST] * self.steps
        else:
            self.step = 0
            self.starts = [0.0] + [NEVER] * (self.steps - 1)
        self.on_enter()

    def on_enter(self):
        pass

    def replay(self):
        """Replay every step reached so far, one after another."""
        s = 0.0
        for i in range(self.steps):
            if i <= self.step:
                self.starts[i] = s
                s += self.step_durations[min(i, len(self.step_durations) - 1)]
            else:
                self.starts[i] = NEVER
        self.t = 0.0
        self.on_enter()

    def next_step(self) -> bool:
        if self.step < self.steps - 1:
            self.step += 1
            self.starts[self.step] = self.t
            return True
        return False

    def prev_step(self) -> bool:
        if self.step > 0:
            self.starts[self.step] = NEVER
            self.step -= 1
            return True
        return False

    def settle(self):
        """Jump to the end of every running animation (screenshots, tests)."""
        self.t += 600.0

    def update(self, dt: float):
        self.t += dt

    def handle(self, event) -> bool:
        return False

    # ---------------------------------------------------------------- timing
    def lt(self, step: int = 0) -> float:
        """Local time since `step` started."""
        return self.t - self.starts[step]

    def p(self, step: int = 0, delay: float = 0.0, dur: float = 0.6) -> float:
        if step > self.step:
            return 0.0
        return progress(self.lt(step), delay, dur)

    # ---------------------------------------------------------------- shared chrome
    def chrome(self, ctx, captions_alpha=None):
        Wg.header(ctx, self.txt.get("kicker"), self.txt("title"))
        caps = self.txt.get("caption")
        if caps:
            Wg.captions(ctx, caps, captions_alpha)

    def draw(self, ctx):
        raise NotImplementedError


class Act:
    """A list of beats with the navigation interface main.py uses."""

    number = 0
    name = ""

    def __init__(self, beats):
        self.beats = beats
        self.i = 0

    @property
    def beat(self) -> Beat:
        return self.beats[self.i]

    def enter(self, at_end: bool = False):
        self.i = len(self.beats) - 1 if at_end else 0
        self.beat.enter(at_end)

    def update(self, dt):
        self.beat.update(dt)

    def draw(self, ctx):
        self.beat.draw(ctx)

    def handle(self, event) -> bool:
        return self.beat.handle(event)

    def next_beat(self) -> bool:
        if self.beat.next_step():
            return True
        if self.i < len(self.beats) - 1:
            self.i += 1
            self.beat.enter()
            return True
        return False

    def prev_beat(self) -> bool:
        if self.beat.prev_step():
            return True
        if self.i > 0:
            self.i -= 1
            self.beat.enter(at_end=True)
            return True
        return False

    def reset_beat(self):
        self.beat.replay()
