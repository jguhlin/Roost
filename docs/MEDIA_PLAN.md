# Media Plan — per-page editorial decisions

Answers, per briefing page, the four questions before any figure is made:

1. **Does a figure make sense here at all?**
2. **What figure type carries the most *useful* information for this topic?**
3. **Do we need multiple figures?**
4. **What sort of video (if any) is useful?** — same test applied to video.

Rule of thumb (added to FIGURE_DESIGN §1): a video earns its place only when
the topic has (a) a **number contrast** that benefits from animated count-up,
(b) a **state transition** (a mechanism flipping, a barrier being bypassed),
or (c) a **spatial/temporal process**. Otherwise the figure already carries
it and a video is decoration.

Status legend: ✅ shipped · 🔧 todo · ➖ deliberately none.

## Full briefings

| Page | 1. Figure? | 2. Type | 3. Count | 4. Video? | Status |
|---|---|---|---|---|---|
| Qinghai Lake mortality discrepancy | yes — numbers ARE the story | numbers-first display + log context | 1 | **yes** — animated count-up dramatizes 4.1× divergence (type a) | ✅ fig v2 + video v2 |
| ANP32A species barrier | yes — mechanism | side-by-side cell schematic with icons | 1 | **yes** — state transition: block → adaptive bypass (type b) | ✅ fig v2 + video (v1 beats — 🔧 v2 pass pending) |
| PB2-E627K across hosts | yes — comparative function | log-panel + host-context cards | 1 | **no** — static comparison, no motion adds meaning | ✅ fig v2 · video ➖ by design |
| Minimal ANP32 isoform | yes — set logic | functional matrix | 1 | **no** — a matrix has no temporal dimension | ✅ · video ➖ |
| B3.13 vs D1.1 cattle lineages | yes — two things: (a) what they are, (b) **when/how they unfolded** | (a) comparison cards ✅ (b) **timeline** — Feb 2024 TX → 13 states Jul 2024 → 2025 WI D1.1 | **2** | later — only if the timeline animates well (type c) | ✅ cards · 🔧 timeline |
| Wild-bird dispersal 2.3.4.4b | yes — but it's a **geographic** story | **schematic map** (Americas Pacific spread + Oceania gap), stats as annotations — NOT stat panels | 1 | possible later (type c: spread over time) | 🔧 replace stat panel with map |
| True mortality burden | yes — the under-count IS the message | official-vs-field log bars | 1 | **no** — single static contrast | ✅ · video ➖ |

## Gap reports (16)

For a gap report the actionable content is *where the evidence lives and
where it doesn't* — the gap map is the right type, and one figure is enough.
Videos for gap reports: **no** (a video restating "insufficient evidence"
transmits nothing the map hasn't).

| Group | Pages | Decision |
|---|---|---|
| Substantive gap reports (13) | DDX58, MX1, NS1-STAT, reassortment, PB2 markers, mallard cytokines, tolerance framework, HA evolution/CVV, brain lesions, NL otters, HA RBM, ducks-vs-chickens, waterfowl tolerance | ✅ keep gap maps (spec-driven) |
| Thin-to-empty gap report | was-the-2005-qinghai-lake…species-barrier-crossing (1 section, no content to map) | **no figure** — fold into the sibling Qinghai page's story; ➖ |

## Credits policy (applies everywhere)

- **Credit every imported asset, including CC0/PD** — "no attribution
  required" is a legal floor, not a practice. On-page figure attribution now
  lists all assets with license; per-figure TXT + rollup already did.
- Figures with zero third-party assets say so in the manifest
  (`attribution_summary: ""` → no credit line, sources still cited).
- Modifications (e.g. recoloring) are recorded per-asset in the manifest
  (`modified: true` + note), and stated on-figure when space allows.

## Follow-up queue (priority order)

1. 🔧 dispersal → schematic map (type-fit fix) — highest value
2. 🔧 cattle timeline (second figure for B3.13/D1.1 page)
3. 🔧 ANP32A video → v2 beat structure
4. 🔧 migrate remaining .py figures to style.py (mortality-burden, dispersal
   successor, anp32-isoforms)
5. 🔧 landscape-level "state of the field" video (candidate; only if it
   animates the contradiction counts meaningfully)
6. 🔧 CC0 music bed for videos (then revisit all videos with audio)
   → **done D164 79254ea5**: synthesized ambient pad (make_ambient_bed.py,
   CC0-by-construction); both videos carry AAC audio. ANP32A video is now v2
   beats; all figure sources on house style. Remaining niceties: landscape
   'state of the field' video (only if it animates meaningfully).
