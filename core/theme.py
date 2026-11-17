"""Palette, type sizes, layout rows, and the font loader (UI and monospace).

All sizes are in virtual pixels on the 1920 x 1080 canvas.
"""
from __future__ import annotations

import os

import pygame
import pygame.freetype

# ---------------------------------------------------------------- canvas
W, H = 1920, 1080
SAFE = 40          # nothing may come closer than this to the canvas edge
MARGIN = 96        # normal content margin

# ---------------------------------------------------------------- palette
BG = (10, 12, 21)
PANEL = (18, 22, 36)
PANEL_EDGE = (44, 52, 76)
GRID = (32, 38, 58)
FG = (234, 237, 244)
DIM = (152, 160, 180)
FAINT = (88, 96, 120)
NEUTRAL = (198, 204, 218)

# Color meanings, the same in every act. Each one is always paired with an
# icon, a line style, or a label as well.
LANG = (190, 146, 255)      # language / LLM: the sentence, the LLM box, "Say"
TOOL = (82, 214, 190)       # tool calls: JSON calls, schema, accepted calls
DRONE = (92, 172, 255)      # the drone, its path, camera cone, its calls
DOG = (255, 150, 62)        # the dog, its path, its calls
HOME = (240, 208, 96)       # the home PC, links, return-home paths
WARN = (255, 84, 100)       # rejected calls, battery reserve, failed phrases

BUILT = (124, 224, 132)     # status tag: built and measured
OBJ_RED = (222, 64, 64)     # the red chair (an object color, not a meaning)

# ---------------------------------------------------------------- type sizes
COVER_TITLE = 64
TITLE = 58
KICKER = 24
CAPTION = 36
CAPTION2 = 30
BODY = 32
LABEL = 28
SMALL = 24
TINY = 22
CODE = 26

# ---------------------------------------------------------------- layout rows
KICKER_Y = 52
TITLE_Y = 84
CONTENT_TOP = 180
CONTENT_BOTTOM = 840
SOURCE_Y = 866
CAPTION_Y = (918, 970)

LINE_W = 3


def fade(color, a: float):
    """Blend a color toward the background (cheap alpha on an opaque canvas)."""
    a = max(0.0, min(1.0, a))
    return tuple(int(BG[i] + (color[i] - BG[i]) * a) for i in range(3))


def mix(c1, c2, a: float):
    a = max(0.0, min(1.0, a))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


# ---------------------------------------------------------------- fonts
_HOME = os.path.expanduser("~")


def _inter(name):
    return [(p, 0) for p in (f"{_HOME}/Library/Fonts/{name}", f"/Library/Fonts/{name}",
                             f"/usr/share/fonts/truetype/inter/{name}", f"C:/Windows/Fonts/{name}")]


# (family, regular [(path, index)], bold [(path, index)]); first that exists wins.
UI_FONT_CANDIDATES = [
    ("Inter", _inter("Inter-Regular.ttf"), _inter("Inter-Bold.ttf")),
    ("Helvetica Neue", [("/System/Library/Fonts/HelveticaNeue.ttc", 0)],
     [("/System/Library/Fonts/HelveticaNeue.ttc", 1)]),
    ("Arial",
     [("/System/Library/Fonts/Supplemental/Arial.ttf", 0), ("/Library/Fonts/Arial.ttf", 0),
      ("C:/Windows/Fonts/arial.ttf", 0), ("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf", 0)],
     [("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0), ("/Library/Fonts/Arial Bold.ttf", 0),
      ("C:/Windows/Fonts/arialbd.ttf", 0), ("/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf", 0)]),
]


def _jb(name):
    return [(p, 0) for p in (f"{_HOME}/Library/Fonts/{name}", f"/Library/Fonts/{name}",
                             f"/usr/share/fonts/truetype/jetbrains-mono/{name}", f"C:/Windows/Fonts/{name}")]


MONO_FONT_CANDIDATES = [
    ("JetBrains Mono", _jb("JetBrainsMono-Regular.ttf"), _jb("JetBrainsMono-Bold.ttf")),
    ("Menlo", [("/System/Library/Fonts/Menlo.ttc", 0)], [("/System/Library/Fonts/Menlo.ttc", 1)]),
    ("Courier New",
     [("/System/Library/Fonts/Supplemental/Courier New.ttf", 0), ("C:/Windows/Fonts/cour.ttf", 0),
      ("/usr/share/fonts/truetype/msttcorefonts/Courier_New.ttf", 0)],
     [("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", 0), ("C:/Windows/Fonts/courbd.ttf", 0),
      ("/usr/share/fonts/truetype/msttcorefonts/Courier_New_Bold.ttf", 0)]),
]


def _first_existing(cands):
    for path, idx in cands:
        if os.path.exists(path):
            return path, idx
    return None


def _bundled():
    """pygame ships freesansbold.ttf, so this fallback always exists offline."""
    p = os.path.join(os.path.dirname(pygame.__file__), "freesansbold.ttf")
    return (p, 0), (p, 0)


def _pick(cands, label):
    for family, reg, bold in cands:
        r = _first_existing(reg)
        if r:
            return family, r, _first_existing(bold) or r
    reg, bold = _bundled()
    return f"pygame default ({label} fallback)", reg, bold


class Fonts:
    def __init__(self):
        if not pygame.freetype.get_init():
            pygame.freetype.init()
        self.family, self.regular, self.bold = _pick(UI_FONT_CANDIDATES, "UI")
        self.mono_family, self.mono_regular, self.mono_bold = _pick(MONO_FONT_CANDIDATES, "mono")
        self._fonts = {}
        self._text = {}

    def font(self, size: int, bold: bool = False, mono: bool = False) -> pygame.freetype.Font:
        key = (int(size), bool(bold), bool(mono))
        f = self._fonts.get(key)
        if f is None:
            if mono:
                path, idx = self.mono_bold if bold else self.mono_regular
            else:
                path, idx = self.bold if bold else self.regular
            f = pygame.freetype.Font(path, int(size), font_index=idx)
            f.antialiased = True
            f.kerning = True
            f.pad = True
            self._fonts[key] = f
        return f

    def _has(self, font, ch) -> bool:
        try:
            m = font.get_metrics(ch)
        except pygame.error:
            return False
        return bool(m) and m[0] is not None

    def render(self, text: str, size: int, color, bold: bool = False, mono: bool = False) -> pygame.Surface:
        """Render text once at virtual resolution and cache it (transparent background).

        Characters the chosen face lacks (for example an arrow in some UI fonts)
        are drawn with the other face, so no glyph ever shows as a box."""
        key = (text, int(size), tuple(color), bool(bold), bool(mono))
        s = self._text.get(key)
        if s is None:
            main = self.font(size, bold, mono)
            alt = self.font(size, bold, not mono)
            runs, cur, cur_alt = [], "", False
            for ch in text:
                use_alt = (not ch.isspace()) and (not self._has(main, ch)) and self._has(alt, ch)
                if cur and use_alt != cur_alt:
                    runs.append((cur, cur_alt))
                    cur = ""
                cur_alt = use_alt
                cur += ch
            if cur:
                runs.append((cur, cur_alt))
            if not runs or (len(runs) == 1 and not runs[0][1]):
                surf, _ = main.render(text, tuple(color))
            else:
                parts = [(alt if a else main).render(r, tuple(color)) for r, a in runs]
                asc = max(((alt if a else main).get_sized_ascender()) for _, a in runs)
                h = max(p[0].get_height() + (asc - (alt if a else main).get_sized_ascender())
                        for p, (_, a) in zip(parts, runs))
                surf = pygame.Surface((sum(p[0].get_width() for p in parts), h), pygame.SRCALPHA)
                x = 0
                for (img, rect), (_, a) in zip(parts, runs):
                    f = alt if a else main
                    surf.blit(img, (x, asc - f.get_sized_ascender()))
                    x += img.get_width()
            s = surf.convert_alpha() if pygame.display.get_surface() is not None else surf
            self._text[key] = s
        return s

    def width(self, text: str, size: int, bold: bool = False, mono: bool = False) -> int:
        return self.render(text, size, (255, 255, 255), bold, mono).get_width()

    def wrap(self, text: str, size: int, max_w: int, bold: bool = False, mono: bool = False):
        lines = []
        for para in text.split("\n"):
            words = para.split()
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if cur and self.width(trial, size, bold, mono) > max_w:
                    lines.append(cur)
                    cur = w
                else:
                    cur = trial
            lines.append(cur)
        return lines


_FONTS = None


def fonts() -> Fonts:
    """Shared font cache. Rebuilt if pygame was shut down and restarted."""
    global _FONTS
    if _FONTS is not None and _FONTS._fonts:
        try:
            next(iter(_FONTS._fonts.values())).get_sized_height()
        except pygame.error:
            _FONTS = None
    if _FONTS is None or not pygame.freetype.get_init():
        _FONTS = Fonts()
    return _FONTS
