"""Generates the launcher icon (.iconset) and the dmg background image (pure Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

INDIGO = (79, 70, 229)
VIOLET = (124, 58, 237)
CYAN = (34, 211, 238)
BG_TOP = (13, 15, 26)
BG_BOTTOM = (26, 30, 51)


def gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def make_icon() -> Image.Image:
    S = 1024
    img = gradient((S, S), INDIGO, VIOLET).convert("RGBA")

    # macOS icons keep a transparent margin (~8% each side)
    pad = 82
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, S - pad, S - pad], radius=170, fill=255)
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(bg)

    # clapperboard: white body + striped clap bar
    body = [280, 430, 744, 720]
    d.rounded_rectangle(body, radius=28, fill=(245, 246, 252, 255))
    # play triangle on the body
    cx, cy = (body[0] + body[2]) // 2, (body[1] + body[3]) // 2 + 6
    d.polygon([(cx - 58, cy - 74), (cx - 58, cy + 74), (cx + 82, cy)], fill=(79, 70, 229, 255))

    # striped clap bar (drawn flat, rotated a touch)
    bar = Image.new("RGBA", (560, 150), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    bd.rounded_rectangle([0, 0, 559, 149], radius=26, fill=(245, 246, 252, 255))
    for i in range(-2, 8):
        x0 = i * 90
        bd.polygon([(x0, 0), (x0 + 45, 0), (x0 + 45 - 60, 149), (x0 - 60, 149)], fill=(30, 32, 56, 255))
    bar = bar.rotate(8, expand=True, resample=Image.BICUBIC)
    bg.alpha_composite(bar, (250, 236))

    # small spark: three rounded dots top-right
    for i, (x, y, r) in enumerate([(760, 320, 16), (800, 278, 11), (832, 246, 7)]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=CYAN + (255,))

    return bg


def write_iconset(icon: Image.Image) -> None:
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    root = ASSETS / "icon.iconset"
    root.mkdir(exist_ok=True)
    for s in sizes:
        img = icon.resize((s, s), Image.LANCZOS)
        img.save(root / f"icon_{s}x{s}.png")
        if s <= 512:
            icon.resize((s * 2, s * 2), Image.LANCZOS).save(root / f"icon_{s}x{s}@2x.png")


def make_background() -> None:
    W, H = 1400, 900
    img = gradient((W, H), BG_TOP, BG_BOTTOM).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    # soft violet glow top center + cyan bottom right (cinematic vignette)
    d.ellipse([W // 2 - 420, -260, W // 2 + 420, 260], fill=VIOLET + (36,))
    d.ellipse([W - 500, H - 320, W + 260, H + 260], fill=CYAN + (22,))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 27)
    except OSError:
        font = small = None
    if font:
        msg = "Trascina «CineForge AI» in Applicazioni"
        tw = d.textlength(msg, font=font)
        d.text(((W - tw) / 2, 660), msg, font=font, fill=(235, 238, 248, 255))
        hint = "poi apri l'app e clicca «Prepara e avvia»"
        hw = d.textlength(hint, font=small)
        d.text(((W - hw) / 2, 726), hint, font=small, fill=(150, 158, 185, 255))
    img.convert("RGB").save(ASSETS / "background.png")


if __name__ == "__main__":
    icon = make_icon()
    icon.save(ASSETS / "icon_1024.png")
    write_iconset(icon)
    make_background()
    print("assets ok:", sorted(p.name for p in ASSETS.rglob("*") if p.is_file()))
