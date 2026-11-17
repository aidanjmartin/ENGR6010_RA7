"""Slider, legend, axes, status tags, source lines, captions, code blocks, bars, cards."""
from __future__ import annotations

import math

import pygame

from . import draw as D
from . import theme as T
from .theme import fonts


# ===================================================================== slider
class Slider:
    """Horizontal slider in virtual pixels. Continuous, or snapping to `values`."""

    def __init__(self, x0, x1, y, vmin, vmax, value, values=None, color=T.DRONE, step=None):
        self.x0, self.x1, self.y = x0, x1, y
        self.vmin, self.vmax = vmin, vmax
        self.values = values
        self.step = step
        self.color = color
        self.value = value
        self.drag = False
        self.touched = False

    @property
    def hit(self) -> pygame.Rect:
        return pygame.Rect(self.x0 - 26, self.y - 26, self.x1 - self.x0 + 52, 52)

    def frac_of(self, v):
        return (v - self.vmin) / (self.vmax - self.vmin)

    def x_of(self, v):
        return self.x0 + (self.x1 - self.x0) * self.frac_of(v)

    def _set_from_x(self, x):
        f = min(1.0, max(0.0, (x - self.x0) / (self.x1 - self.x0)))
        v = self.vmin + f * (self.vmax - self.vmin)
        if self.values is not None:
            v = min(self.values, key=lambda u: abs(u - v))
        elif self.step:
            v = round(v / self.step) * self.step
        changed = v != self.value
        self.value = v
        self.touched = True
        return changed

    def handle(self, event) -> bool:
        vpos = getattr(event, "vpos", None)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and vpos and self.hit.collidepoint(vpos):
            self.drag = True
            self._set_from_x(vpos[0])
            return True
        if event.type == pygame.MOUSEMOTION and self.drag and vpos:
            self._set_from_x(vpos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.drag
            self.drag = False
            return was
        return False

    def draw(self, ctx, alpha=1.0, ticks=None, tick_labels=None, label=None, show_value=None):
        s = ctx.surf
        D.line(s, T.fade(T.GRID, alpha), (self.x0, self.y), (self.x1, self.y), 8)
        xv = self.x_of(self.value)
        D.line(s, T.fade(self.color, alpha * 0.85), (self.x0, self.y), (xv, self.y), 8)
        if ticks:
            for k, v in enumerate(ticks):
                x = self.x_of(v)
                D.disc(s, T.fade(T.DIM, alpha), (x, self.y), 5)
                if tick_labels:
                    ctx.text(tick_labels[k], (x, self.y + 22), T.TINY, T.DIM, "midtop", alpha=alpha)
        r = 17 if not self.drag else 20
        D.disc(s, T.fade(T.FG, alpha), (xv, self.y), r)
        D.disc(s, T.fade(self.color, alpha), (xv, self.y), r - 5)
        if label:
            ctx.text(label, (self.x0 - 30, self.y), T.SMALL, T.DIM, "midright", alpha=alpha)
        if show_value:
            ctx.text(show_value, (self.x1 + 30, self.y), T.SMALL, T.FG, "midleft", alpha=alpha)
        ctx.mark(self.hit, "ui", "slider")


# ===================================================================== legend
def legend_swatch(surf, style, color, x, y, w=46, alpha=1.0):
    c = T.fade(color, alpha)
    if style == "solid":
        D.line(surf, c, (x, y), (x + w, y), 5)
    elif style == "dashed":
        D.dashed(surf, c, [(x, y), (x + w, y)], 5, dash=12, gap=8)
    elif style == "dotted":
        D.dotted(surf, c, [(x, y), (x + w, y)], 3, 10)
    elif style == "bar":
        pygame.draw.rect(surf, c, pygame.Rect(x + 8, y - 12, w - 16, 24))
    elif style == "hatched":
        D.hatched_rect(surf, c, pygame.Rect(x + 8, y - 12, w - 16, 24), spacing=7, w=2,
                       fill=T.fade(T.mix(T.BG, color, 0.18), alpha))
    elif style == "box":
        D.rrect(surf, T.fade(T.mix(T.BG, color, 0.2), alpha), pygame.Rect(x + 6, y - 13, w - 12, 26), 6)
        D.rrect(surf, c, pygame.Rect(x + 6, y - 13, w - 12, 26), 6, 3)
    elif style == "dot":
        D.disc(surf, c, (x + w / 2, y), 9)
    elif style == "ring":
        D.ring(surf, c, (x + w / 2, y), 11, 3)
    elif style == "arrow":
        D.arrow(surf, c, (x, y), (x + w, y), 4, 14)


def legend(ctx, pos, items, alpha=1.0, size=T.SMALL, row=40, panel=True, anchor="topleft",
           horizontal=False):
    """items: [(label, color, style)]. Returns the legend rect."""
    F = fonts()
    sw = 46
    if horizontal:
        widths = [sw + 12 + F.width(lbl, size) for lbl, _, _ in items]
        gap = 34
        w = sum(widths) + gap * (len(items) - 1) + 40
        h = row + 12
        r = pygame.Rect(0, 0, w, h)
        setattr(r, anchor, (int(pos[0]), int(pos[1])))
        if panel:
            D.rrect(ctx.surf, T.fade(T.PANEL, alpha), r, 12)
            D.rrect(ctx.surf, T.fade(T.PANEL_EDGE, alpha), r, 12, 2)
        x = r.left + 20
        for (lbl, color, style), wd in zip(items, widths):
            legend_swatch(ctx.surf, style, color, x, r.centery, sw, alpha)
            ctx.text(lbl, (x + sw + 12, r.centery), size, T.FG, "midleft", alpha=alpha, record=False)
            x += wd + gap
        ctx.mark(r, "text", "legend")
        return r
    wmax = max(F.width(lbl, size) for lbl, _, _ in items)
    w = sw + 16 + wmax + 36
    h = row * len(items) + 18
    r = pygame.Rect(0, 0, w, h)
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    if panel:
        D.rrect(ctx.surf, T.fade(T.PANEL, alpha), r, 12)
        D.rrect(ctx.surf, T.fade(T.PANEL_EDGE, alpha), r, 12, 2)
    for k, (lbl, color, style) in enumerate(items):
        y = r.top + 9 + row * k + row // 2
        legend_swatch(ctx.surf, style, color, r.left + 18, y, sw, alpha)
        ctx.text(lbl, (r.left + 18 + sw + 14, y), size, T.fade(T.FG, 1.0), "midleft", alpha=alpha, record=False)
    ctx.mark(r, "text", "legend")
    return r


# ===================================================================== tags and lines
STATUS = {
    "built": ("Built and measured", T.BUILT),
    "plan": ("Plan, not yet built", T.DIM),
    "illus": ("Illustration", T.NEUTRAL),
    "canned": ("Canned example, no LLM running", T.NEUTRAL),
}


def tag(ctx, text, pos, color=T.DIM, anchor="topleft", alpha=1.0, size=T.TINY, icon=None, dashed=False):
    """Small pill. icon: check | ring | wave | bubble | warn | None."""
    F = fonts()
    img_w = F.width(text, size)
    pad_x, h = 14, size + 16
    extra = 30 if icon else 0
    r = pygame.Rect(0, 0, img_w + 2 * pad_x + extra, h)
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    s = ctx.surf
    D.rrect(s, T.fade(T.mix(T.BG, color, 0.13), alpha), r, h // 2)
    if dashed:
        _dashed_pill(s, T.fade(color, alpha * 0.9), r)
    else:
        D.rrect(s, T.fade(color, alpha * 0.85), r, h // 2, 2)
    ix, iy = r.left + pad_x + 10, r.centery
    c = T.fade(color, alpha)
    if icon == "check":
        D.check_mark(s, (ix, iy), 18, c)
    elif icon == "ring":
        D.ring(s, c, (ix, iy), 7, 2)
    elif icon == "wave":
        D.polyline(s, c, [(ix - 9 + k * 3, iy + 4 * math.sin(k * 1.1)) for k in range(7)], 2)
    elif icon == "bubble":
        D.rrect(s, c, pygame.Rect(ix - 9, iy - 7, 18, 12), 4, 2)
        D.poly(s, c, [(ix - 5, iy + 4), (ix - 1, iy + 4), (ix - 6, iy + 9)])
    elif icon == "warn":
        D.warning_triangle(s, (ix, iy + 1), 20, c)
    ctx.text(text, (r.left + pad_x + extra, r.centery), size, color, "midleft", alpha=alpha, record=False)
    ctx.mark(r, "text", text)
    return r


def _dashed_pill(surf, color, r):
    rad = r.height / 2
    pts = []
    for k in range(13):
        a = math.pi / 2 + math.pi * k / 12
        pts.append((r.left + rad + rad * math.cos(a), r.centery + rad * math.sin(a)))
    pts.append((r.right - rad, r.top))
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        pts.append((r.right - rad + rad * math.cos(a), r.centery + rad * math.sin(a)))
    pts.append((r.left + rad, r.bottom))
    D.dashed(surf, color, pts, 2, dash=7, gap=5)


def status_tag(ctx, kind, pos, anchor="topleft", alpha=1.0, size=T.TINY, text=None):
    """One consistent style for 'Built and measured', 'Plan, not yet built',
    'Illustration', and 'Canned example, no LLM running'."""
    label, color = STATUS[kind]
    icon = {"built": "check", "plan": "ring", "illus": "wave", "canned": "bubble"}[kind]
    return tag(ctx, text or label, pos, color, anchor, alpha, size, icon, dashed=(kind == "plan"))


def source_line(ctx, text, pos=(T.MARGIN, T.SOURCE_Y), anchor="topleft", alpha=1.0, size=T.TINY):
    return ctx.text(text, pos, size, T.DIM, anchor, alpha=alpha)


def header(ctx, kicker, title, alpha=1.0):
    if kicker:
        ctx.text(kicker.upper(), (T.MARGIN, T.KICKER_Y), T.KICKER, T.DIM, "topleft", bold=True, alpha=alpha)
    ctx.text(title, (T.MARGIN, T.TITLE_Y), T.TITLE, T.FG, "topleft", bold=True, alpha=alpha)


def captions(ctx, lines, alphas=None):
    for k, s in enumerate(lines[:2]):
        a = 1.0 if alphas is None else alphas[k]
        size = T.CAPTION if k == 0 else T.CAPTION2
        color = T.FG if k == 0 else T.DIM
        ctx.text(s, (T.W // 2, T.CAPTION_Y[k]), size, color, "midtop", alpha=a)


# ===================================================================== axes
class Axes:
    """Maps data to a plot rectangle and draws a clean axis frame."""

    def __init__(self, rect, xlim, ylim):
        self.r = pygame.Rect(rect)
        self.xlim, self.ylim = xlim, ylim

    def X(self, x):
        return self.r.left + (x - self.xlim[0]) / (self.xlim[1] - self.xlim[0]) * self.r.width

    def Y(self, y):
        return self.r.bottom - (y - self.ylim[0]) / (self.ylim[1] - self.ylim[0]) * self.r.height

    def P(self, x, y):
        return (self.X(x), self.Y(y))

    def frame(self, ctx, xticks=None, yticks=None, xfmt=str, yfmt=str, xlabel=None, ylabel=None,
              alpha=1.0, grid=True):
        s = ctx.surf
        if yticks:
            for v in yticks:
                y = self.Y(v)
                if grid:
                    pygame.draw.line(s, T.fade(T.GRID, alpha), (self.r.left, y), (self.r.right, y), 1)
                ctx.text(yfmt(v), (self.r.left - 14, y), T.TINY, T.DIM, "midright", alpha=alpha)
        if xticks:
            for v in xticks:
                x = self.X(v)
                pygame.draw.line(s, T.fade(T.DIM, alpha), (x, self.r.bottom), (x, self.r.bottom + 8), 2)
                ctx.text(xfmt(v), (x, self.r.bottom + 14), T.TINY, T.DIM, "midtop", alpha=alpha)
        D.line(s, T.fade(T.DIM, alpha), self.r.bottomleft, self.r.bottomright, 2)
        D.line(s, T.fade(T.DIM, alpha), self.r.bottomleft, self.r.topleft, 2)
        if xlabel:
            ctx.text(xlabel, (self.r.centerx, self.r.bottom + 52), T.SMALL, T.DIM, "midtop", alpha=alpha)
        if ylabel:
            ctx.text(ylabel, (self.r.left, self.r.top - 18), T.SMALL, T.DIM, "bottomleft", alpha=alpha)
        ctx.mark(self.r, "ui", "axes")


# ===================================================================== code and bars
def code_line(ctx, s, pos, color=T.TOOL, size=T.CODE, anchor="topleft", alpha=1.0, chars=None):
    """One line of monospace code. chars: how many characters are typed so far."""
    if chars is not None:
        full = ctx.text(s, pos, size, color, anchor, alpha=0.0, mono=True, record=False)
        shown = s[:max(0, int(chars))]
        if shown:
            ctx.text(shown, full.topleft, size, color, "topleft", alpha=alpha, mono=True, record=False)
        if alpha > 0 and shown:
            ctx.mark(full, "text", s)
        return full
    return ctx.text(s, pos, size, color, anchor, alpha=alpha, mono=True)


def hbar(ctx, rect, frac, color, alpha=1.0, hatched=False, track=True):
    r = pygame.Rect(rect)
    if track:
        D.rrect(ctx.surf, T.fade(T.GRID, alpha), r, min(8, r.height // 2))
    w = int(r.width * max(0.0, min(1.0, frac)))
    if w > 0:
        b = pygame.Rect(r.left, r.top, w, r.height)
        if hatched:
            D.hatched_rect(ctx.surf, T.fade(color, alpha), b, spacing=8, w=2,
                           fill=T.fade(T.mix(T.BG, color, 0.22), alpha), border=True)
        else:
            D.rrect(ctx.surf, T.fade(color, alpha), b, min(8, r.height // 2))
    ctx.mark(r, "ui", "bar")
    return r


# ===================================================================== study card
def study_card(ctx, rect, rows, alphas=None, title=None):
    """The standard three-row card: [(LABEL, text, color)]."""
    s = ctx.surf
    rect = pygame.Rect(rect)
    D.panel(s, rect, radius=20)
    ctx.mark(rect, "ui", "card")
    top0 = rect.top
    if title:
        ctx.text(title, (rect.left + 40, rect.top + 28), T.LABEL, T.FG, bold=True)
        top0 += 76
    row_h = (rect.bottom - top0) // len(rows)
    for k, (label, val, color) in enumerate(rows):
        a = 1.0 if alphas is None else alphas[k]
        top = top0 + k * row_h
        if k > 0 or title:
            pygame.draw.line(s, T.PANEL_EDGE, (rect.left + 28, top), (rect.right - 28, top), 2)
        D.rrect(s, T.fade(color, a), pygame.Rect(rect.left + 28, top + 26, 6, row_h - 52), 3)
        ctx.text(label, (rect.left + 56, top + 24), T.TINY, T.DIM, "topleft", bold=True, alpha=a)
        ctx.text_block(val, (rect.left + 56, top + 58), T.BODY, T.FG, width=rect.width - 100, alpha=a,
                       max_lines=2, line_gap=1.2)
