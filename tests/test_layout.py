"""Layout and alignment: margins, overlaps, input mapping, and the offline check."""
from __future__ import annotations

import socket

import pygame
import pytest


@pytest.fixture(scope="module")
def rendered():
    """Render every beat and step once, keeping the recorded boxes."""
    from main import build_acts, all_states, render_state
    from core.facts import Facts
    from core.canvas import Ctx
    from core import theme as T
    pygame.init()
    pygame.display.set_mode((64, 64))
    acts = build_acts(Facts())
    canvas = pygame.Surface((T.W, T.H))
    ctx = Ctx(canvas)
    out = []
    for ai, bi, st in all_states(acts):
        beat = render_state(acts, ai, bi, st, ctx)
        out.append((f"{beat.key} step {st + 1}", list(ctx.records)))
    return out


def test_everything_inside_safe_margin(rendered):
    from core import theme as T
    safe = pygame.Rect(T.SAFE, T.SAFE, T.W - 2 * T.SAFE, T.H - 2 * T.SAFE)
    bad = []
    for name, recs in rendered:
        for kind, r, label in recs:
            if r.width and r.height and not safe.contains(r):
                bad.append(f"{name}: {kind} {label!r} {r}")
    assert not bad, "\n".join(bad)


def test_no_text_overlaps(rendered):
    bad = []
    for name, recs in rendered:
        texts = [(r.inflate(-4, -4), label) for kind, r, label in recs if kind == "text" and r.width and r.height]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if texts[i][0].colliderect(texts[j][0]):
                    bad.append(f"{name}: {texts[i][1]!r} overlaps {texts[j][1]!r}")
    assert not bad, "\n".join(bad)


@pytest.mark.parametrize("size", [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (1920, 1200),
                                  (1440, 900), (1366, 768), (2880, 1800), (3024, 1964)])
def test_mouse_mapping_inverts_present(size):
    from core.canvas import compute_transform, map_point
    scale, off, dest = compute_transform(*size)
    assert abs(dest[0] / dest[1] - 16 / 9) < 0.01
    for vx, vy in [(0, 0), (960, 540), (1919, 1079), (1240, 800)]:
        wx = off[0] + vx * scale
        wy = off[1] + vy * scale
        v = map_point((wx, wy), scale, off)
        assert v is not None
        assert abs(v[0] - vx) < 1.0 and abs(v[1] - vy) < 1.0
    # clicks in a letterbox bar are ignored
    if off[1] > 2:
        assert map_point((size[0] / 2, off[1] / 2), scale, off) is None
    if off[0] > 2:
        assert map_point((off[0] / 2, size[1] / 2), scale, off) is None


def test_retina_ratio_mapping():
    from core.canvas import compute_transform, map_point
    # drawable surface 2x the window in points
    scale, off, _ = compute_transform(2880, 1800)
    v = map_point((720, 450), scale, off, ratio=(2.0, 2.0))
    assert abs(v[0] - 960) < 1 and abs(v[1] - 540) < 1


def test_presented_frames_match_canvas():
    from tools.screenshot_all import roundtrip_mad, MAX_MAD, MAX_ALIGN_MAD
    from main import build_acts, render_state
    from core.facts import Facts
    from core.canvas import Ctx
    from core import theme as T
    pygame.init()
    pygame.display.set_mode((64, 64))
    acts = build_acts(Facts())
    canvas = pygame.Surface((T.W, T.H))
    render_state(acts, 4, 2, 6, Ctx(canvas))
    for size in [(1280, 720), (1920, 1200), (1366, 768)]:
        _, m, m_align = roundtrip_mad(canvas, size)
        assert m <= MAX_MAD, (size, m)
        assert m_align <= MAX_ALIGN_MAD, (size, m_align)


def test_check_passes_offline(monkeypatch, capsys):
    def no_network(*a, **k):
        raise OSError("network disabled in test")
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    import main
    assert main.run_check()
    out = capsys.readouterr().out
    assert "FAIL" not in out


def test_every_animation_moment_renders():
    """Beats must draw at every moment of their animations, not only when finished."""
    from main import build_acts, render_timeline
    from core.facts import Facts
    from core.canvas import Ctx
    from core import theme as T
    pygame.init()
    pygame.display.set_mode((64, 64))
    acts = build_acts(Facts())
    ctx = Ctx(pygame.Surface((T.W, T.H)))
    times = tuple(k * 0.07 for k in range(110))
    for ai, act in enumerate(acts):
        for bi in range(len(act.beats)):
            render_timeline(acts, ai, bi, ctx, times)


def test_battery_slider_every_value_and_keys():
    from main import build_acts
    from core.facts import Facts
    from core.canvas import Ctx
    from core import theme as T
    from team.saycan import choice
    pygame.init()
    pygame.display.set_mode((64, 64))
    acts = build_acts(Facts())
    beat = acts[2].beats[1]
    beat.enter()
    beat.settle()
    ctx = Ctx(pygame.Surface((T.W, T.H)))
    for b in range(0, 101):
        beat.slider.value = b
        beat.draw(ctx)
    beat.slider.value = 100
    for _ in range(20):
        beat.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFTBRACKET))
    assert beat.slider.value == 0 and choice(beat.slider.value) == 2
    for _ in range(30):
        beat.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHTBRACKET))
    assert beat.slider.value == 100 and choice(beat.slider.value) == 0


def test_slider_drag_through_mapped_mouse():
    """Drag the 2.2 slider with window-space mouse events through the real mapping."""
    from main import build_acts
    from core.facts import Facts
    from core.canvas import compute_transform, map_point
    pygame.init()
    pygame.display.set_mode((64, 64))
    beat = build_acts(Facts())[2].beats[1]
    beat.enter()
    for size in [(1280, 720), (1920, 1200), (1366, 768)]:
        scale, off, _ = compute_transform(*size)
        sl = beat.slider

        def ev(kind, vx, vy, **kw):
            wpos = (off[0] + vx * scale, off[1] + vy * scale)
            return pygame.event.Event(kind, pos=wpos, vpos=map_point(wpos, scale, off), **kw)

        beat.handle(ev(pygame.MOUSEBUTTONDOWN, sl.x_of(100), sl.y, button=1))
        beat.handle(ev(pygame.MOUSEMOTION, sl.x_of(20), sl.y, buttons=(1, 0, 0), rel=(0, 0)))
        beat.handle(ev(pygame.MOUSEBUTTONUP, sl.x_of(20), sl.y, button=1))
        assert abs(sl.value - 20) <= 1
