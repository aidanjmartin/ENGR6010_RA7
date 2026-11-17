"""One Sentence, Two Robots: an in-class presentation on LLM mission control for
a quadruped and a drone from one home PC. Nothing trains, downloads, or calls an LLM.

    python main.py                 run (windowed 1600 x 900; F toggles full screen)
    python main.py --fullscreen    start full screen
    python main.py --act 3         start at act 3
    python main.py --check         offline self-check, prints PASS or FAIL
    python main.py --screenshots out/   render every beat and window size
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def build_acts(F):
    from acts import act0_title, act1_problem, act2_interface, act3_grounding, act4_team, act5_close
    return [m.make(F) for m in (act0_title, act1_problem, act2_interface, act3_grounding, act4_team, act5_close)]


def all_states(acts):
    """Yield (act_index, beat_index, step) for every beat and every step inside it."""
    for ai, act in enumerate(acts):
        for bi, beat in enumerate(act.beats):
            for st in range(beat.steps):
                yield ai, bi, st


def render_timeline(acts, ai, bi, ctx, times=(0.0, 0.05, 0.2, 0.5, 1.0, 1.5, 2.2, 3.0, 4.5, 7.0)):
    """Draw a beat at several moments of its animation, stepping through every step."""
    from core import theme as T
    act = acts[ai]
    act.i = bi
    beat = act.beats[bi]
    beat.enter()
    for st in range(beat.steps):
        if st:
            beat.next_step()
        last = 0.0
        for t in times:
            beat.update(t - last)
            last = t
            ctx.surf.fill(T.BG)
            ctx.clear()
            act.draw(ctx)
    return beat


def render_state(acts, ai, bi, st, ctx, settle=True):
    """Put a beat at a given step with its animations finished, then draw one frame."""
    from core import theme as T
    act = acts[ai]
    act.i = bi
    beat = act.beats[bi]
    beat.enter()
    for _ in range(st):
        beat.next_step()
        if settle:
            beat.settle()
    if settle:
        beat.settle()
    ctx.surf.fill(T.BG)
    ctx.clear()
    act.draw(ctx)
    return beat


# ====================================================================== app
class App:
    def __init__(self, fullscreen=False, start_act=0):
        import pygame
        from core import theme as T
        from core.canvas import Presenter, Ctx
        from core.facts import Facts
        self.pg = pygame
        self.T = T
        pygame.init()
        pygame.display.set_caption("One Sentence, Two Robots")
        self.presenter = Presenter()
        self.presenter.set_mode(fullscreen)
        self.F = Facts()
        self.acts = build_acts(self.F)
        self.canvas = pygame.Surface((T.W, T.H)).convert()
        self.scene = pygame.Surface((T.W, T.H)).convert()
        self.ctx = Ctx(self.scene)
        self.ctx.recording = False
        self.a = max(0, min(len(self.acts) - 1, start_act))
        self.acts[self.a].enter()
        self.show_debug = False
        self.show_help = False
        self.show_indicator = True
        self.trans_old = None
        self.trans_t = 1.0
        self.mouse_v = None
        self.clock = pygame.time.Clock()

    # ------------------------------------------------------------- navigation
    @property
    def act(self):
        return self.acts[self.a]

    def _ident(self):
        return (self.a, self.act.i)

    def _begin_transition(self, before):
        if self._ident() != before:
            self.trans_old = self.canvas.copy()
            self.trans_t = 0.0

    def next(self):
        before = self._ident()
        if not self.act.next_beat() and self.a < len(self.acts) - 1:
            self.a += 1
            self.act.enter()
        self._begin_transition(before)

    def prev(self):
        before = self._ident()
        if not self.act.prev_beat() and self.a > 0:
            self.a -= 1
            self.act.enter(at_end=True)
        self._begin_transition(before)

    def jump(self, k):
        if 0 <= k < len(self.acts):
            before = self._ident()
            self.a = k
            self.act.enter()
            self._begin_transition(before)

    # ------------------------------------------------------------- events
    def handle(self, ev):
        pg = self.pg
        if ev.type == pg.QUIT:
            return False
        if ev.type in (pg.VIDEORESIZE, pg.WINDOWRESIZED, pg.WINDOWSIZECHANGED):
            self.presenter.update_transform()
            return True
        if ev.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION):
            v = self.presenter.map_mouse(ev.pos)
            self.mouse_v = v
            d = dict(ev.dict)
            d["vpos"] = v
            ev = pg.event.Event(ev.type, d)
            self.act.handle(ev)
            return True
        if ev.type == pg.KEYDOWN:
            k = ev.key
            if k == pg.K_ESCAPE:
                if self.show_help:
                    self.show_help = False
                    return True
                return False
            if k in (pg.K_SPACE, pg.K_RIGHT, pg.K_PAGEDOWN):
                self.next()
            elif k in (pg.K_LEFT, pg.K_PAGEUP):
                self.prev()
            elif k == pg.K_r:
                self.act.reset_beat()
            elif k == pg.K_f:
                self.presenter.toggle()
            elif k == pg.K_d:
                self.show_debug = not self.show_debug
            elif k == pg.K_h:
                self.show_help = not self.show_help
            elif k == pg.K_i:
                self.show_indicator = not self.show_indicator
            elif pg.K_0 <= k <= pg.K_5:
                self.jump(k - pg.K_0)
            else:
                self.act.handle(ev)
        return True

    # ------------------------------------------------------------- frame
    def frame(self, dt):
        pg, T = self.pg, self.T
        from core.anim import ease
        self.act.update(dt)
        self.scene.fill(T.BG)
        self.act.draw(self.ctx)
        if self.trans_t < 1.0 and self.trans_old is not None:
            self.trans_t = min(1.0, self.trans_t + dt / 0.45)
            e = ease(self.trans_t)
            self.canvas.fill(T.BG)
            old = self.trans_old
            old.set_alpha(int(255 * (1 - e)))
            self.canvas.blit(old, (int(-70 * e), 0))
            self.scene.set_alpha(int(255 * e))
            self.canvas.blit(self.scene, (int(70 * (1 - e)), 0))
            self.scene.set_alpha(None)
        else:
            self.canvas.blit(self.scene, (0, 0))
        self.draw_overlays(self.canvas)
        self.presenter.present(self.canvas)

    def draw_overlays(self, surf):
        from core.canvas import Ctx
        from core import draw as D
        T = self.T
        pg = self.pg
        c = Ctx(surf)
        c.recording = False
        if self.show_indicator:
            beat_no = self.act.i + 1
            n = len(self.act.beats)
            b = self.act.beat
            label = f"{self.a} · {beat_no}/{n}"
            if b.steps > 1:
                label += "  " + "".join("●" if k <= b.step else "○" for k in range(b.steps))
            c.text(label, (T.W - T.SAFE - 8, T.SAFE + 6), T.TINY, T.FAINT, "topright")
        if self.show_debug:
            p = self.presenter
            info = [f"window {p.window_size[0]} x {p.window_size[1]}   surface {p.surface_size[0]} x {p.surface_size[1]}",
                    f"scale {p.scale:.4f}   offset {p.offset}   mouse ratio {p.ratio[0]:.2f}, {p.ratio[1]:.2f}",
                    f"mouse (virtual) {('%.1f, %.1f' % self.mouse_v) if self.mouse_v else 'outside canvas'}"]
            box = pg.Rect(T.W // 2 - 520, T.H - 190, 1040, 140)
            pg.draw.rect(surf, (0, 0, 0), box, border_radius=10)
            pg.draw.rect(surf, T.TOOL, box, 2, border_radius=10)
            for k, s in enumerate(info):
                c.text(s, (box.left + 24, box.top + 18 + k * 38), T.TINY, T.TOOL)
            pg.draw.rect(surf, T.TOOL, pg.Rect(0, 0, T.W, T.H), 2)
            if self.mouse_v:
                x, y = self.mouse_v
                pg.draw.line(surf, T.TOOL, (x - 30, y), (x + 30, y), 2)
                pg.draw.line(surf, T.TOOL, (x, y - 30), (x, y + 30), 2)
                D.ring(surf, T.TOOL, (x, y), 12, 2)
        if self.show_help:
            self.draw_help(c)

    def draw_help(self, c):
        pg, T = self.pg, self.T
        rows = [("Space or →", "next beat or step"), ("←", "previous beat or step"), ("0 to 5", "jump to act"),
                ("R", "replay current beat"), ("[ and ]", "step the battery slider in 2.2"), ("Mouse drag", "sliders"),
                ("F", "toggle full screen"), ("D", "alignment debug overlay"), ("H", "this help"),
                ("I", "hide or show beat indicator"), ("Esc", "quit")]
        box = pg.Rect(0, 0, 820, 120 + 52 * len(rows))
        box.center = (T.W // 2, T.H // 2)
        dim = pg.Surface((T.W, T.H), pg.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        c.surf.blit(dim, (0, 0))
        pg.draw.rect(c.surf, T.PANEL, box, border_radius=18)
        pg.draw.rect(c.surf, T.PANEL_EDGE, box, 2, border_radius=18)
        c.text("Controls", (box.left + 50, box.top + 36), T.LABEL + 4, T.FG, bold=True)
        for k, (key, what) in enumerate(rows):
            y = box.top + 110 + 52 * k
            c.text(key, (box.left + 50, y), T.SMALL + 2, T.TOOL, bold=True)
            c.text(what, (box.left + 300, y), T.SMALL + 2, T.FG)

    def run(self):
        pg = self.pg
        running = True
        while running:
            dt = min(0.05, self.clock.tick_busy_loop(60) / 1000.0)
            for ev in pg.event.get():
                if not self.handle(ev):
                    running = False
                    break
            if running:
                self.frame(dt)
        pg.quit()


# ====================================================================== check
def run_check() -> bool:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    ok = True

    def report(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}{'  ' + detail if detail else ''}")

    try:
        from core.facts import Facts
        from tests.test_facts import check_facts
        F = Facts()
        problems = check_facts(F)
        report("facts.yaml loads and matches the test values", not problems, "; ".join(problems[:3]))
    except Exception as e:  # noqa: BLE001
        report("facts.yaml loads and matches the test values", False, repr(e))
        return False

    import pygame
    pygame.init()
    pygame.display.set_mode((64, 64))
    from core.theme import fonts
    f = fonts()
    report("UI font found", f.family is not None, f"{f.family}: {f.regular[0]}")
    report("monospace font found", f.mono_family is not None, f"{f.mono_family}: {f.mono_regular[0]}")
    try:
        from tests.test_checker import checker_problems
        problems = checker_problems()
        report("tool checker cases give the expected verdicts", not problems, "; ".join(problems[:3]))
    except Exception as e:  # noqa: BLE001
        report("tool checker cases give the expected verdicts", False, repr(e))

    from core.canvas import Ctx
    from core import theme as T
    acts = build_acts(F)
    canvas = pygame.Surface((T.W, T.H))
    ctx = Ctx(canvas)
    n = 0
    for ai, bi, st in all_states(acts):
        key = acts[ai].beats[bi].key
        try:
            render_state(acts, ai, bi, st, ctx)
            n += 1
        except Exception as e:  # noqa: BLE001
            report(f"beat {key} step {st + 1} renders", False, repr(e))
    beats = sum(len(a.beats) for a in acts)
    report("every beat renders one frame", n == sum(1 for _ in all_states(acts)), f"{beats} beats, {n} frames")
    bad = []
    for ai, act in enumerate(acts):
        for bi, beat in enumerate(act.beats):
            try:
                render_timeline(acts, ai, bi, ctx)
            except Exception as e:  # noqa: BLE001
                bad.append(f"{beat.key}: {e!r}")
    report("every animation frame renders", not bad, "; ".join(bad[:2]))
    print("PASS" if ok else "FAIL")
    return ok


# ====================================================================== entry
def main(argv=None):
    ap = argparse.ArgumentParser(description="One Sentence, Two Robots presentation")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fullscreen", action="store_true", help="start full screen")
    g.add_argument("--windowed", action="store_true", help="start windowed (default)")
    ap.add_argument("--act", type=int, default=0, help="start at act N (0 to 5)")
    ap.add_argument("--check", action="store_true", help="offline self-check")
    ap.add_argument("--screenshots", metavar="OUTDIR", help="render every beat and window size to OUTDIR")
    args = ap.parse_args(argv)
    if args.check:
        return 0 if run_check() else 1
    if args.screenshots:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        from tools.screenshot_all import run
        return 0 if run(args.screenshots) else 1
    App(fullscreen=args.fullscreen, start_act=args.act).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
