"""The tool checker: canned good calls pass where they are issued, bad calls fail
with exactly the reason shown on screen, and the Tello limits hold at the edges."""
from __future__ import annotations

import pytest

BAD_REASONS = [
    "no such tool for dog",
    "x outside -500 to 500 cm (Tello SDK)",
    "below 30% reserve: return home first",
]


def _go(x=100, y=0, z=100, speed=50):
    return {"tool": "drone.go", "args": {"x": x, "y": y, "z": z, "speed": speed}}


EDGE_CASES = [
    (_go(x=500), True),
    (_go(x=501), False),
    (_go(x=-500, y=0, z=100), None),      # within Tello limits; geofence decides (see below)
    (_go(x=10, y=10, z=10), False),
    (_go(speed=9), False),
    (_go(speed=101), False),
    (_go(speed=10), True),
    (_go(speed=100), True),
]


def checker_problems() -> list[str]:
    """Used by both pytest and main.py --check."""
    from core.facts import load_mission
    from sim.mission import Mission
    from team.checker import Checker, initial_state
    problems = []
    m = load_mission()
    ck = Checker()
    mission = Mission(m, ck)
    for entry in mission.log:
        if not entry.accepted:
            problems.append(f"{entry.call['tool']} rejected where issued: {entry.reason}")
    s0 = initial_state(m)
    for call, want in zip(m["bad_calls"], BAD_REASONS):
        ok, why = ck.check(call, s0.with_(**call.get("state", {})))
        if ok or why != want:
            problems.append(f"{call['tool']}: expected rejection {want!r}, got {ok} {why!r}")
    for call, want in EDGE_CASES:
        ok, why = ck.check(call, s0)
        if want is not None and ok != want:
            problems.append(f"{call['args']}: expected {'accept' if want else 'reject'}, got {why!r}")
    return problems


def test_checker_cases():
    assert checker_problems() == []


def test_bad_calls_exact_reasons():
    from core.facts import load_mission
    from team.checker import check, initial_state
    m = load_mission()
    s0 = initial_state(m)
    got = [check(c, s0.with_(**c.get("state", {}))) for c in m["bad_calls"]]
    assert got == [(False, r) for r in BAD_REASONS]


def test_limit_reasons_name_the_limit():
    from team.checker import check, initial_state
    s0 = initial_state()
    assert check(_go(x=501), s0) == (False, "x outside -500 to 500 cm (Tello SDK)")
    assert check(_go(z=-501), s0) == (False, "z outside -500 to 500 cm (Tello SDK)")
    assert check(_go(x=10, y=10, z=10), s0) == (False, "x, y, z all within -20 to 20 cm (Tello SDK)")
    assert check(_go(speed=9), s0) == (False, "speed outside 10 to 100 cm/s (Tello SDK)")
    assert check(_go(speed=101), s0) == (False, "speed outside 10 to 100 cm/s (Tello SDK)")


def test_rules_in_order():
    from team.checker import check, initial_state
    s0 = initial_state()
    assert check({"tool": "cat.jump", "args": {}}, s0) == (False, "no such tool for cat")
    ok, why = check({"tool": "drone.scout", "args": {}}, s0)
    assert not ok and "required" in why
    ok, why = check({"tool": "drone.go", "args": {"x": "far", "y": 0, "z": 100, "speed": 50}}, s0)
    assert not ok and "integer" in why
    assert check(_go(x=-500), s0) == (False, "outside geofence")
    assert check({"tool": "dog.go_to", "args": {"target": "red chair"}}, s0) == (False, "target not found yet")
    low = s0.with_(battery=29.9)
    assert check({"tool": "drone.return_home", "args": {}}, low)[0]
    assert check({"tool": "drone.land", "args": {}}, low)[0]
    assert not check({"tool": "drone.takeoff", "args": {}}, low)[0]
    assert check({"tool": "drone.takeoff", "args": {}}, s0.with_(battery=30.0))[0]


@pytest.mark.parametrize("p,inside", [((3, 3), True), ((13, 4), True), ((25, 15), True),
                                      ((13, 10), False), ((-1, 3), False), ((33, 5), False)])
def test_geofence_polygon(p, inside):
    from team.checker import inside as point_in, initial_state
    assert point_in(initial_state().geofence, p) == inside


def test_saycan_choice_follows_battery():
    from team.saycan import choice
    assert choice(100.0) == 0          # drone: scout atrium
    assert choice(60.0) == 0
    assert choice(25.0) == 2           # drone: fly home
    assert choice(5.0) == 2
    assert choice(100.0, chair_seen=False) != 3
