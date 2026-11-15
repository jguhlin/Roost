# Model v0.6 — Draft Changes for Review

Generated from the full-corpus verification campaign (569 papers × 18 stages,
1,592 verdicts). Each change cites paper IDs from `model_verdicts.jsonl` —
quotes verbatim in that file. **Nothing applied yet — review, then approve.**

Principle: stages keep their structure; descriptions gain the 2.3.4.6b-era
corrections. Disagreements become "where the literature diverges" entries
with citations on both sides where they exist.

---

## 1 · Spread — Reservoir Species

**Current:** "Ducks and other waterfowl maintain H5N1 with low pathology —
shedding virus into water while showing minimal disease. The ancestral
reservoir."

**Verdict signal:** 5 disagrees + 21 changes — the largest cluster.

**Proposed v0.6:**
> Waterfowl are the ancestral LPAI reservoir and remain the maintenance host
> group for H5Nx — but clade 2.3.4.4b broke the low-pathology contract. Ducks
> now shed virus while dying: 60–80% mortality in experimental infections
> with neurological signs [korea_poultry2025], mass die-offs in barnacle
> geese [efsa_winter2025], lethal systemic replication in mallards
> [input_2024_20]. Transmission persists despite unprecedented mortality —
> the reservoir is now a dying reservoir. No single clear H5N1 reservoir
> species is identifiable [input_2024_214], and farmed poultry is a major
> amplification/emergence site [king_penguin_vaccine2026].

**Diverges entry:**
> The pre-2020 textbook framing — waterfowl as low-pathology maintenance
> hosts — still appears in current papers [sanderling_pathology2025] and
> remains true for classical LPAI. The 2.3.4.4b era contradicts it for H5N1
> in ducks and geese [korea_poultry2025, efsa_winter2025, input_2024_20,
> input_2024_430]. Both cannot be true of the same host–virus pair at the
> same time; clade and date likely resolve the contradiction.

---

## 2 · Spread — Seasonality & Timing

**Current:** "Autumn migration concentrates birds → peak transmission;
spring northward spread reseeds northern hemisphere. Outbreak waves follow
migration pulses with ~2-4 week lag."

**Verdict signal:** 1 disagree + 24 changes — seasonality has dissolved.

**Proposed v0.6:**
> The classic autumn-peak pattern has dissolved: since ~2021, 2.3.4.4b
> circulates year-round in Europe — "seasonality has virtually disappeared"
> [fox_neurotropism2023; griffon_vulture2025; conservation_response2025].
> Peaks now track breeding colonies (sandwich terns: ≥19,326 adult deaths
> late May–July [sandwich_tern_age_mortality_2026]) and spring movements in
> North America [input_2024_395]; in Africa, timing follows rainfall-driven
> waterfowl movements rather than latitudinal migration [south_africa2024].

---

## 3 · Infection — Cytokine Storm (2.5 Inflammatory Axis)

**Current:** "The killing mechanism: H5N1 triggers a hyper-inflammatory
NF-κB loop… Tolerant species (ducks) mount antiviral responses without the
storm; susceptible species (chickens, raptors) ha[ve]…"

**Verdict signal:** 4 disagrees + 3 changes — the storm framing is contested
in wild birds.

**Proposed v0.6** (append to description):
> Wild-bird caveat: the storm is not universal. Kittiwakes die peracutely
> with widespread necrosis but limited inflammatory infiltrates
> [kittiwake_norway2025]; some studies find attenuated pulmonary
> inflammation and reduced IFN responses — "counter to the paradigm"
> [input_2024_115]; in resistant chicken lines, higher early cytokines
> associate with survival, not death [input_2024_403]; ducks actively
> down-regulate pro-inflammatory cytokines to limit tissue damage
> [duck_transcriptome2021]. The storm framing is best-supported in poultry
> and mammals; in wild birds it is neither universal nor always the lethal
> mechanism.

**Diverges entry:**
> Whether the cytokine storm kills wild birds or merely accompanies
> infection is unresolved: strong NF-κB-driven inflammation in susceptible
> poultry [corpus: TNF/IL6/IL1B] vs peracute necrosis with minimal
> infiltrates in kittiwakes [kittiwake_norway2025] and attenuated responses
> in some mammalian models [input_2024_115]. Species, clade, and time-to-
> death likely determine which mechanism dominates.

---

## 4 · Infection — Cell Death & Pathology

**Current:** "The tolerance-vs-susceptibility black box: ducks clear
non-lytically (OASL/HERC5 paper) while chickens die with massive apoptosis.
Neurotropism in spillover carnivores is the extreme."

**Proposed v0.6** (append to description):
> Duck tolerance is partial and eroding: clade 2.3.4.4b isolates are lethal
> to ducks with systemic replication [input_2024_20], and H5N6 lineages show
> increasing duck pathogenicity over time [input_2024_243,
> input_2024_339]. Tolerance holds for some strain–tissue combinations but
> is no longer a safe default for modelling.

---

## 5 · Spread — Bridge & Routes (diverges only, no stage-text change)

**Bridge diverges:**
> The bridge into poultry is contested: domesticated ducks in constructed
> wetlands as the interface [input_2024_415]; bidirectional chicken–waterfowl
> spread [input_2024_274]; vs case–control evidence against wild birds as a
> significant exposure risk for turkey premises [input_2024_317]. Bridge
> host identity is likely region- and production-system-specific.

**Routes diverges:**
> Flyway framing has limits: Europe→Americas links are clear but Asia→Europe
> introduction routes remain unexplained [migratory_geospatial2025]; gene
> flow crosses flyway boundaries [caspian_sea2022]; South American spread
> proceeded along the coast by mammal proximity rather than bird flyways
> [input_2024_258]; some outbreaks have no migratory-bird link at all
> [input_2024_405].

**Sensing diverges (flagged, not changing the gene model):**
> One paper reports RIG-I receptor pathway enrichment in chicken H5N1
> response [input_2024_154], apparently contradicting RIG-I absence in
> chicken genomes. Likely gene-set annotation bleed (RIG-I pathway terms
> populated by MDA5/TLR3 members) — retained as a flagged contradiction, not
> evidence of a chicken RIG-I orthologue.

---

## Summary of edits on approval

| Model | Stage | Edit |
|-------|-------|------|
| spread | reservoir | desc rewrite + diverges entry |
| spread | timing | desc rewrite |
| spread | (new) diverges[] | bridge, routes entries |
| infection | cytokine_storm | desc append + diverges entry |
| infection | celldeath | desc append |
| infection | (new) diverges[] | sensing flag |

Version bumps: infection v0.5→v0.6, spread v0.2→v0.3.
