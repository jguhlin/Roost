# Localization glossary & style guide (per language)

The refinement sweep (`scripts/papers/i18n_refine.py`) and the translation
pipeline (`scripts/i18n_final.py`) both inject this context. Tokens are not
the constraint — quality is. Extend freely; native-speaker reviews welcome.

## Product context (all languages)

Roost is a scientific web resource for researchers and public-health
staff studying highly pathogenic avian influenza (HPAI/H5N1) in birds and
mammal spillover hosts. It is a DATA DASHBOARD: detection records, host
species, genomes, gene presence/absence, and a literature synthesis.
Audience: virologists, ecologists, genomicists, surveillance officials.
Tone: formal academic/technical UI. Concise labels; complete sentences in
descriptions. Numbers are displayed separately — labels are COUNT LABELS
(detections = number of detection records, not the act of detecting).

## Key-prefix usage hints

nav.* (navigation bar, 1-2 words) · stats.* (KPI card labels, counting
nouns!) · home.* (landing page cards) · species./genes./papers./history./
model./methods_page.* (page titles, section headers, tooltips) ·
common.* (buttons, table states).

## Language notes

### Korean (ko) — native-speaker review 2026-10-07
- genome → 유전체 (NOT 게놈) in formal contexts
- Detections (stat) → 검출 건수 (counting noun; never bare 검출 as a label)
- Affected species → 감염 종; Most affected → 최다 감염 종
- mammals → 포유류; "+n mammals" → 포유류 +n종
- Map (nav) → 분포 지도; Model (nav) → 질병 모델
- host → 숙주; reservoir → 저수숙주/저장숙주 (epidemiological usage:
  저장 숙주 preferred); spillover → 전파/종간 전염 (종간 감염)
- gene presence/absence → 유전자 존재/부재
- Keep BLAST, HPAI, H5N1, IUCN as-is

### Japanese (ja)
- genome → ゲノム (standard loanword OK); detection count → 検出数
- affected species → 感染種; host → 宿主; reservoir → 保有宿主
- spillover → スピルオーバー（種間伝播）; presence/absence → 遺伝子の有無

### Simplified Chinese (zh)
- genome → 基因组; detection count → 检测数; affected species → 感染物种
- host → 宿主; reservoir → 储存宿主; spillover → 跨物种传播
- gene presence/absence → 基因存在/缺失

### Hindi (hi)
- genome → जीनोम; detection count → पता लगाए गए मामलों की संख्या (labels may
  shorten to पताकरण संख्या); host → पोषक; reservoir → संग्रह पोषक
- Keep BLAST/H5N1 as-is

### French (fr)
- genome → génome; detection count → détections (cas détectés)
- affected species → espèces infectées; host → hôte; reservoir → réservoir
- spillover → transmission inter-espèces; presence/absence → présence/absence

### Spanish (es)
- genome → genoma; detection count → detecciones (casos detectados)
- affected species → especies infectadas; host → hospedador/anfitrión
  (hospedador in parasitology/virology); reservoir → reservorio
- spillover → derrame inter-específico / transmisión entre especies
