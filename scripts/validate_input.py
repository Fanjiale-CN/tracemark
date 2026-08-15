#!/usr/bin/env python3
"""TraceMark AUP gate — purpose-based, expression-permissive.

Design (v1.0 audit): political expression, public figures, institution names,
satire, historical subjects are ALL allowed. The gate only blocks
certification/impersonation *purposes* and exact replicas of existing seals:

    allowed purposes : art | editorial | satire | travel | gift | postcard
    blocked purposes : authentication | official-document | exact-replica

The gate inspects intent markers (keywords plus config-level purpose field),
never the vocabulary of the text itself. General content safety is delegated
to the host platform; TraceMark does not run a broad political censorship
filter.
"""
import re
import sys

# ---------------------------------------------------------------------------
# Purpose model
# ---------------------------------------------------------------------------
ALLOWED_PURPOSES = {"art", "editorial", "satire", "travel", "gift", "postcard"}
BLOCKED_PURPOSES = {"authentication", "official-document", "exact-replica"}

# Intent markers in user-supplied text / prompts that signal a blocked
# purpose. These are purpose signals ("use this to certify a contract"), not
# topic words ("国务院" is fine in an art/editorial/satire context).
_BLOCK_INTENT_PATTERNS = [
    r"用于.{0,6}认证|用于.{0,6}验证|认证用途|认证.{0,6}用途|刻制印章|刻章|authentication|authenticat",
    r"公章|官方文件|公文|证件|票据|合同盖章|official document|official-document",
    r"印章的效力|同等效力|效力等效|公章刻",
    r"复刻真实印章|复刻现存印章|复刻官方印章|exact replica|replicate an existing (official )?seal",
    r"冒充|仿冒|假冒官方|impersonate|forged|fraud",
    r"法律效[力用]|具有法律效力|legal(ly )?valid|legal validity",
    r"登记印鉴|注册商标盖章|registered mark|trademark impersonat",
]
_BLOCK_INTENT = [re.compile(p) for p in _BLOCK_INTENT_PATTERNS]

# Artistic-context whitelist — when the text itself frames a blocked-topic
# word as art / satire / memorial, the expression is allowed. Checked FIRST.
_ART_CONTEXT_PATTERNS = [re.compile(p) for p in [
    r"纪念章|纪念|讽刺|艺术|玩笑|装饰|playful|artwork|satire|memorial|commemorative",
]]

# ---------------------------------------------------------------------------
# Template registry — source system, format, and text capacity
# ---------------------------------------------------------------------------
TEMPLATES = {
    "zh-square-zhu":      {"track": "zh", "format": "postcard", "capacity": 8},
    "zh-square-bai":      {"track": "zh", "format": "postcard", "capacity": 8},
    "zh-circle-leisure":  {"track": "zh", "format": "postcard", "capacity": 4},
    "jp-circle-stamp":    {"track": "jp", "format": "postcard", "capacity": 8},
    "wz-wax-monogram":    {"track": "wz", "format": "postcard", "capacity": 3},
}

TRACK_DEFAULT_TEMPLATES = {"zh": "zh-square-zhu", "jp": "jp-circle-stamp",
                           "wz": "wz-wax-monogram"}


def derive_mode(track_or_mode: str) -> str:
    """zh/wz -> seal, jp -> stamp; pass through seal|stamp|postcard unchanged."""
    if track_or_mode in ("zh", "wz"):
        return "seal"
    if track_or_mode == "jp":
        return "stamp"
    if track_or_mode in ("seal", "stamp", "postcard"):
        return track_or_mode
    raise ValueError(f"unknown track/mode: {track_or_mode!r}")


def resolve_template(config: dict):
    """Return (template, track, format, capacity, error_message).

    Four concepts stay separate: track / format / template / purpose.
    Errors: unknown template, template/track mismatch, format/template
    mismatch — all are hard errors, never silently fixed.
    """
    track = config.get("track")
    if track not in TRACK_DEFAULT_TEMPLATES:
        return None, None, None, None, (
            f"invalid track {track!r}; expected zh | jp | wz")
    fmt = config.get("format") or "postcard"
    if fmt not in ("seal", "stamp", "postcard"):
        return None, None, None, None, (
            f"invalid format {fmt!r}; expected seal | stamp | postcard")
    tpl = config.get("template") or TRACK_DEFAULT_TEMPLATES[track]
    if tpl not in TEMPLATES:
        return None, None, None, None, f"unknown template {tpl!r}"
    meta = TEMPLATES[tpl]
    if meta["track"] != track:
        return None, None, None, None, (
            f"template {tpl!r} belongs to track {meta['track']!r}, "
            f"not track {track!r}")
    if fmt == "seal" and meta["format"] != "postcard":
        return None, None, None, None, (
            f"format seal cannot combine with template {tpl!r}")
    return tpl, track, fmt, meta["capacity"], None


def check_capacity(text: str, capacity: int):
    """No silent truncation. Over-capacity text is a hard error.

    The caller may auto-switch the config to a larger-capacity template
    (e.g. zh-circle-leisure for 4-char round layout) — but that never
    rewrites the user's text. If still over capacity, fail explicitly.
    """
    n = len(text)
    if n > capacity:
        return (f"text length {n} exceeds template capacity {capacity}; "
                "never silently truncate user text")
    return None


def validate(text: str, mode_or_track: str = "postcard",
             config: dict = None) -> int:
    """Run the AUP gate. Returns 0 = pass, 1 = rejected.

    config (optional): full config dict — enables template resolution,
    capacity checks and the purpose field.
    """
    text = text or ""

    if config:
        tpl, track, fmt, capacity, err = resolve_template(config)
        if err:
            print(f"[tracemark] FAIL: config: {err}", file=sys.stderr)
            return 1
        cap_err = check_capacity(text, capacity)
        if cap_err:
            print(f"[tracemark] FAIL: config: {cap_err}", file=sys.stderr)
            print("[tracemark] HINT: shorten the seal text, or switch the "
                  "config to a template with larger capacity (zh-square-* "
                  "holds 8 chars; wz-wax-monogram holds 3). Do not rewrite "
                  "the user's text.", file=sys.stderr)
            return 1
        if config.get("purpose") in BLOCKED_PURPOSES:
            _print_rejection(text, config["purpose"])
            return 1

    # Intent markers can appear anywhere the operator writes: the seal text,
    # caption, place — a blocked purpose hidden in a caption must still be
    # caught (exact-replica boundary test writes it there).
    full = text
    if config:
        for val in config.values():
            if isinstance(val, str):
                full = "\n".join((full, val))
    for pat in _ART_CONTEXT_PATTERNS:
        if pat.search(full):
            print(f"[tracemark] PASS: {text!r} in {mode_or_track} mode "
                  "(artistic-context whitelist: memorial / satire / art / "
                  "playful usage is permitted)")
            return 0  # whitelisted artistic context beats all blocks
    for pat in _BLOCK_INTENT:
        if pat.search(full):
            _print_rejection(text, "blocked-purpose-marker")
            return 1

    try:
        mode = derive_mode(mode_or_track)
    except ValueError:
        mode = mode_or_track
    print(f"[tracemark] PASS: {text!r} in {mode} mode. "
          "(political themes, public figures, institution names, satire and "
          "historical subjects are permitted; only certification/replication "
          "purposes are blocked)")
    return 0


def _print_rejection(text: str, reason: str):
    print(f"[tracemark] REJECTED: {text!r} signals a blocked purpose "
          f"({reason}): certification, official documents, or exact "
          "replication of an existing seal.", file=sys.stderr)
    print("[tracemark] Allowed purposes: art | editorial | satire | travel | "
          "gift | postcard. Blocked: authentication | official-document | "
          "exact-replica. The same wording used as art/editorial/satire is "
          "welcome — TraceMark blocks the *purpose*, not the *topic*.",
          file=sys.stderr)
    print("[tracemark] 被拒原因：内容表明了认证/公文/复刻真实印章的用途。"
          "艺术、讽刺、纪念等表达用途完全开放——TraceMark 拒绝用途而非话题。",
          file=sys.stderr)
    print("[tracemark] 許可目的: art | editorial | satire | travel | gift | "
          "postcard。認証・公文書・実在印章の完全複製だけがブロックされます。"
          "同じ文言でもアート・風刺・記念用途なら問題ありません。",
          file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print("[tracemark] usage: validate_input.py \"<text>\" "
              "<track|mode> [--config path]", file=sys.stderr)
        sys.exit(2)
    config = None
    args = sys.argv[3:]
    if "--config" in args:
        import yaml  # noqa: E402
        idx = args.index("--config")
        if idx + 1 < len(args):
            config = yaml.safe_load(open(args[idx + 1])) or {}
    sys.exit(validate(sys.argv[1], sys.argv[2], config))


if __name__ == "__main__":
    main()
