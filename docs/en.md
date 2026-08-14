# TraceMark (English)

Artistic decorative seal/postcard synthesis from photo + one-line theme.
Trace every mark.

## Routing table (read AUP.md first, then check availability)

| Track | Trigger | Template |
| --- | --- | --- |
| zh (Chinese seal script) | Chinese names / studio names / auspicious phrases / city souvenirs | built into render.py (red zhuan square seal / white zhuan square seal / round leisure seal) |
| jp (Japanese craft stamp) | katakana / Japanese stationery aesthetic / eki-stamp style | built into render.py (circular ink-wash stamp) |
| wz (Western wax seal) | monogram / wedding / gift / branded envelope | built into render.py (wax-seal round impression) |

**Category availability**: the seal track refuses company/institution/government names (`validate_input.py` rejects and gently redirects to the stamp style); postcard and commemorative-stamp styles accept organization names. See AUP.md.

## Workflow

1. `python3 scripts/validate_input.py "<input text>" "<track>"` → continue once it passes
2. Prepare the input photo (V1 takes photos directly)
3. `python3 scripts/render.py --config examples/<case>/config.yaml` → outputs a 1200×1600 PNG
4. Visual quality gate: verify text character-by-character (zero gibberish), permanent microtext "TRACE·ART" present, perforation/artistic border present
5. Store new cases as paired `examples/<case>/input.jpg + prompt.txt + config.yaml + output.png` (the examples directory IS the eval set)

## Hard constraints (violations → rework)

- Outputs must keep the artification border/perforation/microtext; no configuration may bypass them (legal firewall)
- Text rendering failures (tofu boxes/missing glyphs) must raise an error; never ship a broken output
- Stamp texture (rotation/offset/ink bloom) must be enabled; never ship a perfect geometric impression
- Never generate seal lookalikes: outputs must be perceptibly distinguishable from real seals in size and detail

## Iteration discipline

- Every release must ship user-visible changes (new template / new texture / new case)
- New templates require cultural research first (prototype/dimensions/reading order/palette) before entering render.py; each template must ship with at least one examples/ case and pass regression
