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
| — | Manual source inventory (real URLs for `puc_rss`/`eei_pdf`/`delta_db`) | Done for GA/AZ/EEI (research, 2026-08-03); VA/TX/OH/DELTa blocked, see below |
| — | `puc_rss` pipeline wiring (uses Task 4's fetcher/hash-gate) | Not started — GA & AZ now have real, verified URLs and are `active: true` |
| — | EEI PDF fetcher | Not started — URL verified live and public, `active: true` |
| — | DELTa DB fetcher | Not started, blocked — see open risks |
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
- **Source inventory findings (2026-08-03):** researched and directly
  verified (via `curl` with the project's real User-Agent, not just search)
  all 7 remaining pilot sources:
  - **GA, AZ (`puc_rss`), EEI (`eei_pdf`) — live and activated** in
    `sources.yaml`. All three returned 200 with real content and no
    robots.txt restriction.
  - **VA (`puc_rss`) — deliberately not configured.** `scc.virginia.gov`'s
    robots.txt disallows generic bots (`Disallow: /` catch-all, only a
    named-crawler allowlist permitted). Logged to `sources_skipped.md` per
    the politeness rule rather than worked around. No alternative VA source
    found this pass.
  - **TX (`puc_rss`) — blocked, needs retry.** `www.puc.texas.gov` fails at
    the TLS/connection level (cert chain issue) from this environment.
    Could be transient or environment-specific — worth retrying from a
    different network before concluding it's unfetchable.
  - **OH (`puc_rss`) — blocked, needs retry.** `puco.ohio.gov` 404s on every
    path tried (news page, home, root), consistent with WAF blocking
    non-browser clients. Needs a human to check the site directly and find
    a working path, if one exists.
  - **DELTa (`delta_db`) — blocked, needs a different approach.**
    `sepapower.org/large-load-tariffs-database/` 403s despite robots.txt
    technically allowing it — looks like Cloudflare-style bot protection
    that a plain polite `httpx` GET won't get past regardless of User-Agent.
    No hidden JSON/API endpoint found. Options for later: manual periodic
    export instead of automated fetch, or a deeper look at the page's
    network requests to find a non-blocked backing endpoint.
  - **3 of 4 lanes now have at least one live source** (`legiscan` was
    already live; `puc_rss` now partially live via GA/AZ; `eei_pdf` live).
    `delta_db` remains fully blocked — the `tax_incentive` domain has no
    working source yet.
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
