"""Act 1: the problem. Two very different bodies, and language at the slow layer."""
from __future__ import annotations

import math

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core import widgets as Wg
from core.anim import lerp_pt, progress, pulse
from core.theme import fonts

# ====================================================================== 1.1
SENT_Y = 214
CARD_W, CARD_H = 830, 520
DRONE_CARD = pygame.Rect(96, 300, CARD_W, CARD_H)
DOG_CARD = pygame.Rect(T.W - 96 - CARD_W, 300, CARD_W, CARD_H)


class TwoBodies(Beat):
    key = "1.1"
    step_durations = (4.5,)

    def _chip(self, ctx, text, center, border, alpha=1.0):
        F = fonts()
        w = F.width(text, T.LABEL) + 40
        r = pygame.Rect(0, 0, w, 50)
        r.center = (int(center[0]), int(center[1]))
        D.rrect(ctx.surf, T.fade(T.mix(T.BG, T.LANG, 0.22), alpha), r, 25)
        D.rrect(ctx.surf, T.fade(border, alpha), r, 25, 3)
        ctx.text(text, r.center, T.LABEL, T.FG, "center", alpha=alpha, record=False)
        ctx.mark(r, "text", text)
        return r

    def _card(self, ctx, rect, title, color, lines, code, alpha, art):
        s = ctx.surf
        D.panel(s, rect, radius=22)
        ctx.mark(rect, "ui", "card")
        art(s, rect, alpha)
        tx = rect.left + 270
        ctx.text(title, (tx, rect.top + 30), T.LABEL + 4, color, "topleft", bold=True, alpha=alpha)
        y = rect.top + 86
        for k, ln in enumerate(lines):
            r = ctx.text_block(ln, (tx, y), T.SMALL + 2, T.FG, width=rect.right - tx - 24, alpha=alpha)
            y = r.bottom + 16
        if code:
            r = Wg.code_line(ctx, code, (tx, y - 6), color=T.TOOL, alpha=alpha)
            y = r.bottom + 16
        sep = rect.top + 366
        pygame.draw.line(s, T.fade(T.PANEL_EDGE, alpha), (rect.left + 28, sep), (rect.right - 28, sep), 2)
        ctx.text(self.txt("receives"), (rect.left + 34, sep + 20), T.TINY, T.DIM, "topleft", alpha=alpha)

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        F = fonts()
        sentence = self.F.mission["sentence"]

        # The sentence across the top.
        sa = progress(t, 0.1, 0.5)
        sw = F.width(sentence, T.BODY)
        sbox = pygame.Rect(0, 0, sw + 60, 62)
        sbox.center = (T.W // 2, SENT_Y)
        D.rrect(s, T.fade(T.PANEL, sa), sbox, 14)
        D.rrect(s, T.fade(T.LANG, sa), sbox, 14, 2)
        ctx.text(sentence, sbox.center, T.BODY, T.FG, "center", alpha=sa)

        def drone_art(surf, rect, a):
            D.drone_side(surf, (rect.left + 130, rect.top + 170), 190, T.DRONE, a, t)
            # forward camera view cone
            cx, cy = rect.left + 210, rect.top + 170
            cone = [(cx, cy), (cx + 52, cy - 36), (cx + 52, cy + 36)]
            D.poly_alpha(surf, T.DRONE, cone, int(90 * a))
            D.polyline(surf, T.fade(T.DRONE, 0.6 * a), cone, 2, closed=True)

        def dog_art(surf, rect, a):
            D.draw_dog(surf, D.gait_pose(t * 5.0, 0.6), rect.left + 130, rect.top + 250, 0.6,
                       T.NEUTRAL, T.DOG, a)

        ca = progress(t, 0.4, 0.6)
        self._card(ctx, DRONE_CARD, self.txt("drone_title"), T.DRONE, self.txt("drone_lines"),
                   self.txt("drone_code"), ca, drone_art)
        self._card(ctx, DOG_CARD, self.txt("dog_title"), T.DOG, self.txt("dog_lines"), None,
                   progress(t, 0.6, 0.6), dog_art)

        # Phrases detach from the sentence and fly to the body that can do them.
        x0 = sbox.left + 30

        def phrase_x(sub):
            i = sentence.find(sub)
            return x0 + F.width(sentence[:i], T.BODY) + F.width(sub, T.BODY) / 2

        slot_y = DRONE_CARD.top + 366 + 90
        chips = [
            (self.txt("chip_drone"), phrase_x("Check the atrium"), [(DRONE_CARD.left + 220, slot_y)], T.DRONE, 1.4),
            (self.txt("chip_dog"), phrase_x("send the dog to it"), [(DOG_CARD.left + 230, slot_y)], T.DOG, 1.8),
            (self.txt("chip_both"), phrase_x("come home"),
             [(DRONE_CARD.left + 560, slot_y), (DOG_CARD.left + 560, slot_y)], T.HOME, 2.3),
        ]
        for text, sx, dests, col, t0 in chips:
            lift = progress(t, t0, 0.35)
            if lift <= 0:
                continue
            start = (sx, SENT_Y + 6 + 46 * lift)
            for k, dest in enumerate(dests):
                p = progress(t, t0 + 0.4 + 0.15 * k, 0.9)
                pos = lerp_pt(start, dest, p)
                border = T.mix(T.LANG, col, p)
                self._chip(ctx, text, pos, border, min(1.0, lift * 1.5))

        Wg.source_line(ctx, self.txt("source"), alpha=progress(t, 0.8, 0.5))


# ====================================================================== 1.2
AX_X = 520
Y_TOP, Y_BOT = 300, 790           # 0.1 Hz and 200 Hz
F_TOP, F_BOT = 0.1, 200.0
SLOW = 50.0                       # every pulse is slowed by this same factor
REF_X = 1310


def hz_y(f):
    a = (math.log10(f) - math.log10(F_TOP)) / (math.log10(F_BOT) - math.log10(F_TOP))
    return Y_TOP + a * (Y_BOT - Y_TOP)


class ClockLadder(Beat):
    key = "1.2"
    step_durations = (4.0,)

    def _pulse_dot(self, s, center, hz, color, alpha, t):
        """A dot that flashes once per (slowed) period, with a fading ring."""
        period = SLOW / hz
        ph = (t % period) / period
        D.disc(s, T.fade(color, alpha), center, 10)
        r = 10 + 26 * ph
        a = alpha * (1 - ph) ** 1.5
        if a > 0.02:
            D.ring(s, T.fade(color, a), center, r, 3)

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        mine = self.F.source("mine")

        aa = progress(t, 0.1, 0.6)
        D.line(s, T.fade(T.DIM, aa), (AX_X, Y_TOP), (AX_X, Y_BOT), 3)
        for f, lbl in [(0.1, "0.1 Hz"), (1, "1 Hz"), (10, "10 Hz"), (100, "100 Hz")]:
            y = hz_y(f)
            D.line(s, T.fade(T.DIM, aa), (AX_X - 10, y), (AX_X, y), 2)
            ctx.text(lbl, (AX_X - 18, y), T.TINY, T.DIM, "midright", alpha=aa)
        ctx.text(self.txt("slowed"), (AX_X, Y_BOT + 22), T.TINY, T.DIM, "midtop", alpha=aa)

        g = self.F.value("go2_walk")
        rows = [
            (self.txt("owl"), self.F.value("owlv2_rate"), T.NEUTRAL, 0.5),
            (self.txt("nav"), self.F.value("go2_nav_rate"), T.DOG, 0.8),
            (self.txt("walk"), g["policy_hz"], T.DOG, 1.1),
            (self.txt("pd"), g["pd_hz"], T.DOG, 1.4),
        ]
        # The LLM row sits above the top tick: it has no rate.
        la = progress(t, 0.3, 0.6)
        ly = 214
        D.dashed(s, T.fade(T.LANG, la), [(AX_X, ly + 16), (AX_X, Y_TOP - 12)], 2, 6, 6)
        D.rrect(s, T.fade(T.LANG, la), pygame.Rect(AX_X - 13, ly - 13, 26, 26), 6)
        ctx.text(self.txt("llm"), (AX_X + 44, ly), T.LABEL, T.LANG, "midleft", alpha=la)
        for text, hz, col, t0 in rows:
            a = progress(t, t0, 0.5)
            y = hz_y(hz)
            D.line(s, T.fade(T.GRID, a), (AX_X + 14, y), (AX_X + 34, y), 2)
            self._pulse_dot(s, (AX_X, y), hz, col, a, t)
            ctx.text(text, (AX_X + 44, y), T.LABEL, T.FG, "midleft", alpha=a)
        wa = progress(t, 1.2, 0.5)
        ctx.text(self.txt("walk_note"), (AX_X + 44, hz_y(g["policy_hz"]) + 34), T.TINY, T.DIM, "midleft", alpha=wa)
        Wg.source_line(ctx, "Rows on the axis: " + mine[0].lower() + mine[1:], alpha=progress(t, 1.4, 0.5))

        # Brackets on the left: language plans; policies and controllers move.
        ba = progress(t, 1.8, 0.6)
        bx = 300
        D.polyline(s, T.fade(T.LANG, ba), [(bx + 14, ly - 26), (bx, ly - 26), (bx, ly + 26), (bx + 14, ly + 26)], 3)
        ctx.text_block(self.txt("bracket_lang"), (bx - 16, ly), T.SMALL, T.LANG, width=190, anchor="midright",
                       align="right", alpha=ba)
        y0, y1 = hz_y(self.F.value("go2_nav_rate")) - 22, Y_BOT + 14
        D.polyline(s, T.fade(T.DOG, ba), [(bx + 14, y0), (bx, y0), (bx, y1), (bx + 14, y1)], 3)
        ctx.text_block(self.txt("bracket_move"), (bx - 16, (y0 + y1) / 2), T.SMALL, T.DOG, width=200,
                       anchor="midright", align="right", alpha=ba)

        # Reference markers from the readings, on the same scale.
        ra = progress(t, 2.3, 0.6)
        D.dotted(s, T.fade(T.FAINT, ra), [(REF_X, Y_TOP), (REF_X, Y_BOT)], 2.2, 12)
        ctx.text(self.txt("ref_title"), (REF_X, 214), T.SMALL, T.DIM, "midleft", bold=True, alpha=ra)
        r2 = self.F.value("rt2_rate")["model_55b_hz"]
        ya, yb = hz_y(r2[0]), hz_y(r2[1])
        D.rrect(s, T.fade(T.NEUTRAL, ra), pygame.Rect(REF_X - 8, int(ya), 16, int(yb - ya)), 6)
        ctx.text(self.txt("rt2"), (REF_X + 28, (ya + yb) / 2 - 12), T.SMALL, T.FG, "midleft", alpha=ra)
        ctx.text(self.F.source("rt2"), (REF_X + 28, (ya + yb) / 2 + 16), T.TINY, T.DIM, "midleft", alpha=ra)
        rm = self.F.value("rma_rates")
        for key, hz in (("rma_base", rm["base_policy_hz"]), ("rma_adapt", rm["adaptation_hz"])):
            y = hz_y(hz)
            D.ring(s, T.fade(T.NEUTRAL, ra), (REF_X, y), 9, 3)
            ctx.text(self.txt(key), (REF_X + 28, y), T.SMALL, T.FG, "midleft", alpha=ra)
        ctx.text(self.F.source("rma"), (REF_X + 28, hz_y(rm["base_policy_hz"]) + 28), T.TINY, T.DIM, "midleft",
                 alpha=ra)

        # The Tello's flight controller: on board, no rate shown.
        ta = progress(t, 2.6, 0.6)
        tb = pygame.Rect(REF_X - 30, 806, 560, 80)
        D.rrect(s, T.fade(T.PANEL, ta), tb, 12)
        D.dashed_rect(s, T.fade(T.DRONE, ta * 0.8), tb, 2, 10, 7)
        ctx.mark(tb, "ui", "tello box")
        ctx.text(self.txt("tello"), (tb.left + 24, tb.top + 14), T.SMALL, T.DRONE, alpha=ta)
        ctx.text(self.txt("tello_note"), (tb.left + 24, tb.top + 46), T.TINY, T.DIM, alpha=ta)


def make(F):
    a = Act([TwoBodies(F), ClockLadder(F)])
    a.number = 1
    return a
