"""Draws the app icons (PNG) with Pillow: python scripts/make_icons.py"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "icons")
INK, MARIGOLD, RANI, PAPER = (27, 31, 75), (255, 180, 0), (214, 36, 127), (238, 241, 246)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def font(size):
    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def icon(size, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 0 if maskable else int(size * 0.04)
    radius = 0 if maskable else int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1], radius=radius, fill=MARIGOLD, outline=INK, width=max(2, size // 32))
    inner = size * (0.16 if maskable else 0.12)
    # a shield with a check mark: the "dojo belt" of the app
    cx, top, w, h = size / 2, size * 0.2 + inner * 0.2, size * 0.5, size * 0.58
    shield = [(cx - w / 2, top), (cx + w / 2, top), (cx + w / 2, top + h * 0.55), (cx, top + h), (cx - w / 2, top + h * 0.55)]
    d.polygon([(x + size * 0.015, y + size * 0.015) for x, y in shield], fill=INK)
    d.polygon(shield, fill=RANI, outline=INK)
    d.line([(8, 0)], fill=INK)
    ck = [(cx - w * 0.22, top + h * 0.42), (cx - w * 0.04, top + h * 0.6), (cx + w * 0.26, top + h * 0.26)]
    d.line(ck, fill=PAPER, width=max(3, size // 18), joint="curve")
    return img


os.makedirs(OUT, exist_ok=True)
for name, size, m in (("icon-192.png", 192, False), ("icon-512.png", 512, False), ("maskable-512.png", 512, True), ("apple-touch-icon.png", 180, False), ("favicon-32.png", 32, False)):
    icon(size, m).save(os.path.join(OUT, name))
print("icons written to", OUT)
