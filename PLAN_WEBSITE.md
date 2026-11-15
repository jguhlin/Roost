# Website Scaffold Plan

## Architecture

```
roost/
├── scripts/           # Data pipeline (existing)
├── data/              # Generated data (existing, not in git)
└── web/               # NEW: Website (separate from data pipeline)
    ├── src/
    ├── public/
    │   └── data/      # Exported data for web (copied from ../data/)
    └── package.json
```

## Tech Stack

- **Framework:** Vite + vanilla JS (or Svelte if preferred)
- **Data queries:** DuckDB-WASM
- **Maps:** MapLibre GL JS
- **Styling:** Tailwind CSS
- **Hosting:** Static (GitHub Pages / Vercel / Netlify)

## Data Flow

```
data/*.parquet  ──►  web/public/data/  ──►  DuckDB-WASM (browser)
data/geojson/   ──►  web/public/data/  ──►  MapLibre GL
```

## Pages / Components

1. **Home** - Overview stats, recent detections
2. **Species Explorer** - Search, filter by order/family/susceptibility
3. **Detection Map** - Interactive map with filtering
4. **Species Detail** - Per-species page (pre-rendered JSON + dynamic)
5. **Downloads** - Bulk data exports (parquet, CSV, GeoJSON)

## Status (2026-08-29)

- [x] Phase 1: Scaffold (Svelte 5 chosen over vanilla JS)
- [x] Phase 2: Core features (species search, detection map, filters)
- [x] Phase 3: Detail pages (species modal, timelines, susceptibility)
- [x] Phase 4: Downloads & polish (download center, Papers/Resources routes added)
- [ ] Phase 5: Wiki-style knowledge pages — see `docs/PLAN_WIKI.md`

## Implementation Phases

### Phase 1: Scaffold
- [x] Initialize Vite project in `web/`
- [x] Add DuckDB-WASM, MapLibre, Tailwind
- [x] Create data export script (copy parquet/geojson to web/public/data/)
- [x] Basic layout with navigation

### Phase 2: Core Features
- [x] Species list with client-side search
- [x] Detection map with GeoJSON layers
- [x] Basic filtering (order, family, country)

### Phase 3: Detail Pages
- [x] Species detail pages (modal with tabs)
- [x] Detection timeline charts
- [x] Susceptibility display

### Phase 4: Downloads & Polish
- [x] Download center
- [x] Papers + Resources routes
- [ ] Mobile responsive audit
- [ ] Performance optimization (code-splitting; bundle is 1.3 MB)

### Phase 5: Knowledge Pages (wiki)
- [ ] Gene / mutation / species synthesis pages from LLM corpus
- [ ] See `docs/PLAN_WIKI.md` for design

## Data Export Script

New script: `scripts/export_web_data.py`
- Copies/optimizes parquet files for web
- Generates search index JSON
- Copies GeoJSON layers

## Questions to Resolve

1. ~~Framework: Vite + vanilla JS, or add Svelte/React?~~ → **Svelte 5**
2. ~~Routing: Hash-based (#/species/123) or file-based?~~ → **Hash-based**
3. ~~Search: DuckDB full-text or separate search index (Fuse.js)?~~ → **Custom JSON index + DuckDB hybrid**
4. Where do wiki pages live — new `#/wiki/*` namespace or extend existing routes (genes/species)? → extend existing routes first, see PLAN_WIKI.md
