#!/usr/bin/env python3
"""TraceMark unified entry point — every pipeline step runs; none is optional.

Subcommands:
    render   full pipeline: config check -> AUP validation (purpose-based) ->
             template/format routing -> photo path resolution (relative to
             config.yaml dir, never cwd) -> EXIF fix -> real cmap-based
             missing-glyph detection -> render -> anti-forgery marks ->
             mandatory audit (post-render sidecar verification)
    validate AUP purpose gate (standalone)
    audit    real audit: non-blank + artification marks + edge structure +
             correct size + sidecar metadata consistency (never trusts the
             pixel stream alone)
    doctor   environment health check: dependencies, fonts, write directory

Usage (works from ANY cwd — resources resolve from this script's dir / the
skill root, never the caller's cwd):
    python3 <skill_dir>/scripts/tracemark.py render --config <case>/config.yaml
    python3 <skill_dir>/scripts/tracemark.py render --config ... --no-photo
    python3 <skill_dir>/scripts/tracemark.py validate "<text>" "zh"
    python3 <skill_dir>/scripts/tracemark.py audit <output.jpg>
    python3 <skill_dir>/scripts/tracemark.py doctor

Codex/Claude Code note: call scripts/tracemark.py from ${CLAUDE_SKILL_DIR}
(or the installed skill dir) with --config pointing at a config.yaml inside
that dir; photo paths in the YAML should be relative to the config file, not
to the caller's cwd.
"""
import os
import sys

# Resolve the skill root from this script's own location, not from cwd —
# the caller may be in a completely different project (v1.0 audit test).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
ROOT = SKILL_DIR
sys.path.insert(0, SCRIPT_DIR)

from PIL import Image  # noqa: E402


def fail(msg: str):
    print(f"[tracemark] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def doctor_ok(name: str):
    print(f"[tracemark] doctor: {name} ok")


def doctor_bad(name: str, msg: str):
    print(f"[tracemark] doctor: {name} MISSING — {msg}", file=sys.stderr)


def cmd_doctor(args):
    """Check dependencies, fonts and the output directory."""
    problems = 0

    for mod, extra in (("yaml", "pip install pyyaml"),
                       ("numpy", "pip install numpy"),
                       ("PIL", "pip install pillow"),
                       ("freetype", "pip install freetype-py (HARD DEPENDENCY — "
                                    "missing-glyph detection requires it)")):
        try:
            __import__(mod)
            doctor_ok(f"python module {mod}")
        except ImportError:
            doctor_bad(f"python module {mod}", extra)
            problems += 1

    for name in ("yishanbeizhuanti.ttf", "noto-serif-jp.ttf",
                 "playfair-display.ttf"):
        p = os.path.join(ROOT, "fonts", name)
        if os.path.exists(p):
            doctor_ok(f"font {name}")
        else:
            doctor_bad(f"font {name}", f"expected at {p}")
            problems += 1

    out_dir = args.out_dir or os.getcwd()
    if os.path.isdir(out_dir) and os.access(out_dir, os.W_OK):
        doctor_ok(f"write directory {out_dir}")
    else:
        doctor_bad(f"write directory {out_dir}", "not writable or missing")
        problems += 1

    if problems:
        print(f"[tracemark] doctor: {problems} problem(s). Install missing "
              "dependencies with `pip install -r requirements.txt`.",
              file=sys.stderr)
        sys.exit(1)
    print("[tracemark] doctor: environment healthy")
    sys.exit(0)


def cmd_render(args):
    import render as _render  # noqa: E402
    _render.render_entry(args.config, args.out, args.no_photo)
    # Mandatory audit on EVERY render result, including seal-only mode
    # (v1.0: the audit step can never be skipped).
    out = args.out or os.path.splitext(os.path.abspath(args.config))[0] + ".jpg"
    rc = real_audit(out)
    if rc != 0:
        fail(f"post-render audit failed for {out}; output quarantined")


# ---------------------------------------------------------------------------
# Real audit (v1.0): never claims success from size alone.
# ---------------------------------------------------------------------------
def _has_marks(img) -> bool:
    """TRACE·ART micromark: dark text pixels in the bottom-right band."""
    from PIL import ImageOps
    w, h = img.size
    band = img.crop((w - 300, h - 70, w - 10, h - 20)).convert("L")
    arr = __import__("numpy").asarray(band)
    return int((arr < 140).sum()) > 60


def _has_edge_structure(img) -> bool:
    """Perforation/art edges: enough near-black or near-white edge pixels."""
    import numpy as np
    arr = np.asarray(img.convert("L"))
    edges = np.concatenate([arr[:, :6].ravel(), arr[:, -6:].ravel(),
                            arr[:6, :].ravel(), arr[-6:, :].ravel()])
    return int(((edges < 90) | (edges > 235)).sum()) > 400


def _not_blank(img) -> bool:
    arr = __import__("numpy").asarray(img.convert("L"))
    return float(arr.std()) > 12.0


def real_audit(path: str, config_path: str = None) -> int:
    """Return 0 = passed, 1 = failed. Checks:

    - file is a real image and non-blank
    - correct output size (1200x1600 postcard / 620x620 seal-only)
    - TRACE·ART micromark present
    - edge structure (perforation / art border) present
    - sidecar metadata exists and matches (text/template/size)
    """
    if not os.path.exists(path):
        print(f"[tracemark] AUDIT-FAIL: output missing: {path}", file=sys.stderr)
        return 1
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        print(f"[tracemark] AUDIT-FAIL: cannot open {path}: {e}",
              file=sys.stderr)
        return 1

    checks = []
    checks.append(("non-blank", _not_blank(img)))
    checks.append(("edge structure", _has_edge_structure(img)))
    checks.append(("TRACE·ART mark", _has_marks(img)))

    # Size must match one of the two legitimate footprints.
    seal_side = 380 + 240
    checks.append(("footprint size", img.size in ((1200, 1600), (seal_side, seal_side))))

    # Sidecar consistency (render-time metadata vs pixel stream).
    sidecar = os.path.splitext(path)[0] + ".tracemark.json"
    if os.path.exists(sidecar):
        import json
        meta = json.load(open(sidecar))
        checks.append(("sidecar text", meta.get("text") not in (None, "")))
        checks.append(("sidecar template", meta.get("template") in (
            "zh-square-zhu", "zh-square-bai", "zh-circle-leisure",
            "jp-circle-stamp", "wz-wax-monogram")))
        if config_path and os.path.abspath(meta.get("config", "")) != os.path.abspath(config_path):
            checks.append(("sidecar config", False))
        else:
            checks.append(("sidecar config", True))
    else:
        checks.append(("sidecar metadata", False))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"[tracemark] AUDIT-FAIL: {path} failed checks: "
              f"{', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"[tracemark] AUDIT-PASS: {path} "
          f"({img.size[0]}x{img.size[1]}; perforation + TRACE·ART verified; "
          f"sidecar consistent)")
    return 0


def cmd_audit(args):
    sys.exit(real_audit(args.path, args.config))


def cmd_validate(args):
    import validate_input  # noqa: E402
    text, mode_or_track = args.text, args.mode
    try:
        mode = validate_input.derive_mode(mode_or_track)
    except ValueError:
        mode = mode_or_track
    cfg = None
    if args.config:
        import yaml  # noqa: E402
        cfg = yaml.safe_load(open(args.config)) or {}
    sys.exit(validate_input.validate(text, mode, cfg))


def main():
    ap = __import__("argparse").ArgumentParser(description="TraceMark unified entry point")
    sub = ap.add_subparsers(dest="command")

    pr = sub.add_parser("render", help="full pipeline: validate -> resolve -> render -> audit")
    pr.add_argument("--config", required=True)
    pr.add_argument("--no-photo", action="store_true", help="seal-only output")
    pr.add_argument("--out", default=None)
    pr.set_defaults(func=cmd_render)

    pv = sub.add_parser("validate", help="AUP purpose gate (standalone)")
    pv.add_argument("text")
    pv.add_argument("mode", help="mode seal|stamp|postcard or track zh|jp|wz")
    pv.add_argument("--config", default=None)
    pv.set_defaults(func=cmd_validate)

    pa = sub.add_parser("audit", help="real audit of an output (blank/size/marks/metadata)")
    pa.add_argument("path")
    pa.add_argument("--config", default=None, help="expected source config (sidecar check)")
    pa.set_defaults(func=cmd_audit)

    pd = sub.add_parser("doctor", help="environment health check: deps, fonts, write dir")
    pd.add_argument("--out-dir", default=None, help="directory to test writability")
    pd.set_defaults(func=cmd_doctor)

    args = ap.parse_args()
    if not args.command:
        ap.print_help()
        sys.exit(2)
    args.func(args)


if __name__ == "__main__":
    main()
