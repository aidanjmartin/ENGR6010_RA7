"""Vector drawing primitives and original robot art.

Robot drawings are generic: a four-legged robot dog (side and top views), a small
quadrotor with propeller guards (side and top views), and a desktop tower. No
brands, logos, or likenesses of commercial products.
"""
from __future__ import annotations

import math

import pygame
import pygame.gfxdraw as gfx

from . import theme as T


# ===================================================================== primitives
def _i(p):
    return int(round(p[0])), int(round(p[1]))


def disc(surf, color, c, r):
    x, y = _i(c)
    r = int(round(r))
    if r <= 0:
        return
    gfx.aacircle(surf, x, y, r, color)
    gfx.filled_circle(surf, x, y, r, color)


def ring(surf, color, c, r, w=3):
    x, y = _i(c)
    pygame.draw.circle(surf, color, (x, y), int(round(r)), max(1, int(w)))
    gfx.aacircle(surf, x, y, int(round(r)), color)
    if w > 1:
        gfx.aacircle(surf, x, y, int(round(r - w + 1)), color)


def poly(surf, color, pts):
    ip = [_i(p) for p in pts]
    if len(ip) < 3:
        return
    gfx.aapolygon(surf, ip, color)
    gfx.filled_polygon(surf, ip, color)


def poly_alpha(surf, color, pts, alpha=60):
    """Translucent filled polygon (blended onto an opaque canvas)."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
    if w <= 0 or h <= 0:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    loc = [(int(round(p[0] - x0)), int(round(p[1] - y0))) for p in pts]
    gfx.filled_polygon(tmp, loc, (*color[:3], int(alpha)))
    gfx.aapolygon(tmp, loc, (*color[:3], int(alpha)))
    surf.blit(tmp, (x0, y0))


def line(surf, color, a, b, w=T.LINE_W, cap=True):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if w <= 1.5:
        pygame.draw.aaline(surf, color, a, b)
        return
    if L < 1e-6:
        disc(surf, color, a, w / 2)
        return
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    poly(surf, color, [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)])
    if cap and w >= 4:
        disc(surf, color, a, w / 2 - 0.5)
        disc(surf, color, b, w / 2 - 0.5)


def polyline(surf, color, pts, w=T.LINE_W, closed=False):
    if len(pts) < 2:
        return
    seq = list(pts) + ([pts[0]] if closed else [])
    for a, b in zip(seq[:-1], seq[1:]):
        line(surf, color, a, b, w, cap=False)
    if w >= 4:
        for p in seq:
            disc(surf, color, p, w / 2 - 0.5)


def dashed(surf, color, pts, w=T.LINE_W, dash=16, gap=11, phase=0.0):
    """Dashed polyline measured along arc length."""
    if len(pts) < 2:
        return
    period = dash + gap
    s = -phase % period
    pos = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-9:
            continue
        t0 = 0.0
        while t0 < L:
            m = (pos + t0 + s) % period
            if m < dash:
                seg = min(dash - m, L - t0)
                p0 = (a[0] + (b[0] - a[0]) * t0 / L, a[1] + (b[1] - a[1]) * t0 / L)
                t1 = t0 + seg
                p1 = (a[0] + (b[0] - a[0]) * t1 / L, a[1] + (b[1] - a[1]) * t1 / L)
                line(surf, color, p0, p1, w, cap=False)
                t0 = t1
            else:
                t0 += period - m
        pos += L


def dotted(surf, color, pts, r=2.5, spacing=12):
    if len(pts) < 2:
        return
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-9:
            continue
        t = (-acc) % spacing
        while t <= L:
            disc(surf, color, (a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L), r)
            t += spacing
        acc += L


def arrow(surf, color, a, b, w=4, head=18, style="solid", head_w=None):
    ax, ay = a
    bx, by = b
    L = math.hypot(bx - ax, by - ay)
    if L < 1:
        return
    ux, uy = (bx - ax) / L, (by - ay) / L
    head = min(head, L * 0.6)
    hw = (head_w or head * 0.62)
    base = (bx - ux * head, by - uy * head)
    if style == "dashed":
        dashed(surf, color, [a, base], w, dash=12, gap=9)
    else:
        line(surf, color, a, base, w, cap=False)
    poly(surf, color, [(bx, by), (base[0] - uy * hw, base[1] + ux * hw), (base[0] + uy * hw, base[1] - ux * hw)])


def rrect(surf, color, rect, radius=12, width=0):
    pygame.draw.rect(surf, color, pygame.Rect(rect), width, border_radius=int(radius))


def dashed_rect(surf, color, rect, w=3, dash=14, gap=9, radius=0):
    r = pygame.Rect(rect)
    pts = [r.topleft, r.topright, r.bottomright, r.bottomleft, r.topleft]
    dashed(surf, color, pts, w, dash, gap)


def hatched_rect(surf, color, rect, spacing=11, w=2, fill=None, border=True):
    r = pygame.Rect(rect)
    if r.width <= 0 or r.height <= 0:
        return
    if fill is not None:
        pygame.draw.rect(surf, fill, r)
    old = surf.get_clip()
    surf.set_clip(r.clip(old) if old else r)
    x = r.left - r.height
    while x < r.right:
        pygame.draw.line(surf, color, (x, r.bottom), (x + r.height, r.top), w)
        x += spacing
    surf.set_clip(old)
    if border:
        pygame.draw.rect(surf, color, r, 2)


def panel(surf, rect, color=T.PANEL, edge=T.PANEL_EDGE, radius=18):
    rrect(surf, color, rect, radius)
    rrect(surf, edge, rect, radius, 2)


def warning_triangle(surf, center, size, color=T.WARN):
    cx, cy = center
    h = size * 0.87
    pts = [(cx, cy - h * 0.6), (cx + size / 2, cy + h * 0.4), (cx - size / 2, cy + h * 0.4)]
    poly(surf, color, pts)
    bar_w = max(2, size * 0.09)
    line(surf, T.BG, (cx, cy - h * 0.28), (cx, cy + h * 0.08), bar_w)
    disc(surf, T.BG, (cx, cy + h * 0.24), bar_w * 0.6)


# ===================================================================== robot dog
# Leg angle convention: angle from straight down, positive toward the front (+x).
DOG = dict(body_w=230, body_h=62, head_w=70, head_h=46, l1=74, l2=74)
HIPS = {"front": 82, "rear": -82}


def _rounded(x0, y0, x1, y1, r, n=5):
    """Corner points of a rounded rectangle, clockwise from top-left."""
    pts = []
    corners = [((x0 + r, y0 + r), math.pi), ((x1 - r, y0 + r), 1.5 * math.pi),
               ((x1 - r, y1 - r), 0.0), ((x0 + r, y1 - r), 0.5 * math.pi)]
    for (cx, cy), a0 in corners:
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def dog_points(pose, scale=1.0):
    """Body and head outlines, an accent stripe, and legs [(hip, knee, foot, near)] in a local frame.

    pose = dict(rot=angle, legs=[(hip, knee)] for front-near, front-far, rear-near, rear-far)
    """
    s = scale
    rot = pose.get("rot", 0.0)
    c, sn = math.cos(rot), math.sin(rot)

    def R(p):
        return (p[0] * c - p[1] * sn, p[0] * sn + p[1] * c)

    bw, bh = DOG["body_w"] * s, DOG["body_h"] * s
    body = [R(p) for p in _rounded(-bw / 2, -bh / 2, bw / 2, bh / 2, 16 * s)]
    hw, hh = DOG["head_w"] * s, DOG["head_h"] * s
    hx0 = bw / 2 - hw * 0.25
    hy0 = -bh / 2 - hh * 0.45
    head = [R(p) for p in _rounded(hx0, hy0, hx0 + hw, hy0 + hh, 12 * s)]
    stripe = [R((-bw / 2 + 14 * s, -bh * 0.12)), R((bw / 2 - 14 * s, -bh * 0.12))]
    eye = R((hx0 + hw * 0.72, hy0 + hh * 0.45))
    legs = []
    names = [("front", True), ("front", False), ("rear", True), ("rear", False)]
    for (which, near), (hip_a, knee_a) in zip(names, pose["legs"]):
        hip = (HIPS[which] * s + (0 if near else -12 * s), bh * 0.22)
        a1 = hip_a
        knee = (hip[0] + DOG["l1"] * s * math.sin(a1), hip[1] + DOG["l1"] * s * math.cos(a1))
        a2 = hip_a + knee_a
        foot = (knee[0] + DOG["l2"] * s * math.sin(a2), knee[1] + DOG["l2"] * s * math.cos(a2))
        legs.append((R(hip), R(knee), R(foot), near))
    return body, head, legs, stripe, eye


def draw_dog(surf, pose, origin_x, ground_y, scale=1.0, color=T.NEUTRAL, accent=T.DOG,
             alpha=1.0, silhouette=False):
    """Draw the robot dog with its lowest point resting on ground_y."""
    body, head, legs, stripe, eye = dog_points(pose, scale)
    pts = body + head + [l[2] for l in legs] + [l[1] for l in legs]
    foot_r = 10 * scale
    max_y = max(p[1] for p in pts) + foot_r * 0.6
    oy = ground_y - max_y + pose.get("lift", 0.0)
    ox = origin_x

    def P(p):
        return (p[0] + ox, p[1] + oy)

    col = T.fade(color, alpha)
    far = T.fade(T.mix(color, T.BG, 0.5), alpha)
    acc = T.fade(accent, alpha)
    lw = 15 * scale
    for hip, knee, foot, near in legs:
        if not near:
            line(surf, far, P(hip), P(knee), lw)
            line(surf, far, P(knee), P(foot), lw * 0.8)
            disc(surf, far, P(foot), foot_r)
    poly(surf, T.fade(T.mix(color, T.BG, 0.12), alpha), [P(p) for p in body])
    poly(surf, col, [P(p) for p in head])
    if not silhouette:
        line(surf, acc, P(stripe[0]), P(stripe[1]), max(2, 7 * scale))
        disc(surf, T.fade(T.BG, alpha), P(eye), 8 * scale)
        disc(surf, acc, P(eye), 4.5 * scale)
    for hip, knee, foot, near in legs:
        if near:
            line(surf, col, P(hip), P(knee), lw)
            line(surf, col, P(knee), P(foot), lw * 0.8)
            disc(surf, T.fade(T.mix(color, T.BG, 0.35), alpha), P(hip), 12 * scale)
            disc(surf, col, P(knee), 8.5 * scale)
            disc(surf, acc, P(foot), foot_r)
    xs = [P(p)[0] for p in pts]
    ys = [P(p)[1] for p in pts]
    return pygame.Rect(int(min(xs) - lw), int(min(ys) - lw), int(max(xs) - min(xs) + 2 * lw),
                       int(max(ys) - min(ys) + 2 * lw))


STAND = (-0.45, 0.9)
CROUCH = (-1.05, 2.1)
TUCK = (0.6, -1.9)


def dog_pose(legs_each, rot=0.0):
    return {"rot": rot, "legs": [legs_each] * 4}


def gait_pose(phase, amp=1.0):
    """Trot: diagonal pairs move together."""
    legs = []
    for k, off in enumerate([0.0, math.pi, math.pi, 0.0]):
        ph = phase + off
        hip = STAND[0] + 0.32 * amp * math.sin(ph)
        lift = max(0.0, math.cos(ph))
        knee = STAND[1] + 0.55 * amp * lift
        hip -= 0.12 * amp * lift
        legs.append((hip, knee))
    return {"rot": 0.0, "legs": legs}


def blend_pose(a, b, p):
    return {"rot": a["rot"] + (b["rot"] - a["rot"]) * p,
            "legs": [(la[0] + (lb[0] - la[0]) * p, la[1] + (lb[1] - la[1]) * p)
                     for la, lb in zip(a["legs"], b["legs"])],
            "lift": a.get("lift", 0.0) + (b.get("lift", 0.0) - a.get("lift", 0.0)) * p}


# ===================================================================== robot dog, top view
def dog_top(surf, center, heading, length=70, color=T.DOG, alpha=1.0, phase=0.0):
    """Top-down robot dog. heading in radians (0 = +x on screen)."""
    cx, cy = center
    c, s = math.cos(heading), math.sin(heading)

    def P(x, y):
        return (cx + x * c - y * s, cy + x * s + y * c)

    L, Wd = length / 2, length * 0.2
    col = T.fade(color, alpha)
    legc = T.fade(T.mix(color, T.BG, 0.35), alpha)
    for k, (x, side) in enumerate([(L * 0.62, 1), (L * 0.62, -1), (-L * 0.62, 1), (-L * 0.62, -1)]):
        swing = 0.18 * length * math.sin(phase + (0 if k in (0, 3) else math.pi))
        hip = P(x, side * Wd)
        foot = P(x + swing, side * (Wd + length * 0.2))
        line(surf, legc, hip, foot, max(3, length * 0.08))
        disc(surf, legc, foot, max(2, length * 0.05))
    poly(surf, col, [P(p[0], p[1]) for p in _rounded(-L, -Wd, L, Wd, Wd * 0.8, 4)])
    head = [P(p[0], p[1]) for p in _rounded(L * 0.78, -Wd * 0.75, L * 1.22, Wd * 0.75, Wd * 0.6, 3)]
    poly(surf, T.fade(T.mix(color, T.FG, 0.35), alpha), head)
    line(surf, T.fade(T.BG, alpha), P(-L * 0.6, 0), P(L * 0.5, 0), max(2, length * 0.04))


# ===================================================================== quadrotor
def drone_top(surf, center, heading, size=60, color=T.DRONE, alpha=1.0, t=0.0):
    """Top-down quadrotor with round propeller guards. Camera dot marks the front."""
    cx, cy = center
    col = T.fade(color, alpha)
    guard = T.fade(T.mix(color, T.BG, 0.3), alpha)
    blade = T.fade(T.mix(color, T.BG, 0.55), alpha)
    arm = size * 0.5
    rotor_r = size * 0.3
    for k in range(4):
        a = heading + math.pi / 4 + k * math.pi / 2
        tip = (cx + arm * math.cos(a), cy + arm * math.sin(a))
        line(surf, col, (cx, cy), tip, max(2, size * 0.09))
        ring(surf, guard, tip, rotor_r, max(2, int(size * 0.05)))
        spin = t * 30 * (1 if k % 2 == 0 else -1)
        for j in range(2):
            b = spin + j * math.pi
            line(surf, blade, (tip[0] - rotor_r * 0.8 * math.cos(b), tip[1] - rotor_r * 0.8 * math.sin(b)),
                 (tip[0] + rotor_r * 0.8 * math.cos(b), tip[1] + rotor_r * 0.8 * math.sin(b)), 2, cap=False)
    c, s = math.cos(heading), math.sin(heading)
    bl, bw = size * 0.3, size * 0.2
    body = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in _rounded(-bl, -bw, bl, bw, bw * 0.6, 3)]
    poly(surf, col, body)
    disc(surf, T.fade(T.FG, alpha), (cx + bl * 0.7 * c, cy + bl * 0.7 * s), max(2, size * 0.07))


def drone_side(surf, center, width=150, color=T.DRONE, alpha=1.0, t=0.0):
    """Side view: flat body, two visible arms with guards, forward camera on the right."""
    cx, cy = center
    col = T.fade(color, alpha)
    dark = T.fade(T.mix(color, T.BG, 0.4), alpha)
    bw, bh = width * 0.42, width * 0.13
    for sx in (-1, 1):
        x = cx + sx * width * 0.36
        line(surf, dark, (cx, cy - bh * 0.1), (x, cy - bh * 0.55), max(3, width * 0.035))
        gw = width * 0.3
        rrect(surf, dark, pygame.Rect(int(x - gw / 2), int(cy - bh * 0.95), int(gw), int(bh * 0.55)),
              int(bh * 0.25), max(2, int(width * 0.018)))
        ph = math.sin(t * 50 + sx)
        line(surf, T.fade(T.mix(color, T.FG, 0.3), alpha), (x - gw * 0.42 * ph, cy - bh * 0.9),
             (x + gw * 0.42 * ph, cy - bh * 0.9), 3, cap=False)
    rrect(surf, col, pygame.Rect(int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh)), int(bh * 0.4))
    disc(surf, T.fade(T.BG, alpha), (cx + bw * 0.42, cy), bh * 0.32)
    disc(surf, T.fade(T.FG, alpha), (cx + bw * 0.42, cy), bh * 0.18)
    for sx in (-1, 1):
        line(surf, dark, (cx + sx * bw * 0.3, cy + bh / 2), (cx + sx * bw * 0.36, cy + bh * 0.95), 3)
    return pygame.Rect(int(cx - width / 2), int(cy - bh), int(width), int(bh * 2))


# ===================================================================== home PC
def pc_tower(surf, center_bottom, height=150, color=T.HOME, alpha=1.0, label=True):
    """Generic desktop tower with a GPU slot glow. Returns its rect."""
    x, yb = center_bottom
    w = height * 0.48
    r = pygame.Rect(int(x - w / 2), int(yb - height), int(w), int(height))
    rrect(surf, T.fade(T.PANEL, alpha), r, 10)
    rrect(surf, T.fade(color, alpha), r, 10, 3)
    for k in range(3):
        y = r.top + height * (0.14 + 0.06 * k)
        line(surf, T.fade(T.mix(color, T.BG, 0.45), alpha), (r.left + w * 0.18, y), (r.right - w * 0.18, y), 3)
    gpu = pygame.Rect(int(r.left + w * 0.14), int(r.top + height * 0.56), int(w * 0.72), int(height * 0.12))
    rrect(surf, T.fade(T.mix(color, T.BG, 0.2), alpha), gpu, 4)
    disc(surf, T.fade(color, alpha), (r.centerx, r.bottom - height * 0.12), height * 0.04)
    return r


# ===================================================================== map props
def chair_top(surf, center, size=26, color=T.NEUTRAL, alpha=1.0, heading=0.0):
    cx, cy = center
    c, s = math.cos(heading), math.sin(heading)

    def P(x, y):
        return (cx + x * c - y * s, cy + x * s + y * c)

    h = size / 2
    poly(surf, T.fade(color, alpha), [P(-h, -h), P(h, -h), P(h, h), P(-h, h)])
    line(surf, T.fade(T.mix(color, T.FG, 0.4), alpha), P(-h, -h - 4), P(h, -h - 4), 6)


def table_top(surf, rect, color=(140, 120, 96), alpha=1.0):
    r = pygame.Rect(rect)
    rrect(surf, T.fade(color, alpha), r, 8)
    rrect(surf, T.fade(T.mix(color, T.FG, 0.3), alpha), r, 8, 2)


def check_mark(surf, center, size=24, color=T.TOOL):
    cx, cy = center
    polyline(surf, color, [(cx - size * 0.45, cy), (cx - size * 0.12, cy + size * 0.35),
                           (cx + size * 0.5, cy - size * 0.4)], max(3, size * 0.16))


def cross_mark(surf, center, size=24, color=T.WARN):
    cx, cy = center
    h = size * 0.38
    line(surf, color, (cx - h, cy - h), (cx + h, cy + h), max(3, size * 0.16))
    line(surf, color, (cx - h, cy + h), (cx + h, cy - h), max(3, size * 0.16))


def battery_icon(surf, rect, frac, color, edge=T.FG):
    r = pygame.Rect(rect)
    rrect(surf, edge, r, 5, 2)
    nub = pygame.Rect(r.right, r.centery - r.height // 5, 5, r.height * 2 // 5)
    rrect(surf, edge, nub, 2)
    inner = r.inflate(-8, -8)
    inner.width = max(0, int(inner.width * max(0.0, min(1.0, frac))))
    if inner.width:
        rrect(surf, color, inner, 3)


def pin(surf, tip, size=34, color=T.OBJ_RED, alpha=1.0):
    x, y = tip
    head = (x, y - size)
    poly(surf, T.fade(color, alpha), [(x, y), (x - size * 0.42, y - size * 0.75), (x + size * 0.42, y - size * 0.75)])
    disc(surf, T.fade(color, alpha), head, size * 0.45)
    disc(surf, T.fade(T.FG, alpha), head, size * 0.18)


def camera_icon(surf, center, size=40, color=T.NEUTRAL):
    cx, cy = center
    r = pygame.Rect(0, 0, size * 1.4, size)
    r.center = (int(cx), int(cy))
    rrect(surf, color, r, 6)
    disc(surf, T.BG, r.center, size * 0.3)
    disc(surf, color, r.center, size * 0.18)
    rrect(surf, color, pygame.Rect(r.left + size * 0.2, r.top - size * 0.2, size * 0.4, size * 0.24), 3)
