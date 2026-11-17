"""Act 0: title. The sentence is typed at the home PC; two robots wait on the pad."""
from __future__ import annotations

import math

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core.anim import progress
from core.theme import fonts

TYPE_RATE = 34.0        # characters per second


class TitleBeat(Beat):
    key = "0.1"
    step_durations = (6.0,)

    def draw(self, ctx):
        t = self.t
        s = ctx.surf
        sentence = self.F.mission["sentence"]

        # Faint mission paths fanning out from the pad and back.
        pa = progress(t, 0.9, 1.6)
        pad_c = (1190, 838)
        targets = [(520, 300, T.DRONE), (760, 330, T.DOG), (1010, 300, T.DRONE), (1310, 320, T.DOG),
                   (1560, 300, T.DRONE)]
        for k, (tx, ty, col) in enumerate(targets):
            q = progress(t, 0.9 + 0.12 * k, 1.4)
            if q <= 0:
                continue
            out, back = [], []
            for i in range(41):
                u = i / 40
                bx = pad_c[0] + (tx - pad_c[0]) * u
                by = pad_c[1] + (ty - pad_c[1]) * math.sin(u * math.pi / 2)
                out.append((bx - 26 * math.sin(u * math.pi), by))
                back.append((bx + 26 * math.sin(u * math.pi), by))
            n = max(2, int(41 * q))
            D.dashed(s, T.fade(col, 0.32 * pa), out[:n], 2, 10, 9)
            D.dashed(s, T.fade(T.HOME, 0.26 * pa), back[:n], 2, 10, 9)

        # Title and subtitle.
        ctx.text(self.txt("title"), (T.W // 2, 132), T.COVER_TITLE, T.FG, "midtop", bold=True,
                 alpha=progress(t, 0.1, 0.7))
        ctx.text(self.txt("subtitle"), (T.W // 2, 226), T.BODY, T.DIM, "midtop", alpha=progress(t, 0.5, 0.7))

        # The sentence, typed into a box above the PC.
        ba = progress(t, 0.6, 0.6)
        box = pygame.Rect(0, 0, 1260, 150)
        box.center = (T.W // 2, 560)
        D.rrect(s, T.fade(T.PANEL, ba), box, 18)
        D.rrect(s, T.fade(T.LANG, ba * 0.9), box, 18, 3)
        ctx.text(self.txt("typed_label"), (box.left + 28, box.top - 12), T.TINY, T.LANG, "bottomleft", alpha=ba)
        chars = max(0, int((t - 1.2) * TYPE_RATE))
        F = fonts()
        lines = F.wrap(sentence, T.BODY + 2, box.width - 80)
        left = chars
        y = box.top + 30
        for ln in lines:
            shown = ln[:max(0, left)]
            left -= len(ln) + 1
            if shown:
                ctx.text(shown, (box.left + 40, y), T.BODY + 2, T.FG, "topleft", alpha=ba, record=False)
            y += int((T.BODY + 2) * 1.35)
        if ba > 0:
            ctx.mark(box, "text", "sentence box")
        typing = chars < len(sentence)
        if ba > 0.5 and (typing or int(t * 2) % 2 == 0):
            # cursor after the last typed character
            done = sentence[:chars]
            k, acc = 0, 0
            for k, ln in enumerate(lines):
                if acc + len(ln) >= len(done):
                    break
                acc += len(ln) + 1
            part = done[acc:]
            cx = box.left + 40 + (F.width(part, T.BODY + 2) if part else 0) + 4
            cy = box.top + 30 + k * int((T.BODY + 2) * 1.35)
            pygame.draw.rect(s, T.LANG, pygame.Rect(int(cx), int(cy + 4), 3, T.BODY))

        # Home PC at the bottom centre, the pad and robots beside it.
        ra = progress(t, 0.3, 0.7)
        pc = D.pc_tower(s, (860, 860), 170, T.HOME, ra)
        ctx.mark(pc, "ui", "pc")
        ctx.text(self.txt("pc"), (pc.centerx, pc.bottom + 14), T.SMALL, T.HOME, "midtop", alpha=ra)
        D.line(s, T.fade(T.HOME, 0.6 * ra), (pc.right + 6, 840), (1030, 840), 3)
        pad = pygame.Rect(1030, 846, 330, 14)
        D.rrect(s, T.fade(T.mix(T.HOME, T.BG, 0.55), ra), pad, 7)
        ctx.text(self.txt("pad"), (pad.centerx, pad.bottom + 14), T.SMALL, T.DIM, "midtop", alpha=ra)
        rob = progress(t, 0.6, 0.7)
        D.draw_dog(s, D.dog_pose(D.STAND), 1120, pad.top, 0.42, T.NEUTRAL, T.DOG, rob)
        D.drone_side(s, (1286, pad.top - 14), 120, T.DRONE, rob, t * 0.0)

        ctx.text(self.txt("footer"), (T.W // 2, 1002), T.SMALL, T.DIM, "midbottom", alpha=progress(t, 1.6, 0.8))


def make(F):
    a = Act([TitleBeat(F)])
    a.number = 0
    return a
