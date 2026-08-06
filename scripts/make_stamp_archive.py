"""Simple Pillow-based approximation of the make-photo-stamp-archive composite.

Not an AI regeneration: crops/resizes the source photo faithfully into a left
panel and hand-draws a stamp-style graphic (circle seal, dry-ink texture,
typewriter caption) onto a paper-toned right panel.
"""
import random
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

random.seed(7)

SRC = Path("raw/529411.jpg")
OUT = Path("processed/529411_stamp_archive.jpg")
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

CANVAS_H = 1600
PHOTO_W = 900
PAPER_W = round(PHOTO_W * 45 / 55)

PAPER_COLOR = (240, 233, 217)
INK_NAVY = (40, 55, 95)
INK_CARAMEL = (150, 96, 46)
INK_FADED = (120, 112, 96)


def load_photo_panel():
    img = ImageOps.exif_transpose(Image.open(SRC)).convert("RGB")
    w, h = img.size
    target_aspect = PHOTO_W / CANVAS_H
    new_h = round(w / target_aspect)
    if new_h <= h:
        top = (h - new_h) // 2
        box = (0, top, w, top + new_h)
    else:
        new_w = round(h * target_aspect)
        left = (w - new_w) // 2
        box = (left, 0, left + new_w, h)
    cropped = img.crop(box)
    return cropped.resize((PHOTO_W, CANVAS_H), Image.LANCZOS)


def paper_texture(w, h):
    base = Image.new("RGB", (w, h), PAPER_COLOR)
    noise = Image.effect_noise((w, h), 18).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    fiber = Image.merge("RGB", [noise, noise, noise])
    base = Image.blend(base, fiber, 0.06)
    # faint vertical scan streaks
    draw = ImageDraw.Draw(base)
    for _ in range(40):
        x = random.randint(0, w)
        shade = random.randint(-6, 6)
        col = tuple(max(0, min(255, c + shade)) for c in PAPER_COLOR)
        draw.line([(x, 0), (x, h)], fill=col, width=1)
    return base.filter(ImageFilter.GaussianBlur(0.3))


def worn_circle(draw, cx, cy, r, color, width=5, gap_prob=0.16, jitter=2):
    steps = 240
    prev = None
    for i in range(steps + 1):
        ang = 2 * math.pi * i / steps
        if random.random() < gap_prob:
            prev = None
            continue
        rr = r + random.uniform(-jitter, jitter)
        x = cx + rr * math.cos(ang)
        y = cy + rr * math.sin(ang)
        if prev is not None:
            w = max(1, width + random.randint(-2, 1))
            draw.line([prev, (x, y)], fill=color, width=w)
        prev = (x, y)


def stipple(draw, cx, cy, r, color, count, alpha=90):
    for _ in range(count):
        ang = random.uniform(0, 2 * math.pi)
        rr = random.uniform(0, r)
        x = cx + rr * math.cos(ang)
        y = cy + rr * math.sin(ang)
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=color)


def draw_stamp(paper, cx, cy, r):
    stamp_layer = Image.new("RGBA", paper.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(stamp_layer)

    worn_circle(d, cx, cy, r, INK_NAVY + (200,), width=6)
    worn_circle(d, cx, cy, r - 10, INK_NAVY + (90,), width=2, gap_prob=0.35)

    # three small stars along the upper arc, echoing the source logo
    star_r = r * 0.62
    for i, ang_deg in enumerate((-58, -20, 18)):
        ang = math.radians(ang_deg - 90)
        sx = cx + star_r * math.cos(ang)
        sy = cy + star_r * math.sin(ang)
        draw_star(d, sx, sy, r * 0.09, INK_NAVY + (210,))

    # simplified tapered glass silhouette holding the layered drink
    gw, gh = r * 0.62, r * 0.9
    gx0, gy0 = cx - gw / 2, cy - gh / 2 + r * 0.12
    gx1, gy1 = cx + gw / 2, cy + gh / 2 + r * 0.12
    taper = gw * 0.18
    glass = [
        (gx0 + taper, gy0), (gx1 - taper, gy0),
        (gx1, gy1), (gx0, gy1),
    ]
    d.line(glass + [glass[0]], fill=INK_NAVY + (190,), width=3, joint="curve")

    foam_top = gy0 + (gy1 - gy0) * 0.32
    d.polygon(
        [(gx0 + taper * 0.4, foam_top), (gx1 - taper * 0.4, foam_top), (gx1 - 2, gy1 - 2), (gx0 + 2, gy1 - 2)],
        fill=INK_CARAMEL + (70,),
    )
    stipple(d, cx, (foam_top + gy1) / 2, gw * 0.35, INK_CARAMEL + (110,), 220)

    paper.alpha_composite(stamp_layer) if paper.mode == "RGBA" else paper.paste(
        stamp_layer, (0, 0), stamp_layer
    )


def draw_star(d, cx, cy, r, color):
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    d.polygon(pts, fill=color)


def draw_caption(paper, x, y, title, subtitle):
    d = ImageDraw.Draw(paper)
    f_title = ImageFont.truetype(FONT_MONO_BOLD, 22)
    f_sub = ImageFont.truetype(FONT_MONO, 16)
    faded_title = INK_FADED + (170,) if paper.mode == "RGBA" else INK_FADED
    faded_sub = INK_FADED + (140,) if paper.mode == "RGBA" else tuple(
        min(255, c + 40) for c in INK_FADED
    )
    d.text((x, y), title, font=f_title, fill=faded_title)
    d.text((x, y + 30), subtitle, font=f_sub, fill=faded_sub)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    photo_panel = load_photo_panel()

    paper = paper_texture(PAPER_W, CANVAS_H).convert("RGBA")

    r = PAPER_W * 0.30
    cx = PAPER_W - r - 70
    cy = r + 90
    draw_stamp(paper, cx, cy, r)
    draw_caption(paper, cx - r * 0.75, cy + r + 30, "COFFEE FLOAT", "glass / foam / orion")

    paper_rgb = Image.new("RGB", paper.size, PAPER_COLOR)
    paper_rgb.paste(paper, (0, 0), paper)

    canvas = Image.new("RGB", (PHOTO_W + PAPER_W, CANVAS_H), PAPER_COLOR)
    canvas.paste(photo_panel, (0, 0))
    canvas.paste(paper_rgb, (PHOTO_W, 0))

    d = ImageDraw.Draw(canvas)
    d.line([(PHOTO_W, 0), (PHOTO_W, CANVAS_H)], fill=(210, 200, 180), width=2)

    canvas.save(OUT, quality=95)
    print(f"saved {OUT} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
