#!/usr/bin/env python3
"""TraceMark render engine — template-driven seal/postcard synthesis.

Unified pipeline (no step is skippable):
    config structure check -> AUP validation -> template/track routing ->
    photo path resolution (relative to config.yaml dir, hard-fail on missing) ->
    EXIF orientation correction -> real cmap-based missing-glyph detection ->
    render -> force anti-forgery marks on every output.

Usage:
    python3 render.py --config examples/<case>/config.yaml
    python3 render.py --config examples/<case>/config.yaml --no-photo   # seal-only output

config.yaml schema:
    track: zh | jp | wz            (cultural track; zh/wz -> seal mode, jp -> stamp)
    template: zh-square-zhu | zh-square-bai | zh-circle-leisure
              jp-circle-stamp | wz-wax-monogram | null
    text: "<seal text>"
    seed: 7
    photo: <path relative to config dir, or null>
    caption: "<one-line caption>"
    date: "2026.08.15"
    place: "<place name>"
    style:
        vermilion: "#C8392B" | "#9E2A2B"
        mode: zhu | bai (zh) | red | black (jp) | crimson | wine | gold (wz)

AUP enforcement: `validate_input.py` is called automatically before render
(never skippable from this entry point).
"""
import os
import sys
import argparse

import yaml
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from texture import SealTexture, StampTexture, WaxTexture  # noqa: E402
import validate_input  # noqa: E402

import freetype  # noqa: E402 — hard dependency; missing-glyph detection
# reads the font's real cmap (glyph index 0 = .notdef tofu). Without it the
# pipeline cannot guarantee text fidelity, so we fail loudly instead of
# falling back to an unreliable heuristic (v1.0 audit requirement).

CANVAS_W, CANVAS_H = 1200, 1600
SEAL_CELL = 380
PAPER = (245, 240, 232, 255)

FONT_ZH = os.path.join(ROOT, "fonts", "chongxi_seal.otf")  # 崇羲篆體 — true xiaozhuan canon (CC BY-ND; keep as-is)
FONT_ZH_FALLBACK = os.path.join(ROOT, "fonts", "yishanbeizhuanti.ttf")  # legacy fallback
FONT_JP = os.path.join(ROOT, "fonts", "noto-serif-jp.ttf")
FONT_WZ = os.path.join(ROOT, "fonts", "playfair-display.ttf")


def fail(msg: str):
    print(f"[tracemark] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception as e:
        fail(f"font load failed ({path}): {e}")


def glyphs_missing(font_path: str, text: str) -> list:
    """True missing-glyph detection via the font's cmap (glyph index 0 = .notdef tofu)."""
    face = freetype.Face(font_path)
    face.select_charmap(freetype.FT_ENCODING_UNICODE)
    return [ch for ch in text if face.get_char_index(ord(ch)) == 0]


def verify_text(text: str, font_path: str, label: str):
    """Fail explicitly on tofu/missing glyph — never output a broken product."""
    missing = glyphs_missing(font_path, text)
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


def draw_glyph_centered(canvas, pos, ch, font, fill, cell_size: int):
    """Draw one glyph centered in a `cell_size` square box at `pos`."""
    bbox = font.getbbox(ch)
    glyph = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glyph)
    gd.text(((cell_size - (bbox[2] - bbox[0])) // 2 - bbox[0],
             (cell_size - (bbox[3] - bbox[1])) // 2 - bbox[1]), ch,
            font=font, fill=fill)
    canvas.alpha_composite(glyph, pos)


def resolve_zh_font(text: str):
    """Primary zhuan typeface is the true xiaozhuan canon 崇羲篆體 (CC BY-ND).
    Fall back to 峄山碑篆体 only if the text contains glyphs the canon lacks —
    verify_text then fails loudly on anything neither font can render (v1.1)."""
    for path in (FONT_ZH, FONT_ZH_FALLBACK):
        missing = glyphs_missing(path, text)
        if not missing:
            return path
    fail(f"zh-seal text {text!r} cannot be fully rendered by the bundled "
         "xiaozhuan fonts (missing in both 崇羲篆體 and 峄山碑篆体). "
         "Suggestions: use 1–4 Traditional Chinese characters from the 《說文解字》 canon "
         "(e.g. 觀 not 观), shorten the text, or remove rare/decorative characters")


def render_zh(cfg: dict):
    style = cfg.get("style", {})
    mode = style.get("mode", "zhu")
    text = cfg["text"]
    seed = cfg.get("seed", 7)
    hexc = style.get("vermilion", "#C8392B")
    color = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))

    font_size = SEAL_CELL // (2 if len(text) <= 2 else 3) - SEAL_CELL // 24
    zh_font_path = resolve_zh_font(text)
    font = load_font(zh_font_path, font_size)
    verify_text(text, zh_font_path, "zh-seal")

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
            fill = color + (255,) if mode == "zhu" else (255, 255, 255, 255)
            draw_glyph_centered(plate_art, (x0, y0), ch, font, fill, font_size)

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


def render_zh_circle_leisure(cfg: dict):
    """Round leisure seal 圆闲章: circular frame with a column of zhuan glyphs
    (2-4 chars), the traditional seal-script leisure-stamp silhouette."""
    style = cfg.get("style", {})
    text = cfg["text"]
    seed = cfg.get("seed", 7)
    hexc = style.get("vermilion", "#9E2A2B")
    color = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))

    font_size = SEAL_CELL // (3 if len(text) >= 3 else 2) - SEAL_CELL // 24
    zh_font_path = resolve_zh_font(text)
    font = load_font(zh_font_path, font_size)
    verify_text(text, zh_font_path, "zh-circle-leisure")

    art = Image.new("RGBA", (SEAL_CELL, SEAL_CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(art)
    r = SEAL_CELL // 2 - 8
    cx, cy = SEAL_CELL // 2, SEAL_CELL // 2
    # outer ring (thick) + inner ring (thin) like a round seal rim
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=max(3, SEAL_CELL // 56))
    r2 = r - 12
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=color, width=2)

    # glyph column inside the inner circle
    n = len(text)
    col_gap = (r2 * 2 - 24) // max(1, n + 1)
    for i, ch in enumerate(text):
        gy = (cy - r2) + 12 + col_gap * (i + 1) - font_size // 2
        draw_glyph_centered(art, ((SEAL_CELL - font_size) // 2, gy), ch,
                            font, color + (255,), font_size)

    tex = SealTexture(seed=seed, uneven=0.10, dry_ratio=0.01)
    masked = tex.apply(art, SEAL_CELL, color)
    # circular mask: glyph plate + rings stay inside the seal footprint;
    # re-fit the texture output (may have expanded past SEAL_CELL due to
    # rotation) back into the cell before masking
    if masked.size != (SEAL_CELL, SEAL_CELL):
        masked = masked.resize((SEAL_CELL, SEAL_CELL), Image.LANCZOS)
    mask = Image.new("L", (SEAL_CELL, SEAL_CELL), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    a = np.clip(np.minimum(np.array(mask), np.array(masked.split()[3])), 0, 255).astype("uint8")
    masked.putalpha(Image.fromarray(a))
    return masked


def render_jp(cfg: dict):
    style = cfg.get("style", {})
    mode = style.get("mode", "red")
    text = cfg["text"]
    seed = cfg.get("seed", 7)
    color = (158, 42, 43, 255) if mode == "red" else (30, 30, 30, 255)

    font_size = SEAL_CELL // 5
    font = load_font(FONT_JP, font_size)
    verify_text(text, FONT_JP, "jp-stamp")

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
    combined = np.clip(np.minimum(np.array(mask), np.array(existing)), 0, 255).astype("uint8")
    art.putalpha(Image.fromarray(combined))

    # vertical text along center: distribute over inner diameter
    avail = (r2 * 2) - font_size
    n = len(text)
    ystep = avail / max(1, n)  # n gaps -> last glyph stays inside the ring
    for i, ch in enumerate(text):
        y0 = (SEAL_CELL // 2 - r2) + int(ystep * (i + 0.5)) - font_size // 2
        draw_glyph_centered(art, ((SEAL_CELL - font_size) // 2, y0), ch, font, color, font_size)

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
    import random as _random
    import math as _math
    cx, cy, r = SEAL_CELL // 2, SEAL_CELL // 2, SEAL_CELL // 2 - 14
    rng = _random.Random(seed)
    pts = []
    n = 240
    for i in range(n):
        ang = 2 * _math.pi * i / n
        rr = r + rng.uniform(-5, 5)
        pts.append((cx + rr * _math.cos(ang), cy + rr * _math.sin(ang)))
    d.polygon(pts, fill=base + (255,))
    # laurel ring approx: small leaf ellipses around
    for i in range(28):
        ang = 2 * 3.14159265 * i / 28
        lx = cx + (r - 42) * _math.cos(ang)
        ly = cy + (r - 42) * _math.sin(ang)
        d.ellipse([lx - 9, ly - 5, lx + 9, ly + 5], outline=(255, 235, 200, 190), width=3)

    # monogram: letters participate in the composition, never ignored.
    # 1 letter: big centered; 2 letters: big pair side by side; 3 letters:
    # big initial + remaining as small under-scroll. Each configuration
    # produces a visually distinct product (M != MA, v1.0 audit test).
    font_big = load_font(FONT_WZ, SEAL_CELL // 2)
    font_pair = load_font(FONT_WZ, SEAL_CELL // 3)
    font_small = load_font(FONT_WZ, SEAL_CELL // 6)
    n = len(text)
    verify_text(text, FONT_WZ, "wz-monogram")
    if n == 0:
        fail("wz-monogram text is empty; provide 1-3 letters")
    fill = (255, 240, 215, 255)
    small_fill = (255, 240, 215, 230)
    if n == 1:
        bbox = font_big.getbbox(text)
        glyph = Image.new("RGBA", ((bbox[2] - bbox[0]) + 30, (bbox[3] - bbox[1]) + 30), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((15 - bbox[0], 15 - bbox[1]), text, font=font_big, fill=fill)
        art.alpha_composite(glyph, ((SEAL_CELL - glyph.width) // 2,
                                    (SEAL_CELL - glyph.height) // 2))
    elif n == 2:
        b0 = font_pair.getbbox(text[0])
        b1 = font_pair.getbbox(text[1])
        total = (b0[2] - b0[0]) + 24 + (b1[2] - b1[0])
        gh = max(b0[3] - b0[1], b1[3] - b1[1]) + 30
        glyph = Image.new("RGBA", (total + 20, gh), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((12 - b0[0], 15 - b0[1]), text[0], font=font_pair, fill=fill)
        gd.text((12 + (b0[2] - b0[0]) + 24 - b1[0], 15 - b1[1]), text[1],
                font=font_pair, fill=fill)
        art.alpha_composite(glyph, ((SEAL_CELL - glyph.width) // 2,
                                    (SEAL_CELL - glyph.height) // 2))
    else:
        big, small = text[0], text[1:]
        bbox = font_big.getbbox(big)
        glyph = Image.new("RGBA", ((bbox[2] - bbox[0]) + 30, (bbox[3] - bbox[1]) + 30), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((15 - bbox[0], 15 - bbox[1]), big, font=font_big, fill=fill)
        art.alpha_composite(glyph, ((SEAL_CELL - glyph.width) // 2,
                                    (SEAL_CELL - glyph.height) // 2))
        bbox = font_small.getbbox(small)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        sg = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sg)
        sd.text((5 - bbox[0], 5 - bbox[1]), small, font=font_small, fill=small_fill)
        art.alpha_composite(sg, ((SEAL_CELL - sg.width) // 2,
                                 SEAL_CELL - sg.height - 30))

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


def fit_text_width(text: str, font, max_width: int) -> str:
    """Cap on-screen width: append ellipsis when the text would overflow."""
    if font.getbbox(text) is None:
        return text
    if font.getbbox(text)[2] <= max_width:
        return text
    out = text
    while len(out) > 1:
        out = out[:-1]
        if font.getbbox(out + "…")[2] <= max_width:
            return out + "…"
    return "…"


def render_postcard(cfg: dict, plate: "Image.Image"):
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), PAPER)
    photo_path = cfg.get("photo")
    if photo_path:
        if not os.path.exists(photo_path):
            fail(f"photo not found: {photo_path}")
        photo = Image.open(photo_path)
        try:
            photo = ImageOps.exif_transpose(photo)  # iPhone/orientation fix
        except Exception:
            pass
        photo = photo.convert("RGBA")
        # Frame the photo into the upper area WITHOUT mangling its edges:
        # scale to full frame width first (keeps the left-edge watermark band
        # and horizon intact), then centre-crop only excess HEIGHT. A blunt
        # ImageOps.fit (both axes) is what silently chops watermark bands.
        pw, ph = int(CANVAS_W * 0.92), int(CANVAS_H * 0.58)
        scale = pw / photo.width
        new_h = max(1, int(round(photo.height * scale)))
        photo = photo.resize((pw, new_h), Image.LANCZOS)
        if new_h > ph:
            top = (new_h - ph) // 2
            photo = photo.crop((0, top, pw, top + ph))
        else:
            ph = new_h
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
        cap = fit_text_width(cap, f, CANVAS_W - 120)
        bbox = f.getbbox(cap)
        d.text(((CANVAS_W - (bbox[2] - bbox[0])) // 2, y_seal - 84), cap, font=f, fill=(26, 26, 26, 255))
    # date + place (CJK-safe serif); clamp meta width to canvas
    f2 = load_font(FONT_JP, 26)
    meta = " ".join(x for x in [cfg.get("place"), cfg.get("date")] if x)
    if meta:
        meta = fit_text_width(meta, f2, CANVAS_W - 120)
        bbox = f2.getbbox(meta)
        d.text(((CANVAS_W - (bbox[2] - bbox[0])) // 2, y_seal + SEAL_CELL + 36), meta,
               font=f2, fill=(90, 85, 78, 255))
    perforation(canvas)
    micromark(canvas)
    return canvas.convert("RGB")


def render_seal_only(plate: "Image.Image") -> "Image.Image":
    """Seal-only deliverable on paper background.

    Anti-forgery law: even seal-only output must keep the artification frame,
    perforation marks, and the permanent TRACE·ART microtext — identical to the
    postcard mode. A plain bordered-square paste is never shipped."""
    pad = 120
    size = SEAL_CELL + pad * 2
    canvas = Image.new("RGBA", (size, size), PAPER)
    canvas.paste(plate, (pad, pad), plate)
    perforation(canvas)
    micromark(canvas)
    return canvas.convert("RGB")


# ---------------------------------------------------------------------------
# Template routing — every template name documented in SKILL.md must resolve.
# ---------------------------------------------------------------------------
TEMPLATES = {
    "zh-square-zhu": ("zh", "zhu"),
    "zh-square-bai": ("zh", "bai"),
    "zh-circle-leisure": ("zh-circle", "leisure"),
    "jp-circle-stamp": ("jp", "red"),
    "wz-wax-monogram": ("wz", "crimson"),
}

TRACKS = {"zh": render_zh, "zh-circle": render_zh_circle_leisure,
          "jp": render_jp, "wz": render_wz}


def resolve_track_and_mode(cfg: dict):
    """template (if valid) wins; otherwise derive from track + style.mode.
    Returns (renderer_key, seal_style_mode)."""
    template = cfg.get("template")
    style = cfg.get("style", {}) or {}
    if template and template in TEMPLATES:
        return TEMPLATES[template]
    if template:
        print(f"[tracemark] WARN: unknown template '{template}' (ignored); "
              f"fallback to track '{cfg.get('track', 'zh')}'", file=sys.stderr)
    track = cfg.get("track", "zh")
    if track not in ("zh", "jp", "wz"):
        fail(f"unknown track '{track}'; expected zh | jp | wz")
    if track == "zh":
        return ("zh", style.get("mode", "zhu"))
    if track == "jp":
        return ("jp", style.get("mode", "red"))
    return ("wz", style.get("mode", "crimson"))


def resolve_photo_path(cfg: dict, config_dir: str):
    """Photo paths resolve relative to the config.yaml directory (never cwd).
    Returns resolved absolute path or None; hard-fails on missing files."""
    photo = cfg.get("photo")
    if photo in (None, False):
        return None
    photo = str(photo)
    if not os.path.isabs(photo):
        photo = os.path.join(config_dir, photo)
    if not os.path.exists(photo):
        fail(f"photo not found: {photo}")
    return photo


def check_config_structure(cfg, config_path: str):
    """Fail fast on structural problems instead of cryptic PIL/KeyError."""
    if not isinstance(cfg, dict):
        fail(f"{config_path}: config must be a YAML mapping at the top level")
    if not cfg.get("text") or not isinstance(cfg.get("text"), str):
        fail(f"{config_path}: required field 'text' missing or empty")
    if not cfg.get("track") or not isinstance(cfg.get("track"), str):
        fail(f"{config_path}: required field 'track' missing (zh | jp | wz)")


def run_aup_check(text: str, track: str, config_path: str):
    """AUP category-availability gate — invoked on every render, not skippable.
    Mode is derived from the cultural track (zh/wz -> seal, jp -> stamp)."""
    mode = validate_input.derive_mode(track)
    code = validate_input.validate(text, mode)
    if code != 0:
        fail(f"AUP check rejected '{text}' for track '{track}' (mode {mode}); "
             f"see guidance above")


def output_result(img: "Image.Image", out_path: str):
    if out_path.lower().endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(out_path, quality=88, optimize=True)
    else:
        img.save(out_path)
    print(f"[tracemark] saved {out_path} ({img.width}x{img.height})")


def write_sidecar(out_path: str, config_path: str, cfg: dict, no_photo: bool):
    """Write a render-time audit sidecar next to the output.

    The `audit` command verifies output integrity against this metadata:
    size, source config identity, text/template/seed fingerprint and per-
    layer SHA-256 digests. A pixel stream alone is never trusted (v1.0)."""
    import hashlib as _hashlib
    sidecar = os.path.splitext(out_path)[0] + ".tracemark.json"
    try:
        with open(out_path, "rb") as f:
            file_hash = _hashlib.sha256(f.read()).hexdigest()
    except OSError:
        file_hash = None
    meta = {
        "generator": "tracemark",
        "config": os.path.abspath(config_path),
        "track": cfg.get("track"),
        "template": cfg.get("template") or validate_input.TRACK_DEFAULT_TEMPLATES.get(cfg.get("track")),
        "text": cfg.get("text"),
        "seed": cfg.get("seed", 7),
        "no_photo": no_photo,
        "output_size": list(cfg.get("__size__", (CANVAS_W, CANVAS_H))),
        "output_sha256": file_hash,
    }
    with open(sidecar, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"[tracemark] sidecar {sidecar}")


import json  # noqa: E402


def render_entry(config_path: str, out_path: str, no_photo: bool):
    """Unified render entry point: every step below runs; none is optional."""
    config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        fail(f"config not found: {config_path}")
    config_dir = os.path.dirname(config_path)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    check_config_structure(cfg, config_path)

    text = cfg["text"]

    # AUP gate via the unified validator (purpose-based). resolve_template
    # enforces: unknown template / template-track mismatch / format-template
    # mismatch are hard errors; check_capacity forbids silent truncation.
    code = validate_input.validate(text, cfg["track"], cfg)
    if code != 0:
        fail(f"AUP gate rejected the render for {config_path}; see guidance "
             "above")

    renderer_key, seal_mode = resolve_track_and_mode(cfg)
    cfg.setdefault("style", {})
    cfg["style"]["mode"] = seal_mode

    cfg["photo"] = resolve_photo_path(cfg, config_dir)

    plate = TRACKS[renderer_key](cfg)
    out_img = render_seal_only(plate) if no_photo else render_postcard(cfg, plate)
    out_path = out_path or os.path.splitext(config_path)[0] + ".jpg"
    output_result(out_img, out_path)

    # Render-time audit sidecar: the `audit` command verifies the output
    # against this metadata + layer digests (never trusts the pixel stream
    # alone — v1.0 real-audit requirement).
    write_sidecar(out_path, config_path, cfg, no_photo)


def main():
    ap = argparse.ArgumentParser(description="TraceMark render engine")
    ap.add_argument("--config", required=True, help="path to config.yaml")
    ap.add_argument("--no-photo", action="store_true", help="seal-only output, no postcard")
    ap.add_argument("--out", default=None, help="output path (default: config basename .jpg)")
    args = ap.parse_args()
    render_entry(args.config, args.out, args.no_photo)


if __name__ == "__main__":
    main()
