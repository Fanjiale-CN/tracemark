#!/usr/bin/env python3
"""TraceMark input guard — category-availability routing (category-level, not keyword-hunting).

Rules (per AUP.md):
- seal mode: organization/company/government names are FORBIDDEN -> guide user to stamp/postcard mode
- stamp / postcard modes: organization, company, government, country names are ALLOWED (memorial nature)

Parameter conventions (both accepted):
- mode: seal | stamp | postcard   (explicit output mode)
- track: zh | jp | wz            (cultural track; mode is derived: zh/wz -> seal, jp -> stamp)

Usage:
    python3 validate_input.py "<text>" "<mode>"          # mode in seal | stamp | postcard
    python3 validate_input.py --track zh "<text>"        # track zh/jp/wz, mode auto-derived
Exit: 0 = pass, 1 = rejected (prints gentle guidance, never a bare error)
"""
import re
import sys

# Forbidden markers — institution names that would touch authentication-grade
# seal territory when rendered in the *seal* mode. Full-word markers come first
# (precise, no false positives on personal names); single-character suffixes
# are a second safety net and only trip when the character itself appears.
FORBIDDEN_MARKERS = [
    # Chinese institution full-word markers (government bodies)
    "国务院", "人民政府", "省政府", "市政府", "县政府", "区政府", "镇政府",
    "人大常委会", "人民法院", "检察院", "公安局", "监察委",
    "税务总局", "海关总署", "市场监管", "卫健委", "气象局", "铁路局",
    "委员会", "事务所", "研究院", "科学院", "博物馆", "纪念馆", "美术馆",
    # Chinese institution suffixes (single-char net)
    "公司", "有限", "集团", "股份", "局", "厅", "署", "政府",
    # English
    "corp", "inc", "ltd", "llc", "co.", "corporation", "company", "limited",
    "government", "ministry", "agency", "bureau", "committee", "association",
    "university", "college", "institute", "foundation", "state council",
    # Japanese
    "会社", "法人", "組合", "省", "庁", "都道府県", "役所",
]

MARKER_RE = re.compile("|".join(re.escape(m) for m in FORBIDDEN_MARKERS), re.IGNORECASE)

GUIDANCE = {
    "zh": "机构/公司/政府名称不能出现在印章模式中——这会触碰「可用于签署认证的印章」的法律红线。这类内容更适合做成纪念邮票或明信片样式，那里官方机构名是被允许的（纪念性质）。试试切换到邮票或明信片模式？",
    "en": "Organization names are not allowed in seal mode — that edges into legally sensitive territory of authentication-grade seals. The same content is welcome in commemorative-stamp or postcard mode, where institutional names are memorial by nature. Try switching to stamp or postcard mode?",
    "ja": "会社・機関の名前は「印章」モードでは使えません。法的効力を持つ印鑑の領域に触れるためです。同じ内容なら記念切手やはがきスタイルが最適です。そちらでは機関名は記念の性質で使えます。「切手」モードに切り替えてみてください。",
}


def derive_mode(track: str):
    """Cultural track to output mode: zh/wz -> seal, jp -> stamp."""
    if track in ("zh", "wz"):
        return "seal"
    if track == "jp":
        return "stamp"
    raise ValueError(f"unknown track '{track}'; expected zh | jp | wz")


def validate(text: str, mode: str) -> int:
    text = text.strip()
    mode = mode.strip().lower()
    if mode not in ("seal", "stamp", "postcard"):
        print(f"[tracemark] unknown mode '{mode}'; choose seal | stamp | postcard", file=sys.stderr)
        return 1
    if mode == "seal" and MARKER_RE.search(text):
        hit = MARKER_RE.search(text).group(0)
        print(f'[tracemark] REJECTED: "{text}" contains organization marker "{hit}" in seal mode.')
        print(GUIDANCE["zh"])
        print(GUIDANCE["en"])
        print(GUIDANCE["ja"])
        return 1
    print(f'[tracemark] PASS: "{text}" in {mode} mode.')
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--track":
        try:
            mode = derive_mode(sys.argv[2])
        except ValueError as e:
            print(f"[tracemark] {e}", file=sys.stderr)
            sys.exit(2)
        sys.exit(validate(sys.argv[3], mode))
    if len(sys.argv) == 3:
        sys.exit(validate(sys.argv[1], sys.argv[2]))
    print(__doc__)
    sys.exit(2)
