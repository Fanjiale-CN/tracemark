#!/usr/bin/env python3
"""TraceMark render engine — template-driven seal/postcard synthesis.

Usage:
    python3 render.py --config examples/<case>/config.yaml
    python3 render.py --config examples/<case>/config.yaml --no-photo   # seal-only output

config.yaml schema:
    track: zh | jp | wz
    template: <template name>
    text: "<seal text>"
    seed: 7
    photo: <path or null>               # photo layer (postcard modes)
    caption: "<one-line caption>"
    date: "2026.08.15"
    place: "<place name>"
    style:
        vermilion: "#C8392B" | "#9E2A2B"
        mode: zh-wen ("zhu"/"bai") | jp ("red"/"black") | wz ("crimson"/"wine"/"gold")
"""
import os
import sys
import argparse
import importlib.util

import yaml
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from texture import SealTexture, StampTexture, WaxTexture  # noqa: E402

CANVAS_W, CANVAS_H = 1200, 1600
SEAL_CELL = 380
PAPER = (245, 240, 232, 255)

FONT_ZH = os.path.join(ROOT, "fonts", "yishanbeizhuanti.ttf")
FONT_JP = os.path.join(ROOT, "fonts", "noto-serif-jp.ttf")
FONT_WZ = os.path.join(ROOT, "fonts", "playfair-display.ttf")


def fail(msg: str):
    print(f"[tracemark] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_font(path: str, size: int):
    try:
        f = ImageFont.truetype(path, size)
        return f
    except Exception as e:
        fail(f"font load failed ({path}): {e}")


def verify_text(text: str, font, label: str):
    """Fail explicitly on tofu/missing glyph — never output a broken product."""
    missing = [ch for ch in text if font.getbbox(ch) is None]
    if missing:
        fail(f"{label}: missing glyph for characters {missing!r}; render aborted")


def zh_layout(text: str, font, cell: int, mode: str):
    """Lay out zhuan characters. zh: columns right->left, top->bottom inside each column.
    4 chars: right col top->bottom, left col top->bottom (standard reading)."""
    n = len(text)
    if n == 1:
        return [(text, 1)]
    if n <= 2:
        return [(text, 1)]  # single column
    if n <= 4:
        cols = 2 if n >= 3 else 1
    else:
        cols = 2
    layout = []
    per = (n + cols - 1) // cols
    for c in range(cols):
        layout.append(text[c * per:(c + 1) * per])
    return layout


GRID_LAYER = None  # cache-free helper uses caller-provided list


def draw_grid(d, cell, mode, color):
    """田字格: white grid on vermilion (zhu mode) or vermilion grid (bai mode).
    Grid is drawn BEFORE texture dry-brush; the seal frame is also drawn separately
    so the outer border never loses segments (dry brush applies to glyph plate only)."""
    lw = max(2, cell // 80)
    if mode == "zhu":
        c = (255, 255, 255, 255)
    else:
        c = color
    d.line([cell // 2, 0, cell // 2, cell], fill=c, width=lw)
    d.line([0, cell // 2, cell, cell // 2], fill=c, width=lw)


def render_zh(cfg: dict):
    style = cfg.get("style", {})
    mode = style.get("mode", "zhu")
    text = cfg["text"]
    seed = cfg.get("seed", 7)
    hexc = style.get("vermilion", "#C8392B")
    color = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))

    font_size = SEAL_CELL // (2 if len(text) <= 2 else 3) - SEAL_CELL // 24
    font = load_font(FONT_ZH, font_size)
    verify_text(text, font, "zh-seal")

    # two-layer composition: frame+grid drawn AFTER texture (crisp),
    # glyph plate textured (organic). This keeps the outer border intact
    # while glyphs and inner grid keep ink character.
    border = max(3, SEAL_CELL // 48)
    inner = SEAL_CELL - border * 2

    # Layer 1: textured glyph plate (smaller square, keeps border gap)
    plate_art = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate_art)
    if mode == "bai":
        pd.rectangle([0, 0, inner - 1, inner - 1], fill=color + (255,))
    if mode == "zhu":
        draw_grid(pd, inner, mode, color)

    layout = zh_layout(text, font, inner, mode)
    cell_unit = (inner - border * 2) // 2
    # traditional reading: first column renders on the RIGHT (right->left)
    for ci, col in enumerate(layout):
        xi = len(layout) - 1 - ci
        x0 = border + xi * cell_unit + (cell_unit - font_size) // 2
        ystep = (inner - border * 2) / (len(col) + 1)
        for ri, ch in enumerate(col):
            y0 = border + int(ystep * (ri + 1)) - font_size // 2
            glyph = Image.new("RGBA", (font_size, font_size), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glyph)
            bbox = font.getbbox(ch)
            fill = color + (255,) if mode == "zhu" else (255, 255, 255, 255)
            gd.text(((font_size - (bbox[2] - bbox[0])) // 2 - bbox[0],
                     (font_size - (bbox[3] - bbox[1])) // 2 - bbox[1]), ch,
                    font=font, fill=fill)
            plate_art.alpha_composite(glyph, (x0, y0))

    tex = SealTexture(seed=seed, uneven=0.08, dry_ratio=0.01)
    plate_inner = tex.apply(plate_art, inner, color)

    # Layer 2: frame + grid crisp on top
    art = Image.new("RGBA", (SEAL_CELL, SEAL_CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    d.rectangle([0, 0, SEAL_CELL - 1, SEAL_CELL - 1], outline=color, width=border)
    art.alpha_composite(plate_inner, (border, border))
    d2 = ImageDraw.Draw(art)
    if mode == "zhu":
        draw_grid(d2, SEAL_CELL, mode, color)
    if mode == "bai":
        draw_grid(d2, SEAL_CELL, mode, (255, 255, 255))
    return art


def render_jp(cfg: dict):
    style = cfg.get("style", {})
    mode = style.get("mode", "red")
    text = cfg["text"]
    seed = cfg.get("seed", 7)
    color = (158, 42, 43, 255) if mode == "red" else (30, 30, 30, 255)

    font_size = SEAL_CELL // 5
    font = load_font(FONT_JP, font_size)
    verify_text(text, font, "jp-stamp")

    art = Image.new("RGBA", (SEAL_CELL, SEAL_CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    r = SEAL_CELL // 2 - 8
    d.ellipse([SEAL_CELL / 2 - r, SEAL_CELL / 2 - r, SEAL_CELL / 2 + r, SEAL_CELL / 2 + r],
              outline=color, width=6)
    r2 = r - 10
    d.ellipse([SEAL_CELL / 2 - r2, SEAL_CELL / 2 - r2, SEAL_CELL / 2 + r2, SEAL_CELL / 2 + r2],
              outline=color, width=2)

    # circular mask so the stamp has no rectangular footprint
    # AND-mask with existing alpha (never turns transparent voids opaque)
    mask = Image.new("L", (SEAL_CELL, SEAL_CELL), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([SEAL_CELL / 2 - r, SEAL_CELL / 2 - r, SEAL_CELL / 2 + r, SEAL_CELL / 2 + r], fill=255)
    existing = art.split()[3]
    na = __import__("numpy")
    combined = na.clip(na.minimum(na.array(mask), na.array(existing)), 0, 255).astype("uint8")
    art.putalpha(Image.fromarray(combined))

    # vertical text along center: distribute over inner diameter
    avail = (r2 * 2) - font_size
    n = len(text)
    ystep = avail / max(1, n)  # n gaps -> last glyph stays inside the ring
    for i, ch in enumerate(text):
        y0 = (SEAL_CELL // 2 - r2) + int(ystep * (i + 0.5)) - font_size // 2
        glyph = Image.new("RGBA", (font_size, font_size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        bbox = font.getbbox(ch)
        gd.text(((font_size - (bbox[2] - bbox[0])) // 2 - bbox[0],
                 (font_size - (bbox[3] - bbox[1])) // 2 - bbox[1]), ch,
                font=font, fill=color)
        art.alpha_composite(glyph, ((SEAL_CELL - font_size) // 2, y0))

    tex = StampTexture(seed=seed, bleed=0.3)
    return tex.apply(art, color)


def render_wz(cfg: dict):
    style = cfg.get("style", {})
    mode = style.get("mode", "crimson")
    text = cfg.get("text", "")
    seed = cfg.get("seed", 7)
    colors = {"crimson": (160, 40, 40), "wine": (90, 28, 42), "gold": (170, 130, 60)}
    base = colors.get(mode, colors["crimson"])

    art = Image.new("RGBA", (SEAL_CELL, SEAL_CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    # organic wax blob edge (near-circle with noise)
    cx, cy, r = SEAL_CELL // 2, SEAL_CELL // 2, SEAL_CELL // 2 - 14
    import random as _random
    import math as _math
    rng = _random.Random(seed)
    pts = []
    n = 240
    for i in range(n):
        ang = 2 * _math.pi * i / n
        rr = r + rng.uniform(-5, 5)
        pts.append((cx + rr * __import__("math").cos(ang), cy + rr * __import__("math").sin(ang)))
    d.polygon(pts, fill=base + (255,))
    # laurel ring approx: small leaf ellipses around
    for i in range(28):
        ang = 2 * 3.14159265 * i / 28
        lx = cx + (r - 42) * __import__("math").cos(ang)
        ly = cy + (r - 42) * __import__("math").sin(ang)
        d.ellipse([lx - 9, ly - 5, lx + 9, ly + 5], outline=(255, 235, 200, 190), width=3)

    # monogram: big letter + small衬字
    font_big = load_font(FONT_WZ, SEAL_CELL // 2)
    font_small = load_font(FONT_WZ, SEAL_CELL // 6)
    big = text[0] if text else "M"
    verify_text(big, font_big, "wz-monogram")
    bbox = font_big.getbbox(big)
    glyph = Image.new("RGBA", ((bbox[2] - bbox[0]) + 30, (bbox[3] - bbox[1]) + 30), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glyph)
    gd.text((15 - bbox[0], 15 - bbox[1]), big, font=font_big, fill=(255, 240, 215, 255))
    art.alpha_composite(glyph, ((SEAL_CELL - glyph.width) // 2, (SEAL_CELL - glyph.height) // 2))
    if len(text) >= 3:
        small = text[1:]
        verify_text(small, font_small, "wz-monogram")
        bbox = font_small.getbbox(small)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        sg = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sg)
        sd.text((5 - bbox[0], 5 - bbox[1]), small, font=font_small, fill=(255, 240, 215, 230))
        art.alpha_composite(sg, ((SEAL_CELL - sg.width) // 2, SEAL_CELL - sg.height - 30))

    tex = WaxTexture(seed=seed)
    return tex.apply(art)


def perforation(canvas: "Image.Image", tooth: int = 22, depth: int = 7):
    """Perforated (stamp) border on all four edges."""
    d = ImageDraw.Draw(canvas)
    w, h = canvas.size
    paper_tone = (250, 246, 238, 255)
    for axis, length in ((0, w), (1, h)):
        for i in range(0, length, tooth * 2):
            if axis == 0:
                d.ellipse([i - depth, -depth, i + depth, depth], fill=paper_tone)
                d.ellipse([i - depth, h - depth, i + depth, h + depth], fill=paper_tone)
            else:
                d.ellipse([-depth, i - depth, depth, i + depth], fill=paper_tone)
                d.ellipse([w - depth, i - depth, w + depth, i + depth], fill=paper_tone)


def micromark(canvas: "Image.Image", text: str = "TRACE·ART"):
    d = ImageDraw.Draw(canvas)
    f = load_font(FONT_WZ, 22)
    bbox = f.getbbox(text)
    d.text((canvas.width - (bbox[2] - bbox[0]) - 24, canvas.height - 48), text,
           font=f, fill=(120, 110, 100, 255))


def render_postcard(cfg: dict, plate: "Image.Image"):
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), PAPER)
    photo_path = cfg.get("photo")
    if photo_path and os.path.exists(photo_path):
        photo = Image.open(photo_path).convert("RGBA")
        # fit photo into upper 62% with inner frame
        pw, ph = int(CANVAS_W * 0.86), int(CANVAS_H * 0.58)
        photo = ImageOps.fit(photo, (pw, ph), Image.LANCZOS)
        canvas.alpha_composite(photo, ((CANVAS_W - pw) // 2, 40))
        # frame rule line
        d = ImageDraw.Draw(canvas)
        d.rectangle([(CANVAS_W - pw) // 2 - 8, 32, (CANVAS_W + pw) // 2 + 8, 40 + ph + 8],
                    outline=(26, 26, 26, 255), width=2)
    # seal plate lower area
    y_seal = int(CANVAS_H * 0.66)
    canvas.alpha_composite(plate, ((CANVAS_W - SEAL_CELL) // 2, y_seal))
    # caption
    cap = cfg.get("caption")
    if cap:
        d = ImageDraw.Draw(canvas)
        f = load_font(FONT_JP, 38)
        bbox = f.getbbox(cap)
        d.text(((CANVAS_W - (bbox[2] - bbox[0])) // 2, y_seal - 84), cap, font=f, fill=(26, 26, 26, 255))
    # date + place (CJK-safe serif)
    f2 = load_font(FONT_JP, 26)
    meta = " ".join(x for x in [cfg.get("place"), cfg.get("date")] if x)
    if meta:
        bbox = f2.getbbox(meta)
        d.text(((CANVAS_W - (bbox[2] - bbox[0])) // 2, y_seal + SEAL_CELL + 36), meta,
               font=f2, fill=(90, 85, 78, 255))
    perforation(canvas)
    micromark(canvas)
    return canvas.convert("RGB")


def render_seal_only(plate: "Image.Image") -> "Image.Image":
    """Seal-only deliverable on paper background."""
    pad = 120
    canvas = Image.new("RGB", (SEAL_CELL + pad * 2, SEAL_CELL + pad * 2), (245, 240, 232))
    canvas.paste(plate.convert("RGB"), (pad, pad), plate)
    return canvas


TRACKS = {"zh": render_zh, "jp": render_jp, "wz": render_wz}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--no-photo", action="store_true", help="seal-only output, no postcard")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    track = cfg.get("track", "zh")
    if track not in TRACKS:
        fail(f"unknown track '{track}'")
    plate = TRACKS[track](cfg)
    if args.no_photo:
        out = render_seal_only(plate)
    else:
        out = render_postcard(cfg, plate)
    out_path = args.out or os.path.splitext(args.config)[0] + ".png"
    out.save(out_path)
    print(f"[tracemark] saved {out_path} ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
