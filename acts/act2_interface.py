"""Act 2: what the LLM should say. The interface ladder, then Say x Can for a team."""
from __future__ import annotations

import math

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core import widgets as Wg
from core.anim import progress, pulse
from team import saycan

# ====================================================================== 2.1
RUNG_TOP, RUNG_H, RUNG_GAP = 212, 110, 6
COL_NAME, COL_CODE, COL_WHO, COL_NUM = 280, 640, 1170, 1500
RIGHT = T.W - T.MARGIN


def value_map(surf, origin, cell=26, alpha=1.0):
    """A small isometric 3D grid: one bright goal cell, a few dark obstacles."""
    ox, oy = origin
    nx, ny = 5, 3
    goal, obstacles = (4, 1), {(1, 0), (2, 2), (2, 1)}

    def P(i, j, k=0):
        return (ox + (i - j) * cell, oy + (i + j) * cell * 0.5 - k * cell * 0.8)

    for i in range(nx):
        for j in range(ny):
            top = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
            if (i, j) == goal:
                c = T.fade(T.TOOL, alpha)
            elif (i, j) in obstacles:
                c = T.fade(T.mix(T.BG, T.WARN, 0.25), alpha)
            else:
                c = T.fade(T.mix(T.PANEL, T.NEUTRAL, 0.12), alpha)
            D.poly(surf, c, top)
            D.polyline(surf, T.fade(T.PANEL_EDGE, alpha), top, 1, closed=True)
            if (i, j) in obstacles:
                up = [P(i, j, 1), P(i + 1, j, 1), P(i + 1, j + 1, 1), P(i, j + 1, 1)]
                D.poly(surf, T.fade(T.mix(T.BG, T.WARN, 0.4), alpha), up)
                D.poly(surf, T.fade(T.mix(T.BG, T.WARN, 0.18), alpha),
                       [P(i, j + 1), P(i + 1, j + 1), P(i + 1, j + 1, 1), P(i, j + 1, 1)])


class Ladder(Beat):
    key = "2.1"
    step_durations = (4.5,)
    HIGHLIGHT_AT = 3.0

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        rungs = self.txt("rungs")

        ha = progress(t, 0.1, 0.5)
        ctx.text(self.txt("head_out"), (COL_CODE, RUNG_TOP - 14), T.TINY, T.DIM, "bottomleft", bold=True, alpha=ha)
        ctx.text(self.txt("head_who"), (COL_WHO, RUNG_TOP - 14), T.TINY, T.DIM, "bottomleft", bold=True, alpha=ha)
        ctx.text(self.txt("head_num"), (COL_NUM, RUNG_TOP - 14), T.TINY, T.DIM, "bottomleft", bold=True, alpha=ha)

        # The spine: language at the top, motors at the bottom.
        y_end = RUNG_TOP + 5 * (RUNG_H + RUNG_GAP) - RUNG_GAP
        D.arrow(s, T.fade(T.DIM, ha), (112, RUNG_TOP + 70), (112, y_end - 10), 3, 16)
        ctx.text_block(self.txt("top"), (128, RUNG_TOP + 6), T.TINY, T.LANG, width=110, alpha=ha)
        ctx.text_block(self.txt("bottom"), (128, y_end - 60), T.TINY, T.DOG, width=110, alpha=ha)

        for k, r in enumerate(rungs):
            a = progress(t, 0.3 + 0.4 * k, 0.5)
            if a <= 0:
                continue
            top = RUNG_TOP + k * (RUNG_H + RUNG_GAP)
            rect = pygame.Rect(COL_NAME - 24, top, RIGHT - COL_NAME + 24, RUNG_H)
            D.rrect(s, T.fade(T.PANEL, a), rect, 14)
            side = T.mix(T.LANG, T.DOG, k / 4)
            D.rrect(s, T.fade(side, a), pygame.Rect(rect.left, rect.top, 8, rect.height), 4)
            ctx.mark(rect, "ui", "rung")
            ctx.text(f"{k + 1}. {r['name']}", (COL_NAME, top + 18), T.LABEL, T.FG, bold=True, alpha=a)
            ctx.text(r["paper"], (COL_NAME, top + 56), T.SMALL, T.DIM, alpha=a)
            if r["code"]:
                n = len(r["code"])
                y0 = top + RUNG_H / 2 - n * 30 / 2 - 2
                for i, line in enumerate(r["code"]):
                    Wg.code_line(ctx, line, (COL_CODE, y0 + i * 30), T.TOOL if k == 0 else T.NEUTRAL, alpha=a)
            else:
                value_map(s, (COL_CODE + 90, top + 18), 22, a)
                ctx.mark(pygame.Rect(COL_CODE, top + 8, 260, RUNG_H - 16), "ui", "value map")
            ctx.text_block(r["who"], (COL_WHO, top + RUNG_H / 2), T.SMALL, T.FG, width=300, anchor="midleft",
                           alpha=a)
            if r["result"]:
                rb = ctx.text_block(r["result"], (COL_NUM, top + 14), T.SMALL, T.FG, width=RIGHT - COL_NUM - 10,
                                    alpha=a, max_lines=2)
                ctx.text("Reported by " + r["source"], (COL_NUM, rb.bottom + 6), T.TINY, T.DIM, alpha=a)
            else:
                ctx.text(self.txt("no_number"), (COL_NUM, top + 22), T.SMALL, T.FAINT, alpha=a)
                ctx.text(r["source"], (COL_NUM, top + 56), T.TINY, T.DIM, alpha=a)

        # The frame settles on rung 1: our team.
        hp = progress(t, self.HIGHLIGHT_AT, 0.7)
        if hp > 0:
            top = RUNG_TOP
            r0 = pygame.Rect(COL_NAME - 34, top - 10, RIGHT - COL_NAME + 44, RUNG_H + 20)
            big = r0.inflate(int(60 * (1 - hp)), int(60 * (1 - hp)))
            D.rrect(s, T.fade(T.TOOL, hp), big, 18, 4)
            ctx.text(self.txt("highlight"), (COL_NAME - 24, y_end + 34), T.LABEL, T.TOOL, "topleft", alpha=hp)


# ====================================================================== 2.2
CHART_X0, CHART_LBL_W, CHART_BAR_W = 96, 210, 270
ROW_X = 760
SAY_X, CAN_X, PROD_X, BAR_W = 1200, 1420, 1640, 190
ROW_Y0, ROW_DY = 330, 104
SLIDER_Y = 790


class SayCan(Beat):
    key = "2.2"
    step_durations = (3.0,)

    def __init__(self, facts):
        super().__init__(facts)
        self.reserve = float(facts.mission["reserve_pct"])
        self.slider = Wg.Slider(1000, 1600, SLIDER_Y, 0, 100, 100, color=T.DRONE, step=1)

    def on_enter(self):
        self.slider.value = 100
        self.slider.drag = False

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFTBRACKET:
                self.slider.value = max(0, self.slider.value - 5)
                return True
            if event.key == pygame.K_RIGHTBRACKET:
                self.slider.value = min(100, self.slider.value + 5)
                return True
        return self.slider.handle(event)

    def _chart(self, ctx, t):
        s = ctx.surf
        res = self.F.value("saycan_results")
        keys = ["palm_saycan", "flan_saycan", "palm_alone", "flan_alone", "behavioral_cloning"]
        names = self.txt("groups")
        ca = progress(t, 0.1, 0.6)
        ctx.text(self.txt("chart_title"), (CHART_X0, 196), T.LABEL, T.FG, bold=True, alpha=ca)
        bx = CHART_X0 + CHART_LBL_W
        y = 262
        for k, (key, name) in enumerate(zip(keys, names)):
            a = progress(t, 0.2 + 0.12 * k, 0.5)
            ctx.text_block(name, (CHART_X0, y + 6), T.SMALL, T.FG, width=CHART_LBL_W - 16, alpha=a)
            v = res[key]
            for j, (field, hatched) in enumerate((("plan", False), ("execute", True))):
                by = y + j * 34
                if field in v:
                    Wg.hbar(ctx, (bx, by, CHART_BAR_W, 24), v[field] / 100.0 * a, T.LANG if not hatched else T.NEUTRAL,
                            a, hatched=hatched)
                    ctx.text(f"{v[field]}%", (bx + CHART_BAR_W + 12, by + 12), T.SMALL, T.FG, "midleft", alpha=a)
                else:
                    ctx.text(self.txt("not_reported"), (bx, by + 12), T.TINY, T.FAINT, "midleft", alpha=a)
            y += 96
        Wg.legend(ctx, (CHART_X0, y + 6), [(self.txt("plan"), T.LANG, "bar"), (self.txt("execute"), T.NEUTRAL, "hatched")],
                  alpha=ca, horizontal=True, panel=False)
        Wg.source_line(ctx, self.F.source("saycan"), (CHART_X0, T.SOURCE_Y), alpha=ca)

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        self._chart(ctx, t)

        # Divider between the reported chart and the illustration.
        pygame.draw.line(s, T.PANEL_EDGE, (ROW_X - 50, 200), (ROW_X - 50, 840), 2)

        ia = progress(t, 0.4, 0.5)
        Wg.status_tag(ctx, "illus", (ROW_X, 196), alpha=ia, text=self.txt("illus"))
        heads = self.txt("heads")
        notes = [self.txt("say_note"), self.txt("can_note"), ""]
        for x, h, n, col in zip((SAY_X, CAN_X, PROD_X), heads, notes, (T.LANG, T.FG, T.TOOL)):
            ctx.text(h, (x, 262), T.LABEL, col, "midleft", bold=True, alpha=ia)
            if n:
                ctx.text(n, (x, 292), T.TINY, T.DIM, "midleft", alpha=ia)

        battery = float(self.slider.value)
        sc = saycan.scores(battery, self.reserve)
        best = max(range(len(sc)), key=lambda i: sc[i][2])
        labels = self.txt("candidates")
        robots = ["drone", "dog", "drone", "dog"]
        for k, (label, robot, (say, can, prod)) in enumerate(zip(labels, robots, sc)):
            a = progress(t, 0.6 + 0.15 * k, 0.5)
            cy = ROW_Y0 + k * ROW_DY + 30
            col = T.DRONE if robot == "drone" else T.DOG
            if robot == "drone":
                D.drone_top(s, (ROW_X + 26, cy), 0.0, 44, col, a, t)
            else:
                D.dog_top(s, (ROW_X + 24, cy), 0.0, 40, col, a, t * 6)
            ctx.text_block(label, (ROW_X + 66, cy), T.SMALL, T.FG, width=SAY_X - ROW_X - 100, anchor="midleft",
                           alpha=a)
            Wg.hbar(ctx, (SAY_X, cy - 13, BAR_W, 26), say, T.LANG, a)
            Wg.hbar(ctx, (CAN_X, cy - 13, BAR_W, 26), can, col, a)
            Wg.hbar(ctx, (PROD_X, cy - 13, BAR_W - 60, 26), prod, T.TOOL if k == best else T.NEUTRAL, a)
            ctx.text(f"{prod:.2f}", (PROD_X + BAR_W - 50, cy), T.SMALL, T.FG, "midleft", alpha=a)
            if k == best and a > 0.5:
                fr = pygame.Rect(ROW_X - 14, cy - 44, T.W - T.MARGIN - ROW_X + 28, 88)
                D.rrect(s, T.fade(T.TOOL, a), fr, 16, 3)
                Wg.tag(ctx, self.txt("chosen"), (fr.right - 12, fr.top), T.TOOL, "midright", alpha=a, icon="check")

        # Battery slider with the reserve line.
        sa = progress(t, 1.2, 0.5)
        sl = self.slider
        rx = sl.x_of(self.reserve)
        D.line(s, T.fade(T.WARN, sa), (rx, SLIDER_Y - 26), (rx, SLIDER_Y + 26), 3)
        sl.draw(ctx, alpha=sa, label=self.txt("battery"), show_value=f"{int(round(battery))}%")
        col = T.WARN if battery < self.reserve else T.DIM
        Wg.tag(ctx, self.txt("reserve"), (rx, SLIDER_Y + 38), T.WARN, "midtop", alpha=sa, icon="warn")
        ctx.text(self.txt("keys"), (sl.x1, SLIDER_Y + 46), T.TINY, col if battery < self.reserve else T.FAINT,
                 "topright", alpha=sa)


def make(F):
    a = Act([Ladder(F), SayCan(F)])
    a.number = 2
    return a
