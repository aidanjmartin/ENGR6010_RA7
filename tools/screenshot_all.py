"""Render every beat and step, then present each frame at several window sizes.

The presented frames come from the same present step the live window uses
(core.canvas.present_into), drawn into offscreen surfaces. Each one is cropped
to its content, resized back to 1920 x 1080, and compared to the raw canvas.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SIZES = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (1920, 1200), (1440, 900), (1366, 768)]
MAX_MAD = 8.0        # presented frame vs raw canvas (scaling blur is allowed here)
MAX_ALIGN_MAD = 1.0  # presented frame vs canvas scaled the same way: catches any shift or crop error


def mad(a, b):
    import numpy as np
    import pygame
    x = pygame.surfarray.array3d(a).astype(np.int16)
    y = pygame.surfarray.array3d(b).astype(np.int16)
    return float(np.abs(x - y).mean())


def roundtrip_mad(canvas, size):
    """Present into a target of `size`, crop the content, scale back, compare."""
    import pygame
    from core.canvas import present_into
    from core import theme as T
    target = pygame.Surface(size)
    _, (ox, oy), (dw, dh) = present_into(target, canvas)
    crop = target.subsurface(pygame.Rect(ox, oy, dw, dh))
    back = pygame.transform.smoothscale(crop, (T.W, T.H))
    ref = pygame.transform.smoothscale(pygame.transform.smoothscale(canvas, (dw, dh)), (T.W, T.H)) \
        if (dw, dh) != (T.W, T.H) else canvas
    # m_raw: against the raw canvas. m_align: against an independent scale round trip,
    # so blur cancels and only misplacement (offset, crop, size) shows up.
    return target, mad(back, canvas), mad(back, ref)


def shifted_control(canvas, size, dx=3):
    """Alignment score of a frame whose content is drawn dx px off. A real layout
    shift this small must fail the alignment limit, or the check would be blind."""
    import pygame
    from core import theme as T
    moved = pygame.Surface((T.W, T.H))
    moved.fill(T.BG)
    moved.blit(canvas, (dx, 0))
    target = pygame.Surface(size)
    from core.canvas import present_into
    _, (ox, oy), (dw, dh) = present_into(target, moved)
    back = pygame.transform.smoothscale(target.subsurface(pygame.Rect(ox, oy, dw, dh)), (T.W, T.H))
    ref = pygame.transform.smoothscale(pygame.transform.smoothscale(canvas, (dw, dh)), (T.W, T.H))
    return mad(back, ref)


def run(outdir: str, sizes=SIZES, save=True) -> bool:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from main import build_acts, all_states, render_state
    from core.facts import Facts
    from core.canvas import Ctx
    from core import theme as T
    pygame.init()
    pygame.display.set_mode((64, 64))
    os.makedirs(outdir, exist_ok=True)
    F = Facts()
    acts = build_acts(F)
    canvas = pygame.Surface((T.W, T.H))
    ctx = Ctx(canvas)
    ok = True
    worst = 0.0
    worst_align = 0.0
    for ai, bi, st in all_states(acts):
        beat = render_state(acts, ai, bi, st, ctx)
        name = f"beat_{beat.key.replace('.', '_')}" + (f"_step{st + 1}" if beat.steps > 1 else "")
        if save:
            pygame.image.save(canvas, os.path.join(outdir, f"{name}_canvas.png"))
        for size in sizes:
            target, m, m_align = roundtrip_mad(canvas, size)
            worst = max(worst, m)
            worst_align = max(worst_align, m_align)
            passed = m <= MAX_MAD and m_align <= MAX_ALIGN_MAD
            ok = ok and passed
            if save:
                pygame.image.save(target, os.path.join(outdir, f"{name}_{size[0]}x{size[1]}.png"))
            if not passed:
                print(f"[FAIL] {name} at {size}: mean abs diff {m:.2f}, alignment diff {m_align:.2f}")
        print(f"{name}: rendered at {len(sizes)} sizes")
    ctrl = min(shifted_control(canvas, sz) for sz in sizes)
    ok = ok and ctrl > MAX_ALIGN_MAD
    print(f"worst mean abs pixel difference vs canvas: {worst:.2f} (limit {MAX_MAD})")
    print(f"control: content shifted 3 px scores {ctrl:.2f} on the alignment check (must exceed {MAX_ALIGN_MAD})")
    print(f"worst alignment difference: {worst_align:.3f} (limit {MAX_ALIGN_MAD})")
    print("PASS" if ok else "FAIL")
    pygame.quit()
    return ok


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    sys.exit(0 if run(out) else 1)
