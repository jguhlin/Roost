# Figure & Media Design System

Planning + review standard for every figure, diagram, and video abstract the
Roost figure system produces. Companion to [FIGURE_AGENT.md](FIGURE_AGENT.md)
(how it works) — this doc is **how it should look**.

v1 — 2026-10-04, after the first 22-figure pass surfaced the need for a
unified visual identity rather than per-figure improvisation.

## 1. Principles

1. **One figure, one message.** If the caption can't state the takeaway in a
   sentence, the figure is doing two jobs — split it.
2. **Editable source is the artifact.** Spec JSON, `.py`, `.svg` — never edit
   the PNG. Style lives in shared code (`figures/style.py`), not pasted in
   each figure.
3. **Native to the site.** Figures render on pages using Tailwind slate/blue;
   the house palette below matches, so media feels embedded, not bolted on.
4. **Evidence-forward.** Every visual claim carries its `[paper_id]` anchor;
   qualitative orderings say so in the figure, not just the caption.
5. **Publish gate:** validator 0 errors → audit clean → pixel check →
   browser check. No exceptions.

## 2. Typography (Lato)

Lato is installed system-wide (weights 250–900) and registered in matplotlib.
It replaces DejaVu Sans in **all** figures and (via `figures/style.py`)
becomes the default for every new figure source.

| Role | Face | Size (preview px @1600w) |
|---|---|---|
| Figure title | Lato Bold/Black | 30–34 |
| Subtitle / lede | Lato Regular, slate-500 | 16–17 |
| Panel label (A · B · C) | Lato Black, small caps feel | 13 |
| Axis + body labels | Lato Regular | 12–13 |
| Big display numbers | Lato Black | 44–110 |
| Cell/annotation text | Lato Regular | 12–13 |
| Caption (on page) | site styles it | — |
| Source/footnote line | Lato Regular, slate-400 | 10–11 |

Rules: no more than 3 weights per figure (Regular + Semibold + Black is the
default trio). Numbers in tables/bars use tabular feel (Lato is close
enough); never letterspace body text; letterspacing only for eyebrow labels.

## 3. Color tokens

Same hues the site already uses (Tailwind-aligned), fixed hex in
`figures/style.py`:

| Token | Hex | Use |
|---|---|---|
| `ink` | `#0f172a` | primary text, axis labels |
| `muted` | `#475569` | secondary text, axes |
| `faint` | `#94a3b8` | footnotes, grid hairlines |
| `surface` | `#f8fafc` | figure background |
| `card` | `#ffffff` | panels/cards |
| `primary` | `#1d4ed8` | data series 1, links, positive-neutral |
| `primary-soft` | `#bfdbfe` | fills for primary-coded cells |
| `alert` | `#dc2626` | gaps, divergence, danger — **sparingly** |
| `alert-soft` | `#fee2e2` | alert-coded fills |
| `caution` | `#d97706` | partial/conditional states |
| `good` | `#16a34a` | positive outcomes, consensus |
| `good-soft` | `#dcfce7` | good-coded fills |

Semantic rules:
- `alert` is reserved for *absence* (gaps) and *divergence* (conflicts) —
  never for decoration. A bar is red because the number is a problem, not
  for contrast.
- Two-series figures: `primary` + `muted`. Divergent: `good`/`alert`.
  Sequential fills: the `-soft` tints of one hue.
- Background is always `surface`; panels `card`. No dark-mode variants yet
  (pages render media on white cards).

## 4. Layout

- SVG diagrams: 1400 px wide canvas, 720–840 tall, 40 px margins, corner
  radius 16–20 on cards, 2–3 px borders in the token hue of the card's
  semantic role.
- matplotlib: figure widths 10.5 in (single) / 12 in (wide) at 160 dpi
  preview; export 2400 px. Panel gaps ≥ 0.45 in; panel labels top-left,
  Bold, `A ·`-style.
- Alignment: panel tops align; baselines of sibling labels align; the
  validator's grid-alignment warnings are treated as errors during rework.
- Whitespace beats boxes: prefer one enclosing card per panel over nested
  boxes inside cards (the B3.13/D1.1 figure is the ceiling — no deeper).

## 5. Data figures

- Direct-label everything possible; legends only when >2 series.
- Log axis when values span >10× (state "log scale" on the axis).
- Big-number callouts (Lato Black, token color) when a single number IS the
  message — then the chart is supporting context, not the point.
- Qualitative orderings (e.g. minireplicon relative activity) must say
  "qualitative" on-figure.
- Source line, bottom-left, 10 px `faint`: corpus ids + figure name.

## 6. Diagrams & icons

- The asset index (12,444 items) is for **host/organism/virus glyphs**, not
  decoration. Rule: if a rectangle's label is a noun with an available
  silhouette or icon (chicken, human, duck, virus, cell), use the asset.
- Icons: flat single-hue silhouettes at 48–80 px, `muted` or the semantic
  token; never multi-color clipart inside a schematic.
- Abstract mechanism (protein domains, complexes): rounded rects with token
  fills — do not force icons onto molecular concepts.
- Arrows: 3–4 px, token-colored, `marker-end` triangles; dashed = blocked/
  absent; spring curves only in video, not statics.
- Caption carries asset attribution; figures with icons always record them
  in the manifest via `search_assets --import`.

## 7. Gap maps (spec-driven)

- Column order: evidence → the gap (gap column last, dashed `alert` outline,
  "THE GAP" label).
- Levels stay semantic: 2 direct / 1 adjacent / 0 none. Never color a
  no-evidence cell with a calm hue to "soften" it.
- Cell text ≤ 3 lines at 12–13 px; if more is needed, the note box carries
  it.

## 8. Video abstracts (fframes)

**Update (2026-10-04, post-review):** the trailer/abstract style is retired.
The default video form for briefings is the **educational explainer** —
lecture pacing, numbered sections from the briefing itself, ~4 s per line,
on-screen citations, progress dots. Two ways to make one:

- `scripts/figures/make_explainer.py --slug NAME` — deterministic briefing→
  video codegen (title + sections + unresolved; meta sections like "search
  coverage" are skipped), builds + renders + publishes. Use this for bulk.
- Hand-authored crates (figures/video/anp32a-barrier) when the beat design
  needs custom diagrams; keep the same pacing rules.

The old motion test (number-contrast / state-transition / spatio-temporal)
now only decides whether a *trailer-style* addition is worth it on top of
the explainer — the explainer itself fits any briefing.

Structure — **hook → tension → resolution → outro** (12–16 s total):

| Beat | Duration | Content |
|---|---|---|
| Hook | 0–2 s | eyebrow (RESEARCH BRIEFING · VIDEO ABSTRACT) + title, spring rise |
| Tension | 2–7 s | the conflicting numbers / the blocked mechanism — animated counters (EaseOut 1.6 s), status flips |
| Resolution | 7–12 s | the explanation/adaptive bypass, amber |
| Outro | 12–16 s | one-line takeaway + briefing slug lower-third, fade |

- Motion language: entrances spring (mass 1, stiffness 160–180, damping
  20–22); counters EaseOut; status words may pulse (sin, 0.85–1.0); nothing
  else moves — no drifting backgrounds, no spin.
- Typography: DM Sans (ships with the fframes template media/) — or Lato if
  added to `media/`; same token colors as figures; display numbers 100–110.
- Composition: center axis for hook/outro; two-panel symmetry for
  comparisons (avian left/blue vs mammalian right/red); badges overlap the
  panels' seam to signal the relationship.
- Every beat must be frame-verified (extract at beat midpoints, ink
  1.5–7%) before publishing.
- Audio: silent until a licensed music bed is sourced (CC0 library TODO);
  never ship TTS.

## 9. Review checklist (before publish)

- [ ] Message: caption states one takeaway in one sentence
- [ ] Typography: Lato, ≤3 weights, sizes from the scale
- [ ] Color: tokens only; `alert` used semantically
- [ ] Data honesty: qualitative/estimated labeled on-figure; log axes noted
- [ ] Icons: nouns-with-silhouettes use assets; attribution in manifest
- [ ] Validator 0 errors (diagrams); audit clean; pixel ink check
- [ ] Browser check on the real page (fresh mount + hash-nav)
- [ ] Caption + source line present; figure named in registry
