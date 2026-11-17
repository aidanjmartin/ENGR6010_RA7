"""A scripted two-robot mission on a top-down map (beat 4.3).

This is an illustration, not a run: the motion is scripted. What is computed is
(1) when the drone's forward camera first covers the red chair, (2) the drone's
battery on the Tello's 13-minute scale, and (3) every tool call, checked by
team/checker.py in the world state at the moment it is issued.

Times are mission minutes. Lengths are metres in the map frame (x right, y up).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from core.facts import load_mission
from team.checker import Checker, initial_state

DRONE_SCAN_SPEED = 9.0       # m per mission minute while scouting
DRONE_CRUISE_SPEED = 30.0    # m per mission minute on the way home
DOG_SPEED = 10.0             # m per mission minute
TAKEOFF_MIN = 0.3
CAMERA_RANGE = 4.5           # m, forward camera footprint (drawn cone)
CAMERA_HALF_ANGLE = math.radians(32)
RETURN_MARGIN = 2.0          # issue return_home this many percent above the reserve
FLIGHT_MINUTES = 13.0        # Tello User Manual: up to 13 min per battery


# ---------------------------------------------------------------- paths
class Path:
    """Piecewise-linear path sampled by arc length."""

    def __init__(self, pts):
        self.pts = [tuple(p) for p in pts]
        self.cum = [0.0]
        for a, b in zip(self.pts[:-1], self.pts[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))

    @property
    def length(self):
        return self.cum[-1]

    def at(self, s):
        """(point, heading) at arc length s."""
        s = max(0.0, min(self.length, s))
        for i in range(len(self.pts) - 1):
            if s <= self.cum[i + 1] or i == len(self.pts) - 2:
                a, b = self.pts[i], self.pts[i + 1]
                L = self.cum[i + 1] - self.cum[i]
                f = 0.0 if L < 1e-9 else (s - self.cum[i]) / L
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), math.atan2(b[1] - a[1], b[0] - a[0])
        return self.pts[-1], 0.0

    def sample(self, step=0.25):
        n = max(2, int(self.length / step) + 1)
        return [self.at(self.length * k / (n - 1))[0] for k in range(n)]


def smooth(pts, per_seg=12):
    """Catmull-Rom spline through the waypoints."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per_seg):
            t = k / per_seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(tuple(pts[-1]))
    return out


def in_cone(origin, heading, target, rng=CAMERA_RANGE, half=CAMERA_HALF_ANGLE):
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    d = math.hypot(dx, dy)
    if d > rng or d < 1e-9:
        return False
    a = math.atan2(dy, dx) - heading
    a = (a + math.pi) % (2 * math.pi) - math.pi
    return abs(a) <= half


@dataclass
class Logged:
    call: dict
    t: float
    accepted: bool
    reason: str
    state: object


class Mission:
    def __init__(self, mission: dict | None = None, checker: Checker | None = None):
        self.m = mission or load_mission()
        self.checker = checker or Checker()
        mp = self.m["map"]
        self.reserve = float(self.m["reserve_pct"])
        self.state0 = initial_state(self.m)
        self.drone_home = tuple(mp["spots"]["drone"])
        self.dog_home = tuple(mp["spots"]["dog"])
        self.chair = next(o for o in mp["objects"] if o["name"] == "red chair")
        self.chair_pos = tuple(self.chair["pos"])
        self.drain = 100.0 / FLIGHT_MINUTES          # percent per flying minute

        # Drone: through the hallway, then a lawnmower over the atrium.
        x0, x1 = 19.5, 30.5
        rows = [2.5, 7.0, 11.5, 16.0]
        scan = [self.drone_home, (8.0, 4.25), (18.0, 4.25)]
        for k, y in enumerate(rows):
            scan += [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]
        self.scan_path = Path(scan)
        self.t_find, self.s_find = self._find_time()
        self.hover = self.scan_path.at(self.s_find)[0]
        self.t_ret = (100.0 - (self.reserve + RETURN_MARGIN)) / self.drain
        self.ret_path = Path([self.hover, (18.0, 4.25), (8.0, 4.25), self.drone_home])
        self.t_land = self.t_ret + self.ret_path.length / DRONE_CRUISE_SPEED

        # Dog: leaves after the sighting, walks a smooth path to the chair, then home.
        approach = (self.chair_pos[0] - 0.8, self.chair_pos[1] - 0.6)
        way = [self.dog_home, (8.0, 4.25), (18.0, 4.25), (21.0, 7.2), (25.5, 10.4), approach]
        self.dog_out = Path(smooth(way))
        self.dog_back = Path(list(reversed(self.dog_out.pts)))
        self.t_dog_start = self.t_find + 0.25
        self.t_dog_arrive = self.t_dog_start + self.dog_out.length / DOG_SPEED
        self.t_dog_home = self.t_dog_arrive + 0.3 + self.dog_back.length / DOG_SPEED
        self.t_end = max(self.t_dog_home, self.t_land)

        # Seven phases (mission-minute intervals).
        self.phases = [
            (0.0, 0.0),
            (0.0, self.t_find),
            (self.t_find, self.t_find + 0.25),
            (self.t_find + 0.25, self.t_ret),
            (self.t_ret, self.t_land),
            (self.t_land, self.t_dog_home),
            (self.t_end, self.t_end),
        ]
        self.log = self._build_log()

    # ------------------------------------------------------------ timeline
    def _find_time(self):
        ds = 0.02
        s = 0.0
        while s <= self.scan_path.length:
            p, h = self.scan_path.at(s)
            if in_cone(p, h, self.chair_pos):
                return TAKEOFF_MIN + s / DRONE_SCAN_SPEED, s
            s += ds
        raise RuntimeError("the scripted scan never sees the red chair")

    def battery(self, t):
        flying = max(0.0, min(t, self.t_land))
        return 100.0 - self.drain * flying

    def drone(self, t):
        """(position, heading, airborne)."""
        if t <= TAKEOFF_MIN:
            return self.drone_home, 0.0, t > 0
        if t <= self.t_find:
            p, h = self.scan_path.at((t - TAKEOFF_MIN) * DRONE_SCAN_SPEED)
            return p, h, True
        if t <= self.t_ret:
            h = math.atan2(self.chair_pos[1] - self.hover[1], self.chair_pos[0] - self.hover[0])
            return self.hover, h, True
        if t < self.t_land:
            p, h = self.ret_path.at((t - self.t_ret) * DRONE_CRUISE_SPEED)
            return p, h, True
        return self.drone_home, math.pi, False

    def dog(self, t):
        """(position, heading, walking)."""
        if t <= self.t_dog_start:
            return self.dog_home, 0.0, False
        if t <= self.t_dog_arrive:
            p, h = self.dog_out.at((t - self.t_dog_start) * DOG_SPEED)
            return p, h, True
        if t <= self.t_dog_arrive + 0.3:
            return self.dog_out.pts[-1], self.dog_out.at(self.dog_out.length)[1], False
        if t <= self.t_dog_home:
            p, h = self.dog_back.at((t - self.t_dog_arrive - 0.3) * DOG_SPEED)
            return p, h, True
        return self.dog_home, math.pi, False

    def found(self, t):
        return frozenset({"red chair"}) if t >= self.t_find else frozenset()

    def world(self, t):
        return self.state0.with_(battery=self.battery(t), drone_pos=self.drone(t)[0],
                                 dog_pos=self.dog(t)[0], found=self.found(t))

    def _build_log(self):
        calls = self.m["calls"]
        times = {
            "drone.takeoff": 0.0,
            "drone.scout": 0.0,
            "vision.find": 0.0,
            "dog.go_to": self.t_dog_start,
            "drone.return_home": self.t_ret,
            "dog.return_home": self.t_dog_arrive + 0.3,
        }
        out = []
        for c in calls:
            t = times[c["tool"]]
            st = self.world(t)
            ok, why = self.checker.check(c, st)
            out.append(Logged(c, t, ok, why, st))
        return out

    def issue_state(self, tool):
        """The world state at the moment a canned call is issued (used in beat 3.1)."""
        return next(l.state for l in self.log if l.call["tool"] == tool)
