"""Virtual 1920 x 1080 canvas, the present step, letterboxing, input mapping, modes.

Everything is drawn in virtual pixels. The window size is used in exactly one
place: compute_transform(), which both present() and map_mouse() share.
"""
from __future__ import annotations

import pygame

from . import theme as T
from .theme import fonts

VW, VH = T.W, T.H
WINDOWED_SIZE = (1600, 900)


# ------------------------------------------------------------------ transform
def compute_transform(win_w: int, win_h: int):
    """Return (scale, (offset_x, offset_y), (dest_w, dest_h)) for a target size."""
    scale = min(win_w / VW, win_h / VH)
    dw = max(1, int(round(VW * scale)))
    dh = max(1, int(round(VH * scale)))
    ox = (win_w - dw) // 2
    oy = (win_h - dh) // 2
    return scale, (ox, oy), (dw, dh)


def present_into(target: pygame.Surface, canvas: pygame.Surface):
    """Scale the canvas into any target surface, centered, with letterbox bars.

    Used for the real window and, unchanged, for offscreen screenshot targets.
    """
    tw, th = target.get_size()
    scale, (ox, oy), (dw, dh) = compute_transform(tw, th)
    target.fill(T.BG)
    if (dw, dh) == (VW, VH):
        target.blit(canvas, (ox, oy))
    else:
        target.blit(pygame.transform.smoothscale(canvas, (dw, dh)), (ox, oy))
    return scale, (ox, oy), (dw, dh)


def map_point(pos, scale, offset, ratio=(1.0, 1.0)):
    """Window (mouse) coordinates -> virtual canvas coordinates, or None if in a bar."""
    sx = pos[0] * ratio[0]
    sy = pos[1] * ratio[1]
    vx = (sx - offset[0]) / scale
    vy = (sy - offset[1]) / scale
    if 0 <= vx < VW and 0 <= vy < VH:
        return (vx, vy)
    return None


class Presenter:
    """Owns the window. Recomputes the transform after every mode change or resize."""

    def __init__(self):
        self.fullscreen = False
        self.scale = 1.0
        self.offset = (0, 0)
        self.dest = (VW, VH)
        self.ratio = (1.0, 1.0)
        self.surface_size = (VW, VH)
        self.window_size = (VW, VH)

    def set_mode(self, fullscreen: bool):
        self.fullscreen = fullscreen
        if fullscreen:
            size = pygame.display.get_desktop_sizes()[0]
            pygame.display.set_mode(size, pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)
        self.update_transform()

    def toggle(self):
        self.set_mode(not self.fullscreen)

    def update_transform(self):
        surf = pygame.display.get_surface()   # never cached across mode changes
        if surf is None:
            return
        sw, sh = surf.get_size()
        try:
            ww, wh = pygame.display.get_window_size()
        except Exception:
            ww, wh = sw, sh
        # On Retina the drawable surface can be larger than mouse coordinates.
        self.ratio = (sw / ww if ww else 1.0, sh / wh if wh else 1.0)
        self.surface_size = (sw, sh)
        self.window_size = (ww, wh)
        self.scale, self.offset, self.dest = compute_transform(sw, sh)

    def present(self, canvas: pygame.Surface):
        surf = pygame.display.get_surface()
        if surf is None:
            return
        if surf.get_size() != self.surface_size:
            self.update_transform()
        present_into(surf, canvas)
        pygame.display.flip()

    def map_mouse(self, pos):
        return map_point(pos, self.scale, self.offset, self.ratio)


# ------------------------------------------------------------------ drawing context
class Ctx:
    """Draw context bound to the virtual canvas.

    Text and UI helpers record bounding boxes so tests can check margins and
    overlaps without parsing pixels.
    """

    def __init__(self, surf: pygame.Surface):
        self.surf = surf
        self.records: list[tuple[str, pygame.Rect, str]] = []
        self.recording = True

    def clear(self):
        self.records = []

    def mark(self, rect, kind: str = "ui", name: str = ""):
        if self.recording:
            self.records.append((kind, pygame.Rect(rect), name))

    # -------------------------------------------------------------- text
    @staticmethod
    def _anchor(rect: pygame.Rect, pos, anchor: str):
        setattr(rect, anchor, (int(round(pos[0])), int(round(pos[1]))))
        return rect

    def text(self, s: str, pos, size: int = T.BODY, color=T.FG, anchor: str = "topleft",
             bold: bool = False, alpha: float = 1.0, record: bool = True, mono: bool = False) -> pygame.Rect:
        if not s:
            return pygame.Rect(int(pos[0]), int(pos[1]), 0, 0)
        img = fonts().render(s, size, color, bold, mono)
        r = self._anchor(img.get_rect(), pos, anchor)
        if alpha <= 0.0:
            return r
        if alpha < 1.0:
            img = img.copy()
            img.set_alpha(int(255 * alpha))
        self.surf.blit(img, r)
        if record:
            self.mark(r, "text", s)
        return r

    def text_block(self, s: str, pos, size: int = T.BODY, color=T.FG, width: int = 800,
                   anchor: str = "topleft", align: str = "left", bold: bool = False,
                   alpha: float = 1.0, line_gap: float = 1.22, max_lines: int | None = None,
                   mono: bool = False) -> pygame.Rect:
        """Wrapped text recorded as one block."""
        F = fonts()
        lines = F.wrap(s, size, width, bold, mono)
        if max_lines:
            lines = lines[:max_lines]
        lh = int(size * line_gap)
        imgs = [F.render(l, size, color, bold, mono) for l in lines]
        bw = max((i.get_width() for i in imgs), default=0)
        bh = lh * (len(lines) - 1) + (imgs[-1].get_height() if imgs else 0)
        block = self._anchor(pygame.Rect(0, 0, bw, bh), pos, anchor)
        if alpha > 0:
            for k, img in enumerate(imgs):
                if align == "center":
                    x = block.centerx - img.get_width() // 2
                elif align == "right":
                    x = block.right - img.get_width()
                else:
                    x = block.left
                if alpha < 1.0:
                    img = img.copy()
                    img.set_alpha(int(255 * alpha))
                self.surf.blit(img, (x, block.top + k * lh))
            self.mark(block, "text", s)
        return block

    def blit(self, img, pos, anchor="topleft", alpha=1.0, kind="ui"):
        r = self._anchor(img.get_rect(), pos, anchor)
        if alpha <= 0:
            return r
        if alpha < 1.0:
            img = img.copy()
            img.set_alpha(int(255 * alpha))
        self.surf.blit(img, r)
        self.mark(r, kind)
        return r
