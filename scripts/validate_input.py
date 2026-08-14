#!/usr/bin/env python3
"""TraceMark input guard — category-availability routing (category-level, not keyword-hunting).

Rules (per AUP.md):
- seal mode: organization/company/government names are FORBIDDEN -> guide user to stamp/postcard mode
- stamp / postcard modes: organization, company, government, country names are ALLOWED (memorial nature)

Usage:
    python3 validate_input.py "<text>" "<mode>"
    mode in: seal | stamp | postcard
Exit: 0 = pass, 1 = rejected (prints guidance, never a bare error)
"""
import re
import sys

FORBIDDEN_MARKERS = [
    # Chinese
    "公司", "有限", "集团", "股份", "事务所", "委员会", "局", "厅", "署", "政府",
    # English
    "corp", "inc", "ltd", "llc", "co.", "corporation", "company", "limited",
    "government", "ministry", "agency", "bureau", "committee",
    # Japanese
    "会社", "法人", "組合", "省", "庁", "都道府県",
]

MARKER_RE = re.compile("|".join(re.escape(m) for m in FORBIDDEN_MARKERS), re.IGNORECASE)

GUIDANCE = {
    "zh": "机构/公司/政府名称不能出现在印章模式中——这会触碰「可用于签署认证的印章」的法律红线。这类内容更适合做成纪念邮票或明信片样式，那里官方机构名是被允许的（纪念性质）。试试切换到邮票模式？",
    "en": "Organization names are not allowed in seal mode — that edges into legally sensitive territory of authentication-grade seals. The same content is welcome in commemorative-stamp or postcard mode, where institutional names are memorial by nature. Try switching to stamp mode?",
    "ja": "会社・機関の名前は「印章」モードでは使えません。法的効力を持つ印鑑の領域に触れるためです。同じ内容なら記念切手やはがきスタイルが最適です。そちらでは機関名は記念の性質で使えます。「切手」モードに切り替えてみてください。",
}


def validate(text: str, mode: str) -> int:
    text = text.strip()
    mode = mode.strip().lower()
    if mode not in ("seal", "stamp", "postcard"):
        print(f"[tracemark] unknown mode '{mode}'; choose seal | stamp | postcard", file=sys.stderr)
        return 1
    if mode == "seal" and MARKER_RE.search(text):
        hit = MARKER_RE.search(text).group(0)
        print(f"[tracemark] REJECTED: \"{text}\" contains organization marker \"{hit}\" in seal mode.")
        print(GUIDANCE["zh"])
        print(GUIDANCE["en"])
        print(GUIDANCE["ja"])
        return 1
    print(f"[tracemark] PASS: \"{text}\" in {mode} mode.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(validate(sys.argv[1], sys.argv[2]))
