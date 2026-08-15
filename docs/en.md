# TraceMark (English)

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark.

## Routing table (read AUP.md first, then check availability)

| Track | Trigger | Template |
| --- | --- | --- |
| zh (Chinese seal script) | Chinese names / studio names / auspicious phrases / city souvenirs | built into render.py (red zhuan square seal / white zhuan square seal / round leisure seal) |
| jp (Japanese craft stamp) | katakana / Japanese stationery aesthetic / eki-stamp style | built into render.py (circular ink-wash stamp) |
| wz (Western wax seal) | monogram / wedding / gift / branded envelope | built into render.py (wax-seal round impression) |

**Purpose-based availability**: risk control gates on *purpose*, not keywords — political expression, public figures, institutions, nations, historical subjects and satire are all allowed; only authentication purposes and the replication of existing official seals are blocked. See AUP.md.

## Workflow

1. Prepare the input photo and write `config.yaml` (schema below). AUP validation, photo-path resolution (relative to the config file, never the cwd), EXIF correction, and the real missing-glyph check are all enforced automatically by the pipeline — no step can be skipped.
2. `python3 scripts/tracemark.py render --config examples/<case>/config.yaml` → outputs a 1200×1600 JPEG (q88); add `--no-photo` for the seal-only deliverable
3. AUP check can also run standalone: `python3 scripts/tracemark.py validate "<text>" "zh"` (track `zh|jp|wz` or mode `seal|stamp|postcard`, auto-derived)
4. Visual quality gate: character-by-character verification (zero tofu — glyphs are checked against the font's actual cmap via freetype-py, glyph index 0 = .notdef), permanent microtext "TRACE·ART" present, perforation/artistic border present (baked into every output, seal-only included)
5. Store new cases as paired `examples/<case>/input.jpg + prompt.txt + config.yaml + output.jpg` (the examples directory IS the eval set); boundary cases use `_expect: fail` or `_expect: reject` in their config

### config.yaml schema

```yaml
track: zh | jp | wz          # zh/wz -> seal mode, jp -> stamp mode (auto-derived)
template: zh-square-zhu | zh-square-bai | zh-circle-leisure |
          jp-circle-stamp | wz-wax-monogram | null   # optional; track fallback otherwise
text: "<seal text>"          # >8 chars is truncated with a warning; tofu chars fail the build
seed: 7                      # explicit seed -> pixel-stable outputs
photo: input.jpg             # relative to config.yaml dir (never cwd); null = seal-only
caption: "<one-line caption>"
date: "2026.08.15"
place: "<place name>"
style:
  vermilion: "#C8392B"
  mode: zhu | bai (zh) | red | black (jp) | crimson | wine | gold (wz)
```

## Hard constraints (violations → rework)

- Outputs must keep the artification border/perforation/microtext; no configuration may bypass them (legal firewall)
- Text rendering failures (tofu boxes/missing glyphs) must raise an error; never ship a broken output
- Stamp texture (rotation/offset/ink bloom) must be enabled; never ship a perfect geometric impression
- Never generate seal lookalikes: outputs must be perceptibly distinguishable from real seals in size and detail

## Iteration discipline

- Every release must ship user-visible changes (new template / new texture / new case)
- New templates require cultural research first (prototype/dimensions/reading order/palette) before entering render.py; each template must ship with at least one examples/ case and pass regression
