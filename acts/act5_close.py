"""Act 5: three takeaways, then what is built and what is next."""
from __future__ import annotations

import pygame

from acts.base import Act, Beat
from core import draw as D
from core import theme as T
from core import widgets as Wg
from core.anim import progress

ROW_Y = (214, 350, 486)
ICON = 104
TEXT_X = 96 + ICON + 44


def icon_ladder(s, r, a):
    x = r.centerx
    D.line(s, T.fade(T.DIM, a), (x, r.top + 22), (x, r.bottom - 14), 3)
    D.rrect(s, T.fade(T.LANG, a), pygame.Rect(x - 9, r.top + 12, 18, 18), 4)
    for k, y in enumerate((r.top + 52, r.top + 70, r.top + 86)):
        D.disc(s, T.fade(T.DOG, a), (x, y), 7 - k)


def icon_check(s, r, a):
    pill = pygame.Rect(r.left + 14, r.centery - 16, r.width - 28, 32)
    D.rrect(s, T.fade(T.mix(T.BG, T.TOOL, 0.2), a), pill, 10)
    D.rrect(s, T.fade(T.TOOL, a), pill, 10, 2)
    D.check_mark(s, (pill.right - 20, pill.centery), 20, T.fade(T.TOOL, a))
    for k in range(3):
        D.line(s, T.fade(T.TOOL, a), (pill.left + 12 + k * 14, pill.centery), (pill.left + 20 + k * 14, pill.centery), 3)


def icon_ground(s, r, a):
    p0 = (r.left + 30, r.top + 36)
    p1 = (r.right - 30, r.bottom - 34)
    D.line(s, T.fade(T.LANG, a), p0, p1, 3)
    D.disc(s, T.fade(T.LANG, a), p0, 9)
    box = pygame.Rect(0, 0, 28, 28)
    box.center = p1
    D.rrect(s, T.fade(T.OBJ_RED, a), box, 6)


ICONS = (icon_ladder, icon_check, icon_ground)
COLORS = (T.LANG, T.TOOL, T.LANG)


class Close(Beat):
    key = "5.1"
    steps = 4
    step_durations = (1.2, 1.0, 1.0, 1.4)

    def draw(self, ctx):
        Wg.header(ctx, self.txt("kicker"), self.txt("title"))
        s = ctx.surf
        for k, text in enumerate(self.txt("takeaways")):
            if self.step < k:
                break
            a = self.p(k, 0.05, 0.5)
            y = ROW_Y[k]
            r = pygame.Rect(96 + int(30 * (1 - a)), y, ICON, ICON)
            D.panel(s, r, T.fade(T.PANEL, a), T.fade(T.PANEL_EDGE, a), 16)
            ICONS[k](s, r, a)
            ctx.mark(r, "ui", "icon")
            D.rrect(s, T.fade(COLORS[k], a), pygame.Rect(TEXT_X - 22, y + 12, 5, ICON - 24), 2)
            ctx.text_block(f"{k + 1}.  {text}", (TEXT_X, y + ICON / 2), T.BODY, T.FG, width=T.W - T.MARGIN - TEXT_X,
                           anchor="midleft", alpha=a)

        if self.step >= 3:
            a = self.p(3, 0.0, 0.6)
            top = 640
            left = pygame.Rect(96, top, 840, 190)
            right = pygame.Rect(T.W - 96 - 840, top, 840, 190)
            for rect, kind, head, body in ((left, "built", "built_head", "built"), (right, "plan", "next_head", "next")):
                D.rrect(s, T.fade(T.PANEL, a), rect, 18)
                if kind == "built":
                    D.rrect(s, T.fade(T.BUILT, a), rect, 18, 2)
                else:
                    D.dashed_rect(s, T.fade(T.DIM, a), rect, 2, 12, 8)
                ctx.mark(rect, "ui", head)
                Wg.status_tag(ctx, kind, (rect.left + 28, rect.top + 24), alpha=a, text=self.txt(head))
                ctx.text_block(self.txt(body), (rect.left + 28, rect.top + 80), T.SMALL + 2, T.FG,
                               width=rect.width - 56, alpha=a, max_lines=3)
            for k, line in enumerate(self.F.references):
                ctx.text(line, (T.W // 2, 870 + k * 32), T.TINY, T.DIM, "midtop", alpha=a)


def make(F):
    a = Act([Close(F)])
    a.number = 5
    return a
