# RegTracker (juniper) — Roadmap & Status

Living status doc. `CLAUDE.md` is the spec/contract; this file tracks progress,
decisions, and open questions against it. Update at the end of each task.

## Product framing (do not lose this)
The hero asset is the **matrix** (states × parameters, sourced + dated +
verified), not the weekly digest — the digest is the matrix's changelog.
The moat is **verification** (sourced, versioned via git, human-reviewed),
not LLM extraction. See `CLAUDE.md` for the full spec.

**Kill criteria** (check at each phase gate):
- If the domain-expert reviewer doesn't say "I didn't know that" within 3
  digests → source selection is wrong.
- If Halcyon ships a sub-$500/mo self-serve tier → pivot to water/siting/
  local depth or services instead of competing head-on.
- If 15–20 paying logos don't materialize in 6 months of selling →
  repackage as one-off reports instead of more subscription infra.

## Status

`CLAUDE.md`'s first-session task list (1–5) is complete as of PR #6.

| Task | What | Status |
|---|---|---|
| 1 | Repo scaffold (uv, package layout, CI/cron workflows) | Done — pushed directly (first commit, no base to PR against) |
| 2 | `sources.yaml` format + pydantic models, 5-state pilot stubs | Done — PR #1 |
| 3 | LegiScan client + per-bill change detection, SQLite introduced | Done — PR #2 |
| 4 | Normalize + hash-gate for HTML sources (PUC RSS) | Done — PR #4 |
| 5 | `digest.md` renderer v0 (LegiScan lane only) | Done — PR #6 |
| — | Manual source inventory (real URLs for `puc_rss`/`eei_pdf`/`delta_db`) | **Blocking next steps — user task, not code** |
| — | `puc_rss` pipeline wiring (uses Task 4's fetcher/hash-gate) | Not started, blocked on inventory |
| — | EEI PDF / DELTa DB fetchers | Not started, blocked on inventory |
| — | Wire pipeline + digest into `weekly.yml` (still lint/test only) | Not started |
| — | Extraction (LLM) + `records` table | Not started (later phase) |
| — | `matrix.md` / `matrix.json` render | Not started (later phase) — the hero asset |
| — | Review queue (human verification CLI) | Not started (later phase) |
| — | Distribution (static site, newsletter) | Not started (later phase) |

## Key decisions log
- **`state` is nullable** in the sources schema, representing national/
  multi-state sources (EEI PDF, DELTa DB) without duplicating rows per state.
- **`fetcher` is a closed enum** of exactly the 4 pilot lanes (`legiscan`,
  `puc_rss`, `eei_pdf`, `delta_db`) — matches the pilot's hard scope boundary.
- **`legiscan_bills` is an additive, lane-scoped table**, not a change to
  CLAUDE.md's `changes` schema — LegiScan's per-bill `change_hash` needed
  finer granularity than the one-row-per-fetch `changes` table gives; rather
  than bend that schema, per-bill state lives in its own table and `changes`
  stays exactly as specified (one row per fetch, `diff_summary` listing which
  bills changed).
- **DB (`data/juniper.db`) and raw fetch JSON are git-tracked**, not
  gitignored — per CLAUDE.md, git history is the audit trail.
- **SQLite `UNIQUE`/`ON CONFLICT` don't match on `NULL` columns** (each NULL
  is distinct in SQL) — `sync_sources` uses manual `SELECT ... IS ?` +
  insert-or-update instead of relying on `ON CONFLICT`. Relevant again for
  any future dedup logic on nullable columns.
- **HTML normalization strips whole elements (script/nav/header/footer)
  and hashes visible text only**, rather than special-casing individual
  session-token/attribute names. Timestamps are scrubbed via regex after
  text extraction. This is deliberately generic so it should hold up for
  `puc_rss` pages without per-source tuning — revisit if a real PUC page
  turns out to bury actual content inside a stripped element.
- **`digest_runs` is another additive, lane-agnostic table** (same pattern
  as `legiscan_bills`) so the weekly digest only shows changes since the
  last render instead of re-showing accumulated history every time.
- **`legiscan_pipeline`'s `diff_summary` format changed** from a bare
  comma-joined bill-number list to `"{bill_number}: {title} — {url}"` per
  bill — the digest needed real content to be useful, and the pipeline
  already had that data in hand at write time. No compatibility concern
  since no real weekly runs have happened yet.

## Open questions / risks (not yet decisions)
- **Repo growth from committing raw JSON weekly.** Fine at current
  (legislation-only, 5-state) scale. No pruning/retention story yet. Revisit
  once EEI/DELTa PDFs and more lanes are live and there's real run history
  to look at — not urgent now.
- **Manual source inventory is now the critical-path blocker.** All 5
  first-session tasks are done — the LegiScan lane is fully wired
  (fetch → detect → digest), and the normalize/hash-gate/fetch primitives
  for HTML sources exist and are tested. But real URLs for `puc_rss`,
  `eei_pdf`, `delta_db` are still stubbed (`active: false`, `url: null`),
  so 3 of 4 pilot lanes can't go live and the digest can only ever show
  legislation. This is the single highest-leverage next step, and it's a
  user task (manual inventory), not code.
- **Verification/review-queue layer isn't scheduled into a numbered task
  yet.** It's the actual moat per the strategy doc, but Tasks 1–5 are all
  lane infrastructure + a v0 digest. Keep this visible so scope doesn't
  drift into "add more lanes" before matrix + extraction + review queue
  exist (later phase work).

## Workflow notes
- Every change ships on a feature branch → PR → CI → squash merge into
  `main`. Established starting Task 1's follow-up; the very first commit
  (scaffold) was pushed directly since there was no base to PR against yet.
- Each numbered task gets planned (plan mode) and confirmed before
  execution, per `CLAUDE.md`'s workflow rules.
