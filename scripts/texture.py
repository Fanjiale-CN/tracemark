#!/usr/bin/env python3
"""TraceMark texture engine — cultural ink/relief artifacts.

Three texture families, one API:
- `zh`   钤印肌理: ink unevenness + random rotation/offset + dry-brush "飞白"
- `jp`   墨晕: soft edge bleed (ink spreading at borders)
- `wz`   蜡质浮雕: raised relief via drop-shadow + highlight layering

All random seeds are explicit -> reproducible (needed by the examples test suite).

Usage:
    from texture import SealTexture, StampTexture, WaxTexture
    canvas = seal.apply(overlay_rgba)  # overlay_rgba: seal art as RGBA image
"""
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

CANVAS_W, CANVAS_H = 1200, 1600


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _fractal_noise(size: int, seed: int, octaves: int = 3) -> "Image.Image":
    """Diamond-ish noise approximated by layered blurred random squares."""
    rng = _rng(seed)
    base = Image.new("L", (1, 1))
    base = base.resize((size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            px[x, y] = rng.randint(0, 255)
    noise = Image.new("L", (size, size), 0)
    amp, freq = 128.0, 1.0
    for _ in range(octaves):
        cell = int(size * freq)
        cell = max(2, cell)
        rnd = Image.new("L", (cell, cell))
        px2 = rnd.load()
        for y in range(cell):
            for x in range(cell):
                px2[x, y] = rng.randint(0, 255)
        rnd = rnd.resize((size, size)).filter(ImageFilter.GaussianBlur(radius=max(1, int(size / cell / 2))))
        noise = Image.fromarray(
            np.clip(
                np.array(noise).astype(float) + amp * (np.array(rnd).astype(float) - 128) / 128,
                0, 255,
            ).astype("uint8"))
        amp /= 2.0
        freq *= 2.0
    return noise


class SealTexture:
    """Chinese zhuan seal: rotation/offset/ink unevenness/dry-brush."""

    def __init__(self, seed: int, uneven: float = 0.15, dry_ratio: float = 0.05,
                 rotation: float = 1.5, offset: float = 3.0):
        self.seed = seed
        self.uneven = uneven
        self.dry_ratio = dry_ratio
        self.rotation = rotation
        self.offset = offset

    def apply(self, seal: "Image.Image", cell: int, color: tuple) -> "Image.Image":
        rng = _rng(self.seed)
        art = seal.convert("RGBA")
        # rotate & offset (imperfection semantics)
        rot = rng.uniform(-self.rotation, self.rotation)
        art = art.rotate(rot, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
        dx = rng.uniform(-self.offset, self.offset)
        dy = rng.uniform(-self.offset, self.offset)
        art = art.crop((int(self.offset), int(self.offset),
                        art.width - int(self.offset), art.height - int(self.offset)))
        # ink unevenness: multiply alpha by noise
        alpha = art.split()[3]
        noise = _fractal_noise(cell, self.seed + 1).resize((alpha.width, alpha.height))
        new_alpha = np.clip(
            np.array(alpha).astype(float) * (1.0 - self.uneven + self.uneven * np.array(noise).astype(float) / 255.0),
            0, 255,
        ).astype("uint8")
        art.putalpha(Image.fromarray(new_alpha))
        # dry-brush "飞白": erase random thin rects
        if self.dry_ratio > 0:
            erase = Image.new("L", art.size, 255)
            edx = erase.load()
            n_pix = int(art.width * art.height * self.dry_ratio)
            for _ in range(max(1, n_pix // 40)):
                x0 = rng.randint(0, max(1, art.width - 1))
                y0 = rng.randint(0, max(1, art.height - 1))
                w = rng.randint(2, max(3, art.width // 10))
                h = rng.randint(2, max(3, art.height // 25))
                d = ImageDraw.Draw(erase)
                d.rectangle([x0, y0, x0 + w, y0 + h], fill=0)
            alpha2 = np.clip(
                np.array(art.split()[3]).astype(float) * (np.array(erase).astype(float) / 255.0),
                0, 255,
            ).astype("uint8")
            art.putalpha(Image.fromarray(alpha2))
        # colorize
        color_layer = Image.new("RGBA", art.size, color + (0,))
        color_layer.putalpha(art.split()[3])
        return color_layer


class StampTexture:
    """Japanese craft stamp: ink bleed at edges."""

    def __init__(self, seed: int, bleed: float = 0.5):
        self.seed = seed
        self.bleed = bleed

    def apply(self, stamp: "Image.Image", color: tuple) -> "Image.Image":
        rng = _rng(self.seed)
        art = stamp.convert("RGBA")
        # ink bleed semantics: only the EDGE band (partially transparent pixels)
        # spreads outward; fully opaque art stays opaque, fully transparent stays void.
        alpha = art.split()[3]
        soft = alpha.filter(ImageFilter.GaussianBlur(radius=1.8))
        a = np.array(soft).astype(float)
        # lift only the semi-transparent band (20..235) toward opaque
        band = np.clip((a - 20.0) / (235.0 - 20.0), 0, 1)
        lifted = a + (255.0 - a) * self.bleed * band * ((255.0 - a) / 255.0)
        a = np.clip(lifted, 0, 255).astype("uint8")
        art.putalpha(Image.fromarray(a))
        rgba = (int(color[0]), int(color[1]), int(color[2]), 0)
        color_layer = Image.new("RGBA", art.size, rgba)
        color_layer.putalpha(art.split()[3])
        return color_layer


class WaxTexture:
    """Western wax seal: raised relief via shadow + highlight layers."""

    def __init__(self, seed: int, relief: int = 8, highlight: int = 3, light_angle_deg: float = 315.0):
        self.seed = seed
        self.relief = relief
        self.highlight = highlight
        self.light_angle_deg = light_angle_deg

    def apply(self, wax: "Image.Image") -> "Image.Image":
        """`wax`: flat RGBA relief art. Returns RGBA with faux 3D relief."""
        alpha = wax.split()[3].convert("L")
        # emboss alpha -> relief displacement maps
        na = np.array(alpha).astype(float) / 255.0
        ang = math.radians(self.light_angle_deg)
        dx = int(round(self.relief * math.cos(ang)))
        dy = int(round(self.relief * math.sin(ang)))
        shadow = alpha.transform(alpha.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy)).filter(ImageFilter.GaussianBlur(radius=2.0))
        highlight = alpha.transform(alpha.size, Image.AFFINE, (1, 0, dx // 2, 0, 1, dy // 2)).filter(ImageFilter.GaussianBlur(radius=1.0))
        base = wax.convert("RGBA")
        # darken where shadow falls, lighten on highlight
        r, g, b, a0 = base.split()
        sh = np.array(shadow).astype(float)
        hl = np.array(highlight).astype(float)
        rr = np.clip(np.array(r).astype(float) - sh * 0.35 + hl * 0.45, 0, 255).astype("uint8")
        gg = np.clip(np.array(g).astype(float) - sh * 0.35 + hl * 0.45, 0, 255).astype("uint8")
        bb = np.clip(np.array(b).astype(float) - sh * 0.35 + hl * 0.45, 0, 255).astype("uint8")
        out = Image.merge("RGBA", (Image.fromarray(rr), Image.fromarray(gg), Image.fromarray(bb), a0))
        return out
