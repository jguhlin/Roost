# CURRENT_STATUS — what's running / just finished

_Living file: background jobs, long pipelines, and fresh results. Delete
entries when they're absorbed. Last updated 2026-11-06 ~10:00._

## Deployed (2026-11-06 ~18:30)

- **roost-beta-dist-20261106.zip** (134 MB) → sftp'd to the deploy host
  (`$ROOST_DEPLOY_HOST:public_html/Roost/`), unzipped in place, remote zip
  removed. Live-verified: index.html, stats.json (44,930 det / 719 sp,
  generated 2026-11-06T10:48), bird_of_the_day.json (pick: Fulica
  americana, wiki link ✓), kākāpō v5 summary ✓.
- Procedure documented: **docs/DEPLOY.md** + one-command
  **scripts/deploy_dist.sh** (preflight → build → verify → sftp batch →
  unzip -o → live checks). GOTCHA: bg shells here are FISH — no heredocs;
  use sftp `-b batchfile` (the script itself is bash, unaffected).
- Previous zip kept locally as rollback artifact (roost-beta-dist-20261102.zip).

## Running now

(none — regen complete, deploy complete)

## bsky bot — LIVE (2026-11-06)

- **@roost-hpai.bsky.social** authenticated; credentials in
  `bsky-bot/.env`. First posts out: EN curlew blurb + ja translation
  (standalone roots). Three sloppy posts caught + deleted within
  minutes (stale test queue entry; two half-translated/hedged zh) —
  filters hardened: language-purity check, `Word:` prefix guard,
  broader preamble rejection, post_queued honors --multilang,
  post_multilang is ledger-idempotent.
- Tag policy: EN = #HPAI + contextual + #Roost; non-EN drops #HPAI
  (localized disease tag carries the topic — avoids cross-language
  tag spam), #Roost universal.
- 1 follower, reader ledger baseline done. app-password sessions
  CANNOT search (403) — hashtag volume stays empirical.

## Staged, waiting for intake (user decision: WAIT)

- **Book chapters split + staged** (2026-11-06, `scripts/papers/split_book.py`):
  `pdfs_to_process/_split/` holds 65 chapter PDFs ready for intake when
  the user green-lights the new batch —
  - `Avian_Influenza_pdf/` — **Swayne, Avian Influenza (Wiley 2008), 25
    chapters**; the canonical reference — split via display-type openers
    + printed-TOC pairing (no bookmarks in the PDF; color plates shift
    page numbering mid-book)
  - `the-veterinary-vaccinebook_compressed/` — 9 sections (Section IV is
    210 pp of per-disease chapters — a level-2 re-split would give
    per-disease granularity if wanted; not implemented as a flag)
  - `978-981-92-0309-3/` — Green Alternatives to Antibiotics, 31 chapters
    (the `-1` twin file is a duplicate — don't intake both)
- `process_new_papers.py` does NOT glob `_split/` (top-level *.pdf only),
  so the staging is intake-safe. ~160 new top-level PDFs also wait.

## Recently finished (absorb into AGENTS.md already done unless noted)

- **Bird of the Day v2** (commit `7d965654`): locale-first vernaculars
  (en pages show no foreign names), LLM summary on the card, links to
  `#/species-full/{sci}` (the modal route fails for genome-only species —
  known SpeciesDetail gap, unfixed), no assembly chips / roster note.
- **Mobile-width gate + 7 overflow fixes** (commits `b7dd9c6b`,
  `534979ca`): `web/tests/mobile_width.spec.js` (33 routes, own Playwright
  project), root `overflow-x: clip`, verso-dag-viewer + code-token
  phantom roots fixed.
- **Georgia → GEO** + alphabetical named country picker
  (`scripts/model/iso3_names.py`, commit `b7dd9c6b`).

## Environment notes

- **LLM :8005 is UP** (muse-glimmer-30b) but flaky per-call today
  (echo/reasoning phases — translations pass the doctrine filter in
  waves; ko/zh/hi/ja/fr each verified at least once, es pending). The
  multilang bot feature degrades gracefully (filtered locale → skip).
  7-day allocation — check `curl -s localhost:8005/v1/models` before
  new LLM passes.
- **ROADMAP (user 2026-11-06)**: bsky bot should translate and support
  the languages Roost currently supports (en zh hi ja fr es ko) —
  mechanism shipped (translate.py + --multilang reply threads, per-post
  langs tags, doctrine filter); per-locale quality review pending.
- **Dev servers**: 5177 LAN (users), 5178 Playwright fixture — both
  running, leave alone.
- **bsky-bot** (private repo `bsky-bot/`): built, dry-run verified,
  LLM responder live-tested — **awaiting credentials in `.env`** to go
  live. Nothing scheduled (cron recipes in its README).
