"""Load content/facts.yaml and content/mission.yaml, and fill {key} templates.

A template field is either a fact key ({tello_flight_time} -> the fact's "text")
or a fact key and part ({go2_walk.policy} -> the fact's texts["policy"]).
Extra values (for example {reserve}) can be passed by the caller.
"""
from __future__ import annotations

import os
import string

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
FACTS_PATH = os.path.join(CONTENT, "facts.yaml")
MISSION_PATH = os.path.join(CONTENT, "mission.yaml")
SCHEMA_PATH = os.path.join(CONTENT, "tools.schema.json")


def load_mission(path: str = MISSION_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class Facts:
    def __init__(self, path: str = FACTS_PATH, mission_path: str = MISSION_PATH):
        with open(path, "r", encoding="utf-8") as fh:
            self.data = yaml.safe_load(fh)
        self.facts = self.data["facts"]
        self.sources = self.data["sources"]
        self.references = self.data["references"]
        self.beats = self.data["beats"]
        self.mission = load_mission(mission_path)
        self.extra = {"reserve": self.mission["reserve_pct"]}

    def __getitem__(self, key):
        return self.facts[key]

    def value(self, key):
        return self.facts[key]["value"]

    def text(self, field: str) -> str:
        if "." in field:
            key, part = field.split(".", 1)
            return str(self.facts[key]["texts"][part])
        return str(self.facts[field]["text"])

    def fmt(self, template: str, **extra) -> str:
        """Replace {key} or {key.part} with on-screen text, or with an extra value."""
        vals = dict(self.extra)
        vals.update(extra)
        out = []
        for literal, field, _spec, _conv in string.Formatter().parse(template):
            out.append(literal)
            if field is None:
                continue
            if field in vals:
                out.append(str(vals[field]))
            elif field.split(".", 1)[0] in self.facts:
                out.append(self.text(field))
            else:
                raise KeyError(f"unknown template field {{{field}}} in {template!r}")
        return "".join(out)

    def source(self, key: str) -> str:
        return self.sources[key]

    def beat(self, key: str) -> "BeatText":
        return BeatText(self, self.beats[key])


class BeatText:
    """Read-only view over one beat's text block with template filling."""

    def __init__(self, facts: Facts, block: dict):
        self.F = facts
        self.block = block

    def __call__(self, key: str, **extra):
        return self._fill(self.block[key], extra)

    def _fill(self, v, extra):
        if isinstance(v, str):
            return self.F.fmt(v, **extra)
        if isinstance(v, list):
            return [self._fill(x, extra) for x in v]
        if isinstance(v, dict):
            return {k: self._fill(x, extra) for k, x in v.items()}
        return v

    def raw(self, key):
        return self.block[key]

    def get(self, key, default=None):
        return self(key) if key in self.block else default


def all_on_screen_strings(F: Facts):
    """Every string that can appear on screen, templates filled. Used by tests."""
    out = []

    def walk(v):
        if isinstance(v, str):
            out.append(F.fmt(v, battery=25))
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(F.beats)
    walk(F.sources)
    walk(F.references)
    for f in F.facts.values():
        if "text" in f:
            out.append(str(f["text"]))
        for t in f.get("texts", {}).values():
            out.append(str(t))
    for row in F.value("grounding_eval"):
        out.append(row["prompt"])
    out.append(F.mission["sentence"])
    return out
