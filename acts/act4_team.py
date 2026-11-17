"""Act 4: the team. Why a drone helps, one home point, and a scripted mission."""
from __future__ import annotations

import math

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core import widgets as Wg
from core.anim import ease, lerp, progress, pulse
from core.theme import fonts
from sim.mission import CAMERA_HALF_ANGLE, CAMERA_RANGE, FLIGHT_MINUTES, Mission
from team.checker import format_call
from acts.act3_grounding import wrap_call


# ====================================================================== 4.1
class WhyDrone(Beat):
    key = "4.1"
    step_durations = (3.0,)

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        colors = [T.NEUTRAL, T.LANG, T.DRONE]
        rows = [(lab, val, c) for (lab, val), c in zip(self.txt("rows"), colors)]
        alphas = [progress(t, 0.3 + 0.25 * k, 0.5) for k in range(3)]
        Wg.study_card(ctx, (96, 196, 820, 580), rows, alphas, title=self.txt("card_title"))

        tri = self.F.value("cladera_triage")
        texts = self.F["cladera_triage"]["texts"]
        vals = [tri["ground_alone"], tri["air_ground"], tri["ground_true_map"]]
        labels = self.txt("bars")
        vtext = [texts["ground_alone"], texts["air_ground"], texts["true_map"]]
        cols = [T.WARN, T.DRONE, T.NEUTRAL]
        x0, base, top = 1010, 680, 300
        ca = progress(t, 0.2, 0.5)
        ctx.text(self.txt("chart_title"), (x0, 196), T.LABEL, T.FG, bold=True, alpha=ca)
        D.line(s, T.fade(T.DIM, ca), (x0, base), (T.W - T.MARGIN, base), 2)
        centers = [1160, 1440, 1700]
        tops = []
        for k, (v, lab, vt, col, cx) in enumerate(zip(vals, labels, vtext, cols, centers)):
            g = progress(t, 0.8 + 0.4 * k, 0.8)
            h = (base - top) * v / 100.0 * g
            r = pygame.Rect(int(cx - 75), int(base - h), 150, int(h))
            if h > 1:
                if k == 2:
                    D.hatched_rect(s, T.fade(col, ca), r, spacing=10, w=2, fill=T.fade(T.mix(T.BG, col, 0.25), ca))
                else:
                    D.rrect(s, T.fade(col, ca), r, 6)
            else:
                D.line(s, T.fade(col, ca), (cx - 75, base - 2), (cx + 75, base - 2), 5)
            ctx.mark(pygame.Rect(cx - 75, top, 150, base - top), "ui", "bar")
            va = progress(t, 1.2 + 0.4 * k, 0.4)
            vr = ctx.text(vt, (cx, base - h - 14), T.TITLE - 10, col if k != 2 else T.FG, "midbottom", bold=True,
                          alpha=va)
            tops.append(vr)
            ctx.text_block(lab, (cx, base + 16), T.SMALL, T.FG, width=250, anchor="midtop", align="center", alpha=ca)
        ra = progress(t, 2.0, 0.4)
        ctx.text(texts["runs"], (centers[1], tops[1].top - 6), T.SMALL, T.DIM, "midbottom", alpha=ra)
        aa = progress(t, 2.4, 0.6)
        if aa > 0:
            p0 = (centers[0] + 40, base - 70)
            p1 = (centers[1] - 92, top + 120)
            D.arrow(s, T.fade(T.FG, aa), p0, (lerp(p0[0], p1[0], aa), lerp(p0[1], p1[1], aa)), 5, 22)
        Wg.source_line(ctx, self.F.source("cladera"), (x0, T.SOURCE_Y), alpha=ca)


# ====================================================================== 4.2
PC = pygame.Rect(560, 186, 800, 586)
INNER_X, INNER_W, INNER_H, INNER_TOP, INNER_DY = 592, 736, 84, 252, 100


class HomePoint(Beat):
    key = "4.2"
    step_durations = (4.5,)

    def _box(self, ctx, rect, label, status, a, note=None):
        s = ctx.surf
        if status == "built":
            D.rrect(s, T.fade(T.mix(T.BG, T.HOME, 0.16), a), rect, 12)
            D.rrect(s, T.fade(T.HOME, a), rect, 12, 3)
        else:
            D.rrect(s, T.fade(T.PANEL, a), rect, 12)
            D.dashed_rect(s, T.fade(T.mix(T.HOME, T.BG, 0.3), a), rect, 2, 12, 8)
        ctx.mark(rect, "ui", label)
        ly = rect.centery if not note else rect.centery - 13
        ctx.text(label, (rect.left + 24, ly), T.LABEL - 2, T.FG, "midleft", alpha=a)
        if note:
            ctx.text(note, (rect.left + 24, rect.centery + 20), T.TINY, T.DIM, "midleft", alpha=a)
        Wg.status_tag(ctx, status, (rect.right - 18, rect.centery), "midright", alpha=a)

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        pa = progress(t, 0.1, 0.5)
        D.rrect(s, T.fade(T.PANEL, pa), PC, 22)
        D.rrect(s, T.fade(T.HOME, pa), PC, 22, 3)
        ctx.mark(PC, "ui", "pc")
        D.pc_tower(s, (PC.left + 52, PC.top + 52), 40, T.HOME, pa)
        ctx.text(self.txt("pc"), (PC.left + 84, PC.top + 32), T.LABEL + 2, T.HOME, "midleft", bold=True, alpha=pa)
        boxes = [("box_llm", "plan", None), ("box_checker", "plan", None), ("box_state", "plan", None),
                 ("box_owl", "built", None), ("box_nav", "built", self.txt("nav_note"))]
        for k, (key, status, note) in enumerate(boxes):
            a = progress(t, 0.5 + 0.3 * k, 0.5)
            r = pygame.Rect(INNER_X, INNER_TOP + k * INNER_DY, INNER_W, INNER_H)
            self._box(ctx, r, self.txt(key), status, a, note)

        # Dog link (built and measured).
        la = progress(t, 2.2, 0.5)
        link_y = 470
        lb = ctx.text_block(self.txt("dog_link"), (96, 196), T.SMALL, T.DOG, width=420, alpha=la)
        Wg.status_tag(ctx, "built", (96, lb.bottom + 14), alpha=la)
        D.draw_dog(s, D.dog_pose(D.STAND), 230, link_y + 50, 0.5, T.NEUTRAL, T.DOG, la)
        D.line(s, T.fade(T.HOME, la), (360, link_y), (PC.left, link_y), 4)
        rr = ctx.text_block(self.txt("dog_result"), (96, link_y + 84), T.SMALL, T.FG, width=420, alpha=la)
        Wg.source_line(ctx, self.F.source("mine"), (96, rr.bottom + 6), alpha=la)

        # Drone link (plan).
        ra = progress(t, 2.6, 0.5)
        rx = PC.right + 30
        ctx.text(self.txt("drone_link"), (rx, 196), T.SMALL, T.DRONE, bold=True, alpha=ra)
        py = 236
        for line in self.txt("drone_ports"):
            pr = ctx.text(line, (rx, py), T.SMALL, T.FG, alpha=ra)
            py = pr.bottom + 6
        Wg.status_tag(ctx, "plan", (rx, pr.bottom + 14), alpha=ra)
        D.drone_side(s, (1690, link_y - 6), 170, T.DRONE, ra, t)
        D.dashed(s, T.fade(T.HOME, ra), [(PC.right, link_y), (1590, link_y)], 4, 14, 9)
        Wg.source_line(ctx, self.F.source("tello"), (rx, link_y + 84), alpha=ra)

        # Packets, slowed for display (no rates are claimed for the drone link).
        if la > 0.9:
            for k in range(3):
                f = ((t * 1.0) + k / 3) % 1.0
                x = lerp(PC.left, 370, f)
                D.disc(s, T.HOME, (x, link_y), 6)
        if ra > 0.9:
            for k in range(2):
                f = ((t * 0.8) + k / 2) % 1.0
                D.disc(s, T.HOME, (lerp(PC.right, 1585, f), link_y - 12), 6)
                D.disc(s, T.DRONE, (lerp(1585, PC.right, f), link_y + 12), 5)
        if ra > 0.9:
            ctx.text(self.txt("packets"), (T.W - T.MARGIN, link_y + 130), T.TINY, T.DIM, "topright", alpha=ra)

        # No router.
        na = progress(t, 3.0, 0.5)
        rt = ctx.text(self.txt("router"), (PC.left, PC.bottom + 34), T.SMALL, T.FG, "midleft", alpha=na)
        Wg.status_tag(ctx, "plan", (rt.right + 18, rt.centery), "midleft", alpha=na)
        ctx.text(self.txt("router_verify"), (PC.left, rt.bottom + 8), T.TINY, T.DIM, alpha=na)

        Wg.source_line(ctx, self.txt("source"), (T.W - T.MARGIN, T.SOURCE_Y), "topright", alpha=na)

        # Legend: line style carries built vs plan, not color alone.
        ga = progress(t, 3.2, 0.5)
        Wg.legend(ctx, (96, 690), [(self.txt("legend_built"), T.HOME, "box"), (self.txt("legend_plan"), T.HOME, "dashed")],
                  alpha=ga, size=T.TINY, row=36)


# ====================================================================== 4.3
MAP_X0, MAP_Y1, MPX = 96, 834, 36.0
LOG_X = 1284
LOG_W = T.W - T.MARGIN - LOG_X
PHASE_DUR = (2.4, 6.0, 1.4, 4.0, 3.2, 5.0, 1.2)


def mx(x):
    return MAP_X0 + x * MPX


def my(y):
    return MAP_Y1 - y * MPX


def mp(p):
    return (mx(p[0]), my(p[1]))


class MissionBeat(Beat):
    key = "4.3"
    steps = 7
    step_durations = PHASE_DUR

    def __init__(self, facts):
        super().__init__(facts)
        self.mission = Mission(facts.mission)
        self.m = facts.mission["map"]
        self.reserve = float(facts.mission["reserve_pct"])

    def mission_time(self):
        k = self.step
        a, b = self.mission.phases[k]
        f = ease(self.lt(k) / PHASE_DUR[k]) if PHASE_DUR[k] > 0 else 1.0
        return lerp(a, b, f)

    def chrome(self, ctx, captions_alpha=None):
        Wg.header(ctx, self.txt.get("kicker"), self.txt("title"))
        Wg.captions(ctx, [self.txt("phase_captions")[self.step]])

    # ------------------------------------------------------------ map
    def _map(self, ctx, t, tm):
        s = ctx.surf
        W, H = self.m["size"]
        frame = pygame.Rect(MAP_X0, int(my(H)), int(W * MPX), int(H * MPX))
        self.frame = frame
        D.rrect(s, T.mix(T.BG, T.PANEL, 0.5), frame, 10)
        ctx.mark(frame, "ui", "map")
        fence = [mp(p) for p in self.F.mission["geofence"]]
        D.poly(s, T.PANEL, fence)
        # floor grid (1 m)
        old = s.get_clip()
        s.set_clip(frame)
        for x in range(int(W) + 1):
            pygame.draw.line(s, T.mix(T.PANEL, T.GRID, 0.6), (mx(x), frame.top), (mx(x), frame.bottom), 1)
        for y in range(int(H) + 1):
            pygame.draw.line(s, T.mix(T.PANEL, T.GRID, 0.6), (frame.left, my(y)), (frame.right, my(y)), 1)
        s.set_clip(old)
        D.poly(s, T.mix(T.BG, T.PANEL, 0.5), [mp(p) for p in [(0, 7.5), (18, 7.5), (18, 18), (0, 18)]])
        D.poly(s, T.mix(T.BG, T.PANEL, 0.5), [mp(p) for p in [(8, 6.5), (18, 6.5), (18, 7.5), (8, 7.5)]])
        D.poly(s, T.mix(T.BG, T.PANEL, 0.5), [mp(p) for p in [(8, 0), (18, 0), (18, 2), (8, 2)]])
        D.dashed(s, T.mix(T.BG, T.WARN, 0.75), fence + [fence[0]], 2, 10, 7)
        ctx.text(self.txt("geofence"), (mx(31.8), my(17.6)), T.TINY, T.mix(T.BG, T.WARN, 0.85), "topright")
        ctx.text(self.txt("home"), (mx(0.4), my(7.1)), T.TINY, T.DIM)
        ctx.text(self.txt("hallway"), (mx(8.4), my(6.1)), T.TINY, T.DIM)
        ctx.text(self.txt("atrium"), (mx(18.4), my(17.6)), T.TINY, T.DIM)

        # Overhead camera coverage (built), and the props.
        x0, y0, x1, y1 = self.m["camera_square"]
        sq = pygame.Rect(int(mx(x0)), int(my(y1)), int((x1 - x0) * MPX), int((y1 - y0) * MPX))
        D.dashed_rect(s, T.NEUTRAL, sq, 2, 12, 8)
        D.camera_icon(s, (sq.left + 22, sq.bottom + 28), 20, T.NEUTRAL)
        ctx.text(self.txt("camera_square"), (sq.left + 44, sq.bottom + 28), T.TINY, T.NEUTRAL, "midleft")
        hp = self.m["home_pad"]
        pad = pygame.Rect(int(mx(hp[0])), int(my(hp[3])), int((hp[2] - hp[0]) * MPX), int((hp[3] - hp[1]) * MPX))
        D.rrect(s, T.mix(T.BG, T.HOME, 0.18), pad, 10)
        D.rrect(s, T.HOME, pad, 10, 2)
        for o in self.m["objects"]:
            if o["kind"] == "chair":
                D.chair_top(s, mp(o["pos"]), 0.7 * MPX, tuple(o["color"]), 1.0, o["heading"])
            else:
                w, h = o["size"]
                D.table_top(s, pygame.Rect(int(mx(o["pos"][0] - w / 2)), int(my(o["pos"][1] + h / 2)),
                                           int(w * MPX), int(h * MPX)))

    def _paths(self, s, tm):
        M = self.mission
        # Drone: planned scan faint, flown part bright, return leg in home color.
        if self.step >= 1:
            D.dashed(s, T.mix(T.BG, T.DRONE, 0.28), [mp(p) for p in M.scan_path.pts], 2, 8, 8)
            flown = min(tm, M.t_find)
            if flown > 0.3:
                L = (flown - 0.3) * 9.0
                pts = [mp(M.scan_path.at(d)[0]) for d in [L * k / 60 for k in range(61)]]
                D.dashed(s, T.DRONE, pts, 3, 12, 8)
        if tm > M.t_ret:
            L = min(tm, M.t_land) - M.t_ret
            pts = [mp(M.ret_path.at(L * 30.0 * k / 40)[0]) for k in range(41)]
            D.dashed(s, T.HOME, pts, 3, 12, 8)
        # Dog: outbound solid in dog color, return in home color.
        if tm > M.t_dog_start:
            L = min(tm, M.t_dog_arrive) - M.t_dog_start
            pts = [mp(M.dog_out.at(L * 10.0 * k / 60)[0]) for k in range(61)]
            D.polyline(s, T.DOG, pts, 4)
        if tm > M.t_dog_arrive + 0.3:
            L = min(tm, M.t_dog_home) - (M.t_dog_arrive + 0.3)
            pts = [mp(M.dog_back.at(L * 10.0 * k / 60)[0]) for k in range(61)]
            D.polyline(s, T.HOME, pts, 4)

    def _robots(self, ctx, t, tm):
        s = ctx.surf
        M = self.mission
        dp, dh, air = M.drone(tm)
        if air:
            old = s.get_clip()
            s.set_clip(self.frame)
            cone = [mp(dp)]
            for k in range(9):
                a = dh - CAMERA_HALF_ANGLE + 2 * CAMERA_HALF_ANGLE * k / 8
                cone.append(mp((dp[0] + CAMERA_RANGE * math.cos(a), dp[1] + CAMERA_RANGE * math.sin(a))))
            D.poly_alpha(s, T.DRONE, cone, 60)
            D.polyline(s, T.mix(T.BG, T.DRONE, 0.7), cone, 2, closed=True)
            s.set_clip(old)
        gp, gh, walking = M.dog(tm)
        D.dog_top(s, mp(gp), -gh, 34, T.DOG, 1.0, t * 8 if walking else 0.0)
        D.drone_top(s, mp(dp), -dh, 34 if air else 28, T.DRONE, 1.0, t if air else 0.0)
        if tm >= M.t_find:
            fa = progress(self.lt(2) if self.step >= 2 else 0, 0.0, 0.5) if self.step == 2 else 1.0
            cp = mp(M.chair_pos)
            D.pin(s, (cp[0], cp[1] - 10), 32, T.OBJ_RED, fa)
            ctx.text(self.txt("found"), (cp[0] - 30, cp[1] - 58), T.SMALL, T.DRONE, "midright", alpha=fa)
        return gp

    # ------------------------------------------------------------ log, battery, clock
    def _log(self, ctx, t, tm):
        s = ctx.surf
        M = self.mission
        ctx.text(self.txt("log"), (LOG_X, 186), T.LABEL, T.FG, bold=True)
        y = 232
        for k, entry in enumerate(M.log):
            a = progress(self.lt(0), 0.2 + 0.25 * k, 0.4)
            issued = self.step >= 1 and (tm > entry.t or (entry.t == 0.0 and tm > 0.0))
            lines = wrap_call(format_call(entry.call), LOG_W - 40, T.CODE)
            col = T.TOOL if issued else T.FAINT
            for j, ln in enumerate(lines):
                Wg.code_line(ctx, ln, (LOG_X + 40, y + j * 34), col, alpha=a)
            if issued:
                D.check_mark(s, (LOG_X + 14, y + 16), 22, T.TOOL if entry.accepted else T.WARN)
            else:
                D.ring(s, T.fade(T.FAINT, a), (LOG_X + 14, y + 16), 8, 2)
            y += 34 * len(lines) + 6
        if self.step == 6:
            y += 6
            ctx.text(self.txt("rejected"), (LOG_X, y), T.TINY, T.FAINT, bold=True)
            y += 30
            for bad in self.F.mission["bad_calls"]:
                lines = wrap_call(format_call(bad), LOG_W - 40, T.CODE)
                for j, ln in enumerate(lines):
                    Wg.code_line(ctx, ln, (LOG_X + 40, y + j * 34), T.FAINT)
                D.cross_mark(s, (LOG_X + 14, y + 16), 20, T.FAINT)
                y += 34 * len(lines) + 4
        return y

    def _battery(self, ctx, tm):
        s = ctx.surf
        M = self.mission
        b = M.battery(tm)
        y = 718
        ctx.text(self.txt("battery"), (LOG_X, y - 30), T.TINY, T.DRONE)
        bar = pygame.Rect(LOG_X, y, LOG_W - 90, 28)
        D.rrect(s, T.GRID, bar, 8)
        col = T.WARN if b < self.reserve else T.DRONE
        fill = pygame.Rect(bar.left, bar.top, int(bar.width * b / 100), bar.height)
        if fill.width > 0:
            D.rrect(s, col, fill, 8)
        for m in range(int(FLIGHT_MINUTES) + 1):
            x = bar.left + bar.width * m / FLIGHT_MINUTES
            pygame.draw.line(s, T.DIM, (x, bar.bottom + 3), (x, bar.bottom + 9), 1)
        rx = bar.left + bar.width * self.reserve / 100
        D.line(s, T.WARN, (rx, bar.top - 8), (rx, bar.bottom + 8), 3)
        ctx.mark(bar, "ui", "battery")
        ctx.text(f"{b:.0f}%", (bar.right + 14, bar.centery), T.LABEL, col, "midleft", bold=True)
        Wg.tag(ctx, self.txt("reserve"), (LOG_X, bar.bottom + 20), T.WARN, icon="warn")
        mins = int(tm)
        secs = int(round((tm - mins) * 60))
        if secs == 60:
            mins, secs = mins + 1, 0
        r = ctx.text(f"{self.txt('clock')}  {mins}:{secs:02d}", (LOG_X, bar.bottom + 76), T.SMALL, T.FG)
        Wg.status_tag(ctx, "illus", (r.right + 16, r.centery), "midleft", text=self.txt("compressed"))

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf
        tm = self.mission_time()
        self._map(ctx, t, tm)
        self._paths(s, tm)
        gp = self._robots(ctx, t, tm)

        # Overlay in the empty corner of the map: honesty tag and legend.
        Wg.status_tag(ctx, "illus", (MAP_X0 + 16, 198), text=self.txt("illus"))
        Wg.legend(ctx, (MAP_X0 + 16, 246), [("drone path", T.DRONE, "dashed"), ("dog path", T.DOG, "solid"),
                                             ("return home", T.HOME, "dashed"), ("drone camera view", T.DRONE, "box")],
                  size=T.TINY, row=34)
        if 3 <= self.step <= 4:
            a = self.p(3, 0.6, 0.5) if self.step == 3 else 1.0
            tx, ty = MAP_X0 + 340, 250
            tg = Wg.status_tag(ctx, "plan", (tx, ty), alpha=a)
            tb = ctx.text_block(self.txt("dog_tag"), (tx, tg.bottom + 10), T.SMALL, T.FG, width=300, alpha=a)
            dpx = mp(gp)
            D.dotted(s, T.fade(T.DOG, 0.7 * a), [(tb.centerx, tb.bottom + 8), (dpx[0], dpx[1] - 22)], 2.2, 10)

        self._log(ctx, t, tm)
        Wg.source_line(ctx, self.txt("source"))
        if self.step >= 1:
            self._battery(ctx, tm)
        if self.step == 0:
            self._sentence_overlay(ctx)

    def _sentence_overlay(self, ctx):
        """Phase 1: the sentence appears over the map; its calls fill the log."""
        a = progress(self.lt(0), 0.0, 0.5)
        box = pygame.Rect(0, 0, 900, 140)
        box.center = (self.frame.centerx, self.frame.top + 300)
        D.rrect(ctx.surf, T.fade(T.PANEL, a), box, 18)
        D.rrect(ctx.surf, T.fade(T.LANG, a), box, 18, 3)
        ctx.mark(box, "ui", "sentence")
        ctx.text_block(self.F.mission["sentence"], (box.left + 32, box.centery), T.LABEL + 2, T.FG, width=box.width - 64,
                       anchor="midleft", alpha=a)
        D.arrow(ctx.surf, T.fade(T.LANG, a), (box.right + 6, box.centery), (LOG_X - 14, 300), 3, 14)


def make(F):
    a = Act([WhyDrone(F), HomePoint(F), MissionBeat(F)])
    a.number = 4
    return a
