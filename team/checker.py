"""The tool-call checker: real code, and the only system logic in this program.

check(call, state) -> (accepted, reason). A call is {"tool": "robot.name",
"args": {...}}. Rules, in order:

  1. the tool exists for that robot in content/tools.schema.json
  2. the arguments validate against the schema (jsonschema)
  3. drone.go respects the Tello SDK limits (values read from facts.yaml)
  4. any target point lies inside the geofence (my setting, mission.yaml)
  5. drone calls other than return_home and land need battery >= reserve (my setting)
  6. dog.go_to needs its target to have been found already
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace

import jsonschema

from core.facts import FACTS_PATH, SCHEMA_PATH, load_mission

import yaml


def load_schema(path: str = SCHEMA_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_limits(path: str = FACTS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["facts"]["tello_go_limits"]["value"]


@dataclass
class WorldState:
    battery: float = 100.0                 # drone battery, percent
    drone_pos: tuple = (2.6, 3.5)          # metres, map frame
    dog_pos: tuple = (4.4, 3.5)
    found: frozenset = frozenset()         # object names seen so far
    reserve: float = 30.0                  # percent, my setting
    geofence: tuple = ()                   # polygon, metres
    areas: dict = field(default_factory=dict)
    objects: dict = field(default_factory=dict)
    home: tuple = (3.5, 3.5)

    def with_(self, **kw) -> "WorldState":
        return replace(self, **kw)


def initial_state(mission: dict | None = None) -> WorldState:
    m = mission or load_mission()
    mp = m["map"]
    return WorldState(
        battery=100.0,
        drone_pos=tuple(mp["spots"]["drone"]),
        dog_pos=tuple(mp["spots"]["dog"]),
        found=frozenset(),
        reserve=float(m["reserve_pct"]),
        geofence=tuple(tuple(p) for p in m["geofence"]),
        areas={k: tuple(v) for k, v in mp["areas"].items()},
        objects={o["name"]: tuple(o["pos"]) for o in mp["objects"]},
        home=tuple(mp["areas"]["home"]),
    )


def inside(poly, p) -> bool:
    """Ray-casting point-in-polygon test."""
    x, y = p
    n = len(poly)
    hit = False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                hit = not hit
    return hit


def _short(msg: str, n: int = 40) -> str:
    msg = msg.replace("'", "")
    return msg if len(msg) <= n else msg[: n - 3].rstrip() + "..."


def _fmt_pct(v: float) -> str:
    return f"{v:g}%"


class Checker:
    def __init__(self, schema: dict | None = None, limits: dict | None = None):
        self.schema = schema or load_schema()
        self.limits = limits or load_limits()
        self.tools = self.schema["tools"]
        self.robots = set(self.schema["robots"])

    # ------------------------------------------------------------------ geometry
    def target_point(self, tool, args, state):
        if tool == "drone.go":
            return (state.drone_pos[0] + args["x"] / 100.0, state.drone_pos[1] + args["y"] / 100.0)
        if tool == "drone.scout":
            return state.areas.get(args["area"])
        if tool == "dog.go_to":
            return state.objects.get(args["target"])
        if tool.endswith(".return_home"):
            return state.home
        return None

    # ------------------------------------------------------------------ rules
    def check(self, call: dict, state: WorldState):
        tool = call.get("tool", "")
        args = call.get("args", {}) or {}
        robot = tool.split(".", 1)[0] if "." in tool else tool
        name = tool.split(".", 1)[1] if "." in tool else ""

        # 1. the tool exists for that robot
        if tool not in self.tools:
            return False, f"no such tool for {robot}"

        # 2. arguments match the schema
        errors = sorted(jsonschema.Draft202012Validator(self.tools[tool]).iter_errors(args),
                        key=lambda e: list(e.path))
        if errors:
            e = errors[0]
            where = ".".join(str(p) for p in e.path)
            return False, _short((where + ": " if where else "") + e.message)

        notes = []
        # 3. Tello SDK limits for drone.go
        if tool == "drone.go":
            L = self.limits
            lo, hi = L["xyz_min"], L["xyz_max"]
            for axis in ("x", "y", "z"):
                if not lo <= args[axis] <= hi:
                    return False, f"{axis} outside {lo} to {hi} cm (Tello SDK)"
            d = L["not_all_within"]
            if all(-d <= args[a] <= d for a in ("x", "y", "z")):
                return False, f"x, y, z all within -{d} to {d} cm (Tello SDK)"
            if not L["speed_min"] <= args["speed"] <= L["speed_max"]:
                return False, f"speed outside {L['speed_min']} to {L['speed_max']} cm/s (Tello SDK)"
            notes.append("within Tello limits")

        # 4. geofence
        p = self.target_point(tool, args, state)
        if p is not None:
            if not inside(state.geofence, p):
                return False, "outside geofence"
            if "area" in args:
                notes.append(f"{args['area']} in geofence")
            elif name == "return_home":
                notes.append("home pad in geofence")
            else:
                notes.append("in geofence")

        # 5. battery reserve for the drone
        if robot == "drone" and name not in ("return_home", "land"):
            if state.battery < state.reserve:
                return False, f"below {state.reserve:g}% reserve: return home first"
            notes.append(f"battery {state.battery:.0f}% ≥ {_fmt_pct(state.reserve)}")

        # 6. the dog only goes to things that have been found
        if tool == "dog.go_to":
            if args["target"] not in state.found:
                return False, "target not found yet"
            notes.insert(0, f"{args['target']} found")

        if not notes:
            notes = ["schema ok"]
        if name == "return_home" and robot == "drone":
            notes = ["always allowed"]
        return True, " · ".join(notes[:2])


_DEFAULT = None


def check(call: dict, state: WorldState):
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Checker()
    return _DEFAULT.check(call, state)


def format_call(call: dict) -> str:
    """drone.scout(area="atrium") style, as shown on screen."""
    parts = []
    for k, v in (call.get("args") or {}).items():
        parts.append(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}")
    return f"{call['tool']}({', '.join(parts)})"


def format_json(call: dict) -> list[str]:
    """The same call as compact JSON, split over two lines for the screen."""
    return [f'{{"tool": "{call["tool"]}",', f' "args": {json.dumps(call.get("args") or {})}}}']
