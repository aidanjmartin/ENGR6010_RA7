"""Act 3: from words to things. Tool calls checked live, then words grounded in pixels."""
from __future__ import annotations

import json

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core import widgets as Wg
from core.anim import lerp_pt, progress, pulse
from core.facts import SCHEMA_PATH
from core.theme import fonts
from sim.mission import Mission
from team.checker import Checker, format_call, format_json, initial_state

def wrap_call(text: str, max_px: int, size: int = T.CODE):
    """Greedy wrap of a call, breaking only after "(" or ", ", continuation indented."""
    F = fonts()
    if F.width(text, size, mono=True) <= max_px:
        return [text]
    pieces, cur = [], ""
    i = 0
    while i < len(text):
        cur += text[i]
        if text[i] == "(" or text[i:i + 2] == ", ":
            if text[i] == ",":
                cur += " "
                i += 1
            pieces.append(cur)
            cur = ""
        i += 1
    if cur:
        pieces.append(cur)
    lines, line = [], ""
    for p in pieces:
        trial = line + p
        lead = "" if not lines else "  "
        if line and F.width((lead + trial).rstrip(), size, mono=True) > max_px:
            lines.append(line.rstrip())
            line = p
        else:
            line = trial
    if line:
        lines.append(line.rstrip())
    return [lines[0]] + ["  " + l for l in lines[1:]]


# ====================================================================== 3.1
LX, LW = 96, 650
MX = 786
RX, RW = 1340, 484
CALLS_Y = 432
LINE = 36
CALL_GAP = 6
TYPE_START, TYPE_EACH = 1.0, 0.55


class ToolCalls(Beat):
    key = "3.1"
    steps = 4
    step_durations = (5.2, 1.4, 1.4, 1.4)

    def __init__(self, facts):
        super().__init__(facts)
        self.checker = Checker()
        self.mission = Mission(facts.mission, self.checker)
        self.calls = facts.mission["calls"]
        self.bad = facts.mission["bad_calls"]
        s0 = initial_state(facts.mission)
        # Good calls are checked in the world state at the moment they are issued.
        self.good_verdicts = [self.checker.check(c, self.mission.issue_state(c["tool"])) for c in self.calls]
        self.bad_states = [s0.with_(**c.get("state", {})) for c in self.bad]
        self.bad_verdicts = [self.checker.check(c, st) for c, st in zip(self.bad, self.bad_states)]
        with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
            sc = json.load(fh)["tools"]["drone.scout"]
        enum = json.dumps(sc["properties"]["area"]["enum"])
        self.schema_lines = ['"drone.scout": {', '  "area": {"enum":', f"    {enum}}},",
                             f'  "required": {json.dumps(sc["required"])}}}']

    def _verdict(self, ctx, y, ok, reason, a):
        if a <= 0:
            return
        col = T.TOOL if ok else T.WARN
        if ok:
            D.check_mark(ctx.surf, (MX + 14, y + 17), 24, T.fade(col, a))
        else:
            D.cross_mark(ctx.surf, (MX + 14, y + 17), 24, T.fade(col, a))
        ctx.text(reason, (MX + 44, y + 17), T.SMALL, col if not ok else T.FG, "midleft", alpha=a)

    def draw(self, ctx):
        self.chrome(ctx)
        t0 = self.lt(0)
        s = ctx.surf

        # Sentence -> LLM -> calls.
        sa = progress(t0, 0.1, 0.5)
        box = pygame.Rect(LX, 186, LW, 108)
        D.rrect(s, T.fade(T.PANEL, sa), box, 14)
        D.rrect(s, T.fade(T.LANG, sa), box, 14, 2)
        ctx.text_block(self.F.mission["sentence"], (box.left + 22, box.top + 16), T.LABEL - 2, T.FG,
                       width=box.width - 44, alpha=sa)
        la = progress(t0, 0.4, 0.5)
        D.arrow(s, T.fade(T.LANG, la), (LX + 80, box.bottom + 4), (LX + 80, 330), 3, 12)
        llm = pygame.Rect(LX + 20, 332, 120, 50)
        D.rrect(s, T.fade(T.mix(T.BG, T.LANG, 0.25), la), llm, 12)
        D.rrect(s, T.fade(T.LANG, la), llm, 12, 3)
        ctx.text(self.txt("llm"), llm.center, T.LABEL, T.FG, "center", bold=True, alpha=la, record=False)
        ctx.mark(llm, "text", "LLM")
        Wg.status_tag(ctx, "canned", (llm.right + 22, llm.centery), "midleft", alpha=la)
        D.arrow(s, T.fade(T.TOOL, la), (LX + 80, llm.bottom + 2), (LX + 80, CALLS_Y - 8), 3, 12)
        ctx.text(self.txt("calls"), (LX + 104, CALLS_Y - 22), T.TINY, T.TOOL, "midleft", alpha=la)

        # Checker column header and its honesty tags.
        ha = progress(t0, 0.6, 0.5)
        ctx.text(self.txt("checker"), (MX, 186), T.LABEL + 4, T.FG, bold=True, alpha=ha)
        Wg.tag(ctx, self.txt("checker_real"), (MX, 236), T.NEUTRAL, alpha=ha)
        Wg.status_tag(ctx, "plan", (MX, 282), alpha=ha, text=self.txt("robot_plan"))

        y = CALLS_Y
        maxw = LW - 10
        for k, (call, (ok, why)) in enumerate(zip(self.calls, self.good_verdicts)):
            lines = wrap_call(format_call(call), maxw)
            start = TYPE_START + TYPE_EACH * k
            total = sum(len(l) for l in lines)
            typed = max(0.0, (t0 - start) * 70)
            for j, ln in enumerate(lines):
                before = sum(len(l) for l in lines[:j])
                if typed > before:
                    Wg.code_line(ctx, ln, (LX, y + j * LINE), T.TOOL, chars=typed - before)
            done = typed >= total
            self._verdict(ctx, y, ok, why, progress(t0, start + total / 70 + 0.1, 0.35) if done else 0.0)
            y += LINE * len(lines) + CALL_GAP

        # Bad calls slide in one per step and are refused.
        if self.step >= 1:
            ba = self.p(1, 0.0, 0.4)
            y += 8
            ctx.text(self.txt("bad"), (LX, y), T.TINY, T.WARN, bold=True, alpha=ba)
            y += 30
            for i in range(3):
                st = i + 1
                if self.step < st:
                    break
                p = self.p(st, 0.0, 0.5)
                lines = wrap_call(format_call(self.bad[i]), maxw)
                x = LX - 60 * (1 - p)
                r = Wg.code_line(ctx, lines[0], (x, y), T.WARN, alpha=p)
                if "state" in self.bad[i]:
                    ctx.text(self.txt("at_battery", battery=int(self.bad[i]["state"]["battery"])),
                             (r.right + 14, r.centery), T.TINY, T.WARN, "midleft", alpha=p)
                ok, why = self.bad_verdicts[i]
                self._verdict(ctx, y, ok, why, self.p(st, 0.45, 0.35))
                y += LINE + 4

        # Right column: the schema the checker uses, one call as JSON, and the readings.
        ra = progress(t0, 0.8, 0.5)
        card = pygame.Rect(RX, 186, RW, 196)
        D.panel(s, card, radius=14)
        ctx.mark(card, "ui", "schema card")
        ctx.text(self.txt("schema_title"), (card.left + 20, card.top + 14), T.TINY, T.TOOL, bold=True, alpha=ra)
        for i, ln in enumerate(self.schema_lines):
            Wg.code_line(ctx, ln, (card.left + 20, card.top + 50 + i * 34), T.NEUTRAL, alpha=ra)
        jcard = pygame.Rect(RX, 398, RW, 128)
        D.panel(s, jcard, radius=14)
        ctx.mark(jcard, "ui", "json card")
        ctx.text(self.txt("json_title"), (jcard.left + 20, jcard.top + 14), T.TINY, T.TOOL, bold=True, alpha=ra)
        for i, ln in enumerate(format_json(self.calls[1])):
            Wg.code_line(ctx, ln, (jcard.left + 20, jcard.top + 48 + i * 34), T.TOOL, alpha=ra)
        na = progress(t0, 1.2, 0.5)
        r = ctx.text_block(self.txt("gorilla"), (RX, 556), T.SMALL, T.FG, width=RW, alpha=na)
        Wg.source_line(ctx, self.F.source("gorilla"), (RX, r.bottom + 8), alpha=na)
        r = ctx.text_block(self.txt("vllm"), (RX, r.bottom + 50), T.SMALL, T.FG, width=RW, alpha=na)
        Wg.source_line(ctx, self.F.source("vllm_docs"), (RX, r.bottom + 8), alpha=na)


# ====================================================================== 3.2
PANEL = pygame.Rect(96, 190, 820, 556)
CX = 1010
BAR_X, BAR_W = 1370, 290
ROW0, ROWDY = 304, 76


def crop_art(surf, kind, rect, a):
    """Small original drawings standing in for detector image crops."""
    r = pygame.Rect(rect)
    D.rrect(surf, T.fade(T.mix(T.BG, T.NEUTRAL, 0.08), a), r, 10)
    D.rrect(surf, T.fade(T.NEUTRAL, a * 0.7), r, 10, 2)
    cx, cy = r.center
    if kind in ("red chair", "blue chair"):
        col = T.OBJ_RED if kind == "red chair" else (80, 120, 220)
        c = T.fade(col, a)
        D.line(surf, c, (cx - 18, cy - 28), (cx - 18, cy + 4), 7)
        D.line(surf, c, (cx - 20, cy + 4), (cx + 22, cy + 4), 7)
        D.line(surf, c, (cx - 16, cy + 4), (cx - 16, cy + 30), 5)
        D.line(surf, c, (cx + 18, cy + 4), (cx + 18, cy + 30), 5)
    elif kind == "table":
        c = T.fade((150, 126, 96), a)
        D.line(surf, c, (cx - 32, cy - 6), (cx + 32, cy - 6), 8)
        D.line(surf, c, (cx - 24, cy - 6), (cx - 24, cy + 28), 5)
        D.line(surf, c, (cx + 24, cy - 6), (cx + 24, cy + 28), 5)
    else:
        c = T.fade((150, 156, 170), a)
        body = pygame.Rect(cx - 16, cy - 26, 32, 54)
        D.rrect(surf, c, body, 4)
        pygame.draw.ellipse(surf, T.fade(T.mix((150, 156, 170), T.FG, 0.3), a), pygame.Rect(cx - 16, cy - 33, 32, 14))


class Words(Beat):
    key = "3.2"
    step_durations = (3.5,)

    def _pill(self, ctx, text, center, a, hl=0.0):
        F = fonts()
        w = F.width(text, T.SMALL) + 36
        r = pygame.Rect(0, 0, w, 40)
        r.center = (int(center[0]), int(center[1]))
        D.rrect(ctx.surf, T.fade(T.mix(T.BG, T.LANG, 0.2 + 0.2 * hl), a), r, 20)
        D.rrect(ctx.surf, T.fade(T.LANG, a), r, 20, 2)
        ctx.text(text, r.center, T.SMALL, T.FG, "center", alpha=a, record=False)
        ctx.mark(r, "text", text)
        return r

    def draw(self, ctx):
        self.chrome(ctx)
        t = self.t
        s = ctx.surf

        # Left: a drawn shared embedding space.
        pa = progress(t, 0.1, 0.5)
        D.panel(s, PANEL, radius=18)
        ctx.mark(PANEL, "ui", "embedding panel")
        for k in range(1, 6):
            x = PANEL.left + PANEL.width * k / 6
            pygame.draw.line(s, T.fade(T.GRID, pa), (x, PANEL.top + 60), (x, PANEL.bottom - 16), 1)
        for k in range(1, 5):
            y = PANEL.top + 50 + (PANEL.height - 60) * k / 5
            pygame.draw.line(s, T.fade(T.GRID, pa), (PANEL.left + 16, y), (PANEL.right - 16, y), 1)
        ctx.text(self.txt("space"), (PANEL.left + 24, PANEL.top + 18), T.SMALL, T.DIM, bold=True, alpha=pa)

        crops = self.txt("crops")
        crop_pos = {crops[0]: (300, 372), crops[1]: (540, 430), crops[2]: (770, 640), crops[3]: (270, 650)}
        for k, name in enumerate(crops):
            a = progress(t, 0.3 + 0.12 * k, 0.5)
            c = crop_pos[name]
            rr = pygame.Rect(0, 0, 100, 100)
            rr.center = c
            crop_art(s, ["red chair", "blue chair", "table", "cylinder"][k], rr, a)
            ctx.mark(rr, "ui", name)
        phrases = self.txt("phrases")
        pill_pos = {phrases[0]: (460, 268), phrases[1]: (430, 520), phrases[2]: (770, 300)}
        snap = progress(t, 1.3, 0.8)
        a0 = progress(t, 0.8, 0.5)
        if snap > 0:
            p0 = pill_pos[phrases[0]]
            p1 = (crop_pos[crops[0]][0] + 30, crop_pos[crops[0]][1] - 30)
            D.line(s, T.fade(T.LANG, snap), p0, lerp_pt(p0, p1, snap), 4)
            if snap >= 1:
                D.ring(s, T.fade(T.LANG, 0.4 + 0.5 * pulse(t)), crop_pos[crops[0]], 66, 3)
        for k, ph in enumerate(phrases):
            self._pill(ctx, ph, pill_pos[ph], progress(t, 0.8 + 0.15 * k, 0.5), hl=snap if k == 0 else 0.0)
        Wg.status_tag(ctx, "illus", (PANEL.left, PANEL.bottom + 16), alpha=pa, text=self.txt("illus"))
        Wg.source_line(ctx, self.txt("clip") + "  " + self.F.source("clip"), alpha=pa)

        # Right: measured grounding, by phrase.
        ca = progress(t, 0.5, 0.5)
        ctx.text(self.txt("chart_title"), (CX, 196), T.LABEL, T.FG, bold=True, alpha=ca)
        tg = Wg.status_tag(ctx, "built", (CX, 240), alpha=ca)
        ctx.text(self.F.source("mine"), (tg.right + 14, tg.centery), T.TINY, T.DIM, "midleft", alpha=ca)
        rows = self.F.value("grounding_eval")
        notes = {3: self.txt("note_nocolor"), 4: self.txt("note_person")}
        for k, row in enumerate(rows):
            a = progress(t, 0.7 + 0.12 * k, 0.5)
            y = ROW0 + k * ROWDY
            zero = row["success"] == 0
            col = T.WARN if zero else T.TOOL
            ctx.text(row["prompt"], (CX, y), T.SMALL, T.FG, "midleft", alpha=a)
            if k in notes:
                D.warning_triangle(s, (CX + 10, y + 30), 18, T.fade(T.WARN, a))
                ctx.text(notes[k], (CX + 26, y + 30), T.TINY, T.WARN, "midleft", alpha=a)
            Wg.hbar(ctx, (BAR_X, y - 13, BAR_W, 26), max(row["success"], 0.012) * a, col, a)
            ctx.text(f"{row['success']:.3f} · n = {row['n']}", (BAR_X + BAR_W + 14, y), T.SMALL,
                     T.WARN if zero else T.FG, "midleft", alpha=a)
        ra = progress(t, 1.6, 0.5)
        y = ROW0 + 5 * ROWDY + 4
        Wg.status_tag(ctx, "built", (CX, y), alpha=ra)
        ctx.text_block(self.txt("real"), (CX, y + 46), T.SMALL, T.FG, width=T.W - T.MARGIN - CX, alpha=ra)
        r = ctx.text(self.txt("homerobot"), (CX, y + 110), T.SMALL, T.FG, alpha=ra)
        Wg.source_line(ctx, self.F.source("homerobot"), (CX, r.bottom + 6), alpha=ra)


def make(F):
    a = Act([ToolCalls(F), Words(F)])
    a.number = 3
    return a
