# PRESS.md — Public Beta Communications & Data Safety Plan

*Created 2026-11-03 from the external review. This is the working document for
everything that must be true before a reporter finds the site.*

---

## Status: In progress

### Completed
- [x] Species insights panel (narratives, gene groups, detection history, susceptibility prose, caveats)
- [x] Beta banner with click-to-reveal email
- [x] Footer logo lockup + GitHub link + bioRxiv citation placeholder
- [x] Matomo analytics (entity events, site search, locale tracking)
- [x] Mammalian-only mutation censorship
- [x] PhyloPic attribution fix (was silently empty)
- [x] Map: OSM basemap, NZ-centred, WebGL-independent stats

### This tranche (no LLM required)
- [x] **Detection count labelling** — "reports" vs "birds" on every surface
- [x] **NZ regional view fix** — "arrived" for detected countries; NZ shows correctly
- [x] **Susceptibility confidence gating** — confidence < 0.3 → "insufficient evidence"
- [x] **formatBytes NaN guard** — Downloads page fixed
- [x] **Genome-available race condition** — shows loading pulse, not "no genome"
- [x] **Date format normalisation** — formatDate() handles ISO-week + US formats
- [x] **Raw array strings** — strain column cleaned (Python dicts + arrays parsed)
- [x] **Vaccine page "agent offline"** — reworded to accurate description
- [x] **Paper count reconciliation** — all three numbers on Credits
- [x] **Kākāpō metadata** — Māori name, population (~350), vaccination target, CR chip on page
- [x] **Kāhu DOC case** — "Case #2 · Wairarapa · 2026-07-17 (DOC)" renders on page
- [x] **Research tab species-filtering** — scope note labels general-context findings

### Next LLM tranche (needs :8005)
- [x] **Press page** (#/press) — fact sheet, stories, how-to-credit, contact
- [x] **Pre-built HTML species pages** — 11,348 static pages, OG tags, sitemap (2,257 indexed), robots.txt
- [ ] **Overlay enrichment** — DOC links, report-a-dead-bird contacts
- [x] **Locale files** — new keys translated

---

## 1. Number Safety — every number quotable without a phone call

### 1a. "Detections" means two things

The `detection_count` column in `detections_merged.parquet` aggregates
flock/event sizes. Species pages currently show the SUM (birds affected),
not the ROW COUNT (surveillance reports).

| Species | Reports (rows) | Birds (sum of detection_count) |
|---|---|---|
| Cape cormorant | 20 | 26,540 |
| Chicken | 312 | 182,071,085 |
| Northern gannet | 420 | 1,093 |

**Fix**: Label both everywhere:
- Species page: "20 reports covering 26,540 birds"
- Home page hero: "44,906 detection records" (not "detections")
- Numbers page: same
- Insights panel already uses row count (correct)

### 1b. Official counts without context

Northern gannet shows 1,093 from official surveillance, but published die-off
estimates are far higher. The honest fix is not to reconcile them (that's a
research project) but to label the number and link to the contradictions page.

**Fix**: Add a tooltip on the detection count: "Official surveillance reports;
published mortality estimates may differ — see Contradictions."

### 1c. Paper count mismatch

| Source | Number | What it measures |
|---|---|---|
| stats.json / home / Numbers | 1,366 | Papers registered in the corpus |
| Credits page | 142 | Papers with full-text LLM extraction |
| (internal) | 1,204 | Papers with markdown available |

**Fix**: Credits page shows all three with plain labels.

### 1d. Susceptibility scores with confidence 0

Twenty gamebirds share a permissiveness of 43.1 at confidence 0–0.2. These
should not appear as quotable numbers.

**Fix**: When confidence < 0.3, the score chip renders as "insufficient
evidence" with the tooltip "Evidence is too thin to support a score."
The plain-language narrative (already generated) is the presentation.

---

## 2. NZ Regional View

### The problem

The regional-risk page rates NZ arrival risk as "low" (score 28.9) even though
the virus **arrived in July 2026** (first_detection: 2026-07-08, 4 species,
8 records). The watchlist shows global priorities (chicken, mallard, cat,
cattle, human) with zero NZ native species.

### The fix

1. **When a country has detections, show "arrived" not a risk score.**
   The risk model computed arrival probability before the event; showing
   "low risk" after arrival is wrong.

2. **Country-specific watchlist.** For NZ: surface native species with
   genomes + susceptibility data (kākāpō, kākā, tūī, kea, kāhu) alongside
   global priorities. The kākāpō question — "which of our birds are next?"
   — is the #1 thing a NZ reporter will ask.

3. **Label the detected species.** NZ detections are Brown skua, kāhu
   (Circus approximans), South Polar skua, Northern giant petrel — all
   non-endemic. Show them, but don't let the watchlist be mistaken for
   "these are NZ's only at-risk species."

### Implementation

- `build_region_risk.py`: when `total_records > 0`, set `arrival_risk.band`
  to "arrived" and include `first_detection` + `detected_species` in the
  response (already present — just needs the band override)
- Watchlist: for detected countries, prepend native species from the
  overlay (conservation-concern species with genomes) above the global list
- Frontend: render "🟢 Arrived {date}" chip instead of the risk meter

---

## 3. Reporter Box (next LLM tranche)

Each species page gets a reporter box above the tabs:

```
┌─────────────────────────────────────────────────────────────┐
│ CAPE CORMORANT AND BIRD FLU                                  │
│                                                              │
│ 20 official reports covering 26,540 birds across 1 country   │
│ (Jan 2021 – Oct 2026) · as of 3 Nov 2026                     │
│                                                              │
│ [Copy citation] [Why the numbers differ]                     │
│                                                              │
│ Evidence: genome-based gene panel; not studied directly      │
│ Closest studied relatives: Great cormorant, Neotropic        │
│ cormorant (both with HPAI research)                          │
│                                                              │
│ Conservation: Near Threatened · est. 250,000–400,000 pairs  │
│ Contact: [country agency] · Report dead birds: [link]        │
└─────────────────────────────────────────────────────────────┘
```

Fields (deterministic + LLM):
- Reports / birds / countries / dates → from `detection_history`
- Evidence strength → from `basis` + wiki paper_count
- Closest studied relatives → from `relatives` + wiki_species
- Conservation + population → from IUCN + overlay
- Citation string → assembled from the site citation template
- Copy button → clipboard API

---

## 4. Press Page (#/press)

Assembled from existing artifacts:

### What Roost is and isn't
> Roost aggregates public HPAI surveillance data and peer-reviewed research
> into a searchable resource. It is NOT an official surveillance source —
> for that, see MPI (NZ), WOAH WAHIS, FAO EMPRES-i, or your national
> veterinary authority. Roost's value is the gene-level and cross-species
> synthesis that official sources don't provide.

### Fact sheet (8 numbers from by_the_numbers.json)
| Number | Plain label | What it means |
|---|---|---|
| 44,906 | detection records | Individual surveillance reports across all sources |
| 718 | species with detections | Birds and mammals confirmed with HPAI |
| 106 | countries | Countries with at least one detection |
| 1,366 | papers registered | Research papers in the corpus |
| 437 | species with no research | Detected species never named in any extracted claim |
| 10 | species = 45% of research | The top-10 most-studied species account for 45% of all findings |
| 1,428 | genes searched | Immune genes searched across sequenced genomes |
| 11,348 | species searchable | Every bird species on Earth in the index |

### Stories in the data
- "437 of 718 infected species have no research findings" — the surveillance-research gap
- "Ten species account for 45% of all HPAI research" — the chicken-and-mouse problem
- "Two 2025 reviews put the Qinghai 2005 death toll at >6,000 and at 1,500 birds" — why the numbers don't agree (→ Contradictions)
- "The kākāpō has no HPAI detections, but 19 parrot species do" — the NZ story

### How to credit
> Roost: Avian Influenza Host Genomics Resource (2026).
> https://josephguhlin.com/Roost/. Accessed [date].

### Contact
joseph.guhlin@[revealed] — NZST (UTC+12/13) — response within 24h

---

## 5. SEO / Shareability (next tranche)

### The structural problem
Every page sits behind `#/`, which search engines treat as a single page.
No sitemap, no meta descriptions, no OG tags. Species pages are all titled
"Species — Roost."

### The fix
Pre-build one HTML page per species at `/species/{sci-slug}.html`:
- `<title>` = "Cape cormorant and bird flu — Roost"
- `<meta description>` = first sentence of the summary
- `<meta og:title>`, `<og:description>`, `<og:image>` (generated card)
- Static content = the reporter box (crawlable)
- `<link rel="canonical">` to the SPA page
- `sitemap.xml` with all 2,257 species URLs

The build step outputs these alongside the SPA in `dist/`. A crawler hits
the static page, a human clicks through to the SPA.

---

## 6. What NOT to do

- **Don't replace susceptibility scores entirely with prose.** Researchers
  need the numbers. Show both: score with confidence chip + narrative.
- **Don't build RSS/email.** Static site; Matomo tells you what's trending.
  A manual "what changed" on the press page is sufficient for beta.
- **Don't try to reconcile official vs literature mortality counts.** That's
  a research project. Label them and link to Contradictions.
- **Don't hide low-confidence susceptibility scores.** Label them
  "insufficient evidence" — transparency is the point.

---

## Appendix: Verified Data Issues

| Issue | Root cause | Status |
|---|---|---|
| Chicken shows 182M detections | `detection_count` sums flock sizes | Fix: use row count for "reports" |
| Cape cormorant Research tab shows general findings | wiki_species returns corpus-wide findings, not species-filtered | Fix: filter or label |
| Kākāpō "No genome sequenced" under "Genome available" | `genePanel` is null on first render; `{:else}` branch fires | Fix: gate on `!has_genome` |
| Kāhu DOC case not shown | `manual_detections[].case` never rendered | Fix: read + display |
| Downloads "NaN undefined" | `formatBytes(undefined)` → NaN, `sizes[NaN]` → undefined | Fix: guard |
| NZ regional risk "low" after arrival | Score computed pre-arrival, not recalculated | Fix: "arrived" band override |
| Watchlist has no NZ natives | Global watchlist algorithm, no per-country overlay | Fix: native-species prepend |
| Vaccine page "verification agent offline" | Hardcoded string | Fix: reword |
| Date format mixing | Raw `date_detected` strings (US/ISO-week) | Fix: parse + format |
| Raw `['h5n1','h5']` in detection lists | Array joined as string | Fix: parse + render as chips |
