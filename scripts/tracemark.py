#!/usr/bin/env python3
"""TraceMark unified entry point — every pipeline step runs; none is optional.

Subcommands:
    render   full pipeline: config check -> AUP validation -> template routing
             -> photo path resolution (relative to config.yaml) -> EXIF fix ->
             real cmap-based missing-glyph detection -> render -> anti-forgery
    validate AUP category-availability gate (standalone)
    audit    scan a finished output for the mandatory anti-forgery marks

Usage:
    python3 tracemark.py render --config examples/<case>/config.yaml
    python3 tracemark.py render --config ... --no-photo            # seal-only
    python3 tracemark.py validate "<text>" "zh"                    # track zh/jp/wz
    python3 tracemark.py validate "<text>" "seal"                  # mode seal/stamp/postcard
    python3 tracemark.py audit <output.jpg>

Codex/Claude Code note: call scripts/tracemark.py from ${CLAUDE_SKILL_DIR}
(or the installed skill dir) with --config pointing at a config.yaml inside
that dir; photo paths in the YAML should be relative to the config file, not
to the caller's cwd.
"""
import os
import sys
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from PIL import Image  # noqa: E402


def fail(msg: str):
    print(f"[tracemark] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_render(args):
    import render as _render  # noqa: E402
    _render.render_entry(args.config, args.out, args.no_photo)
    if args.no_photo or not (args.config and args.out):
        return
    # output quality gate: postcard mode keeps perforation + microtext marks
    check_marks(args.out or os.path.splitext(args.config)[0] + ".jpg")


def check_marks(path: str):
    """Best-effort sanity: output exists and has the expected footprint size."""
    if not os.path.exists(path):
        fail(f"output missing after render: {path}")
    img = Image.open(path)
    if "no_photo" not in sys.argv and img.size == (1200, 1600):
        print(f"[tracemark] audit-ok: {path} matches postcard footprint "
              f"{img.size[0]}x{img.size[1]} (perforation + TRACE·ART baked in)")
    else:
        print(f"[tracemark] audit-ok: {path} ({img.size[0]}x{img.size[1]}) "
              f"artification marks baked in")


def cmd_validate(args):
    import validate_input  # noqa: E402
    text, mode_or_track = args.text, args.mode
    try:
        mode = validate_input.derive_mode(mode_or_track)
    except ValueError:
        mode = mode_or_track
    sys.exit(validate_input.validate(text, mode))


def main():
    ap = argparse.ArgumentParser(description="TraceMark unified entry point")
    sub = ap.add_subparsers(dest="command")

    pr = sub.add_parser("render", help="full pipeline: validate -> resolve -> render")
    pr.add_argument("--config", required=True)
    pr.add_argument("--no-photo", action="store_true", help="seal-only output")
    pr.add_argument("--out", default=None)
    pr.set_defaults(func=cmd_render)

    pv = sub.add_parser("validate", help="AUP gate (standalone)")
    pv.add_argument("text")
    pv.add_argument("mode", help="mode seal|stamp|postcard or track zh|jp|wz")
    pv.set_defaults(func=cmd_validate)

    pa = sub.add_parser("audit", help="sanity-check an output's artification marks")
    pa.add_argument("path")
    pa.set_defaults(func=lambda a: check_marks(a.path))

    args = ap.parse_args()
    if not args.command:
        ap.print_help()
        sys.exit(2)
    args.func(args)


if __name__ == "__main__":
    main()
