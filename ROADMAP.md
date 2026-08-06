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
**All 4 pilot lanes now have a working pipeline as of PR #15** —
`legiscan`, `puc_rss`, `eei_pdf` fetch automatically; `delta_db` is a
manual drop-in lane. Every lane feeds the digest.

| Task | What | Status |
|---|---|---|
| 1 | Repo scaffold (uv, package layout, CI/cron workflows) | Done — pushed directly (first commit, no base to PR against) |
| 2 | `sources.yaml` format + pydantic models, 5-state pilot stubs | Done — PR #1 |
| 3 | LegiScan client + per-bill change detection, SQLite introduced | Done — PR #2 |
| 4 | Normalize + hash-gate for HTML sources (PUC RSS) | Done — PR #4 |
| 5 | `digest.md` renderer v0 (LegiScan lane only) | Done — PR #6 |
| — | Manual source inventory (real URLs for `puc_rss`/`eei_pdf`/`delta_db`) | Done for GA/AZ/TX/EEI; VA/OH deliberately skipped, DELTa blocked, see below |
| — | `puc_rss` pipeline wiring (uses Task 4's fetcher/hash-gate) | Done — PR #11. Live for GA/AZ/TX; digest.md now shows both `legiscan` and `puc_rss` lanes, labeled per state |
| — | EEI PDF fetcher | Done — PR #13. Hash-gates only the "LARGE LOAD TARIFFS" section; digest.md now has a National section |
| — | DELTa DB fetcher | Done — PR #15. Manual drop-in lane (`data/manual/delta_db/`), not automated fetch — see decisions log |
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
- **`hash_gate.check_for_change` gained an optional `url` param** so
  `puc_rss`'s `diff_summary` can say `"Page content changed — <url>"`
  instead of the generic `"content changed"` — same reasoning as the
  `legiscan_pipeline` change above. Default `None` preserves the old
  behavior for any future lane that doesn't have a natural URL.
- **`digest.py` renders multiple lanes per state, not just LegiScan.**
  Generalized to loop over `[("legiscan", "Legislation"), ("puc_rss",
  "PUC Tariff")]`, with each bullet labeled by lane. Confirmed with the
  user before doing this, since Task 5 deliberately scoped the digest to
  LegiScan-only — but leaving a live lane's changes unrendered defeats the
  point of wiring it.
- **EEI PDF hash-gating is scoped to just the "LARGE LOAD TARIFFS"
  section, not the whole document.** The PDF also has a "Large Load
  Projects" section (general project announcements) that churns far more
  often than actual tariff dockets — hashing the whole document would
  mean "changed" fires on routine project news even when nothing
  tariff-relevant moved. Located via a text marker; the full PDF is still
  stored raw regardless. Confirmed with the user before implementing.
- **`html_fetcher.py`'s robots.txt logic moved into a shared `robots.py`**
  so the new `pdf_fetcher.py` could reuse it without duplication. Pure
  refactor, `html_fetcher.py`'s external behavior/tests unchanged.
- **`hash_gate.py` split into a generic `record_change` core and a thin
  `check_for_change` HTML-specific wrapper.** PDF-extracted plain text
  needed hash-gating without going through HTML normalization
  (`normalize_html` parses with `selectolax`, wrong for non-HTML text).
  `check_for_change`'s signature/behavior is unchanged for existing
  callers (`puc_rss_pipeline.py`).
- **New dependency: `pypdf`** — chosen over `pdfplumber` for text
  extraction since this task only needed section-based text hashing, not
  structured table parsing (deferred to the later LLM-extraction phase,
  same limitation as every other lane so far — a detected change means
  "the tariff section changed," not "here's what changed").
- **DELTa is a manual drop-in lane, not an automated fetch.** Confirmed
  via direct investigation: `sepapower.org` returns a genuine Cloudflare
  JS/Turnstile challenge (`cf-mitigated: challenge` header), not a UA
  filter — unsolvable without a real browser (out of scope, no
  Playwright). NCCETC's own writeup on DELTa also confirms the database
  is distributed via an email-gated download form, updated quarterly, not
  served as a plain file at all. A human drops the export into
  `data/manual/delta_db/` by hand; `delta_pipeline.py` hashes whatever's
  there as opaque bytes and diffs it, same downstream behavior as every
  other lane. Confirmed this approach with the user before building it.
- **`hash_gate.py` now has three layers**: `record_hash` (bottom —
  precomputed hash, pure DB bookkeeping, used by `delta_pipeline.py`),
  `record_change` (middle — pre-normalized text, used by `eei_pipeline.py`),
  `check_for_change` (top — HTML-specific, used by `puc_rss_pipeline.py`).
  Each wraps the one below it; no signature changes for existing callers
  at any point in this evolution.

## Open questions / risks (not yet decisions)
- **Repo growth from committing raw JSON weekly.** Fine at current
  (legislation-only, 5-state) scale. No pruning/retention story yet. Revisit
  once EEI/DELTa PDFs and more lanes are live and there's real run history
  to look at — not urgent now.
- **Source inventory findings (2026-08-03):** researched and directly
  verified (via `curl` with the project's real User-Agent, not just search)
  all 7 remaining pilot sources:
  - **GA, AZ, TX (`puc_rss`), EEI (`eei_pdf`) — live and activated** in
    `sources.yaml`. All returned 200 with real content and no robots.txt
    restriction. TX needed a follow-up: `www.puc.texas.gov` fails at the
    TLS level (server-side cert chain misconfiguration — doesn't send its
    intermediate cert — not an environment issue), but the bare domain
    `https://puc.texas.gov` works fine and redirects to the same content;
    `sources.yaml` now points at the bare-domain URL directly.
  - **VA (`puc_rss`) — deliberately not configured.** `scc.virginia.gov`'s
    robots.txt disallows generic bots (`Disallow: /` catch-all, only a
    named-crawler allowlist permitted). Logged to `sources_skipped.md` per
    the politeness rule rather than worked around. No alternative VA source
    found this pass.
  - **OH (`puc_rss`) — deliberately not configured (2026-08-04 follow-up).**
    Not a robots.txt issue — `puco.ohio.gov/robots.txt` permits `/news`.
    The site runs a WAF that 404s our real, descriptive User-Agent on every
    path while an identical request with a generic browser UA succeeds
    (confirmed directly). Getting through would mean spoofing a browser UA,
    which contradicts the project's own politeness principle of honestly
    identifying the fetcher — chose not to do that. Logged to
    `sources_skipped.md` alongside VA. No automated alternative found.
  - **DELTa (`delta_db`) — resolved via manual drop-in lane (2026-08-06
    follow-up).** `sepapower.org` sits behind a genuine Cloudflare
    JS/Turnstile challenge (`cf-mitigated: challenge`), and the database
    itself is distributed through an email-gated download form, not
    served as a fetchable file — not something any User-Agent or robots.txt
    compliance could get around honestly. See decisions log for the
    manual drop-in lane built instead (`data/manual/delta_db/`).
  - **`puc_rss` is live for 3 of 5 pilot states** (GA, AZ, TX); VA and OH
    are both deliberately excluded (documented in `sources_skipped.md`).
    `legiscan` and `eei_pdf` fetch automatically. `delta_db` is a manual
    drop-in lane. Every pilot lane now has a working pipeline.
  - **Emerging pattern:** every source we've had to route around (VA, OH,
    DELTa) was blocked by something *other* than a clear robots.txt rule —
    a UA-sniffing WAF, or (for DELTa) a real browser challenge plus an
    email-gated distribution model. Worth remembering that "robots.txt
    allows it" doesn't guarantee an honest fetcher can actually get in;
    treat WAF/anti-bot/challenge blocks the same as a robots.txt disallow
    rather than trying to defeat them, and watch for sources whose
    distribution model isn't really "fetch a URL" at all.
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
