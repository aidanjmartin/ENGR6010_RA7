"""The scripted mission respects the checker, the reserve, the geofence, and the pad."""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def mission():
    from sim.mission import Mission
    return Mission()


def _times(m, n=2000):
    return [m.t_end * k / (n - 1) for k in range(n)]


def test_drone_stays_above_reserve_until_the_return_leg(mission):
    for t in _times(mission):
        if t < mission.t_ret:
            assert mission.battery(t) >= mission.reserve, t
    assert mission.battery(mission.t_ret) >= mission.reserve
    assert mission.battery(mission.t_land) < mission.battery(mission.t_ret)


def test_return_home_issued_above_reserve(mission):
    entry = next(e for e in mission.log if e.call["tool"] == "drone.return_home")
    assert entry.state.battery >= mission.reserve


def test_both_end_on_the_pad(mission):
    x0, y0, x1, y1 = mission.m["map"]["home_pad"]
    for p in (mission.drone(mission.t_end)[0], mission.dog(mission.t_end)[0]):
        assert x0 <= p[0] <= x1 and y0 <= p[1] <= y1


def test_every_logged_call_passed_the_checker(mission):
    assert len(mission.log) == 6
    assert all(e.accepted for e in mission.log), [(e.call, e.reason) for e in mission.log]
    assert [e.call["tool"] for e in mission.log] == [c["tool"] for c in mission.m["calls"]]


def test_no_path_leaves_the_geofence(mission):
    from team.checker import inside
    fence = mission.state0.geofence
    for t in _times(mission):
        assert inside(fence, mission.drone(t)[0]), ("drone", t)
        assert inside(fence, mission.dog(t)[0]), ("dog", t)


def test_red_chair_found_by_drone_outside_camera_square(mission):
    x0, y0, x1, y1 = mission.m["map"]["camera_square"]
    cx, cy = mission.chair_pos
    assert not (x0 <= cx <= x1 and y0 <= cy <= y1)
    assert 0 < mission.t_find < mission.t_ret
    assert mission.t_dog_start > mission.t_find


def test_phase_order(mission):
    ph = mission.phases
    assert len(ph) == 7
    starts = [a for a, _ in ph]
    assert starts == sorted(starts)
    assert mission.t_land < mission.t_dog_arrive < mission.t_dog_home
