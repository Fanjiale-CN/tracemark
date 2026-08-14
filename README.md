# TraceMark

> Trace every mark. Turn a photo into a stamped postcard — Chinese seal-carving, Japanese town-stamp, Western wax seal. Three cultures, one generation.

**Choose your language**:
**[English](docs/en.md)** · [简体中文](docs/zh-hans.md) · [繁體中文](docs/zh-hant.md) · [粵語](docs/yue.md) · [日本語](docs/ja.md) · [Français](docs/fr.md)

Each language gets a full standalone page — links stay stable as content grows.

![Chinese seal-carving postcard — 海上观日](gallery/zh_shanghai_new.png)

*Track zh — a photo of Shanghai at dawn, stamped with a vermilion zhuan seal 「海上观日」: square grid, right-column-first reading order, jinshi dry-brush texture, perforated postcard edge.*

![Japanese craft stamp postcard — 京都の灯](gallery/jp_kyoto_new.png)

*Track jp — Kyoto night alley under chochin lanterns, sealed with a circular sumi-ink craft stamp 「京都の灯」: enso-style ink ring, sumi mist halo, washi grain with deckled edges.*

![Western wax seal postcard — monogram](gallery/wz_seal_new.png)

*Track wz — an embossed crimson wax seal with a monogram flourish on letterpress cotton paper, photographed like real stationery.*

---

## What is TraceMark

TraceMark is an agent skill: give it a photo and a one-line theme, it renders a 1200×1600 stamped art postcard. Pure PIL deterministic rendering — **text is always typeset correctly, zero generative gibberish**; the whole pipeline runs locally, photos never leave your machine.

Quick start:

```bash
git clone https://github.com/Fanjiale-CN/tracemark.git
cd tracemark
# 1. risk check first (every text passes this gate)
python3 scripts/validate_input.py "海上观日" seal
# 2. render (edit config.yaml text/track/seed to change theme)
python3 scripts/render.py --config examples/shanghai-sunrise/config.yaml
# → examples/shanghai-sunrise/output.jpg
```

One YAML configures a case (`examples/shanghai-sunrise/config.yaml`): `text` is the seal text, `track` picks `zh|jp|wz`, `seed` controls stamp randomness, `photo` set to null skips the photo zone.

## Three tracks

| Track | Cultural prototype | Use it for | Example |
| --- | --- | --- | --- |
| zh | Chinese zhuan seal-carving (square grid, right→left reading order) | name / studio / city memories | `examples/shanghai-sunrise` |
| jp | Japanese eki-stamp craft stamp (circular sumi-ink) | travel memories / stationery | `examples/kyoto-lantern` |
| wz | Western wax seal (embossed monogram) | envelopes / weddings / brands | `examples/wax-monogram` |

## Why it looks like this (design stance)

Outputs are **deliberately not real seals**: perforated edges, non-standard layout, a permanent micro-type `TRACE·ART`. That is both an art language and a legal moat — seal laws protect marks usable for authentication, and statute (e.g. the 1970 U.S. postal law's size-difference requirement for stamp reproductions) itself carves out the "artistic difference" safe zone. See AUP.md.

Risk control works in two layers: input validation (the seal track refuses company/agency/government names and gently redirects to the postcard track) plus output-layer forced artification (no config can opt out of the border and micro-type). Creators never hit a wall — a refusal always comes with a road.

## File layout

```
SKILL.md            # route table + usage flow (agent entry)
docs/               # six languages, one standalone page each
AUP.md              # acceptable use policy, six languages
FONTS.md            # license notes for the three bundled fonts
scripts/validate_input.py  # category-availability risk gate
scripts/render.py          # compositing engine (zh/jp/wz tracks)
scripts/texture.py         # stamp texture (ink mist / jinshi / wax relief)
examples/           # input-output paired cases = the eval suite
research/           # three-culture seal studies (design rationale)
gallery/            # showcase images used on this page
```

## Contributing

New cases follow the same pairing as `examples/` — submit one input photo + prompt + config + output. The `examples/` directory doubles as the regression eval suite, so every contribution is checked against real outputs.

## Iteration discipline

Each release ships only user-visible change (new template / new texture / new case); see [Releases](../../releases). Pure refactors never headline a changelog.

## License

MIT © 2026 Galok. Font licenses in `FONTS.md` (the seal-script font ships under its author's custom license — no renaming, no trademark use, redistribution must include the license copy with attribution).
