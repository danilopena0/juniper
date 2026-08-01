# Project: juniper — state data center regulation monitor

## What this is
A lightweight pipeline that monitors US state-level data center regulation
(legislation, PUC large-load tariffs, tax incentives, water/siting rules,
moratoria) and maintains a STRUCTURED PARAMETER MATRIX (states × parameters)
plus a weekly change digest. Solo developer + one domain-expert reviewer.
Runs on GitHub Actions cron. No servers.

## Product priorities (in order)
1. Matrix accuracy: every cell = value + primary source URL + as-of date +
   verification status. A wrong MW threshold is worse than a missing one.
2. Change detection: "OH: moratorium threshold 100MW → 75MW" style diffs.
3. Cost discipline: LLM calls ONLY on content whose normalized hash changed.
4. Politeness: honor robots.txt, 1 req/sec max, descriptive User-Agent with
   contact email, weekly cadence. Skip any source whose ToS prohibits
   automated access and log it to `sources_skipped.md`.

## Architecture (do not add components without asking)
sources.yaml → fetchers → normalize → hash-gate → LLM extract → SQLite
→ render (matrix.json, matrix.md, digest.md) → commit

- Python 3.12, uv, httpx, selectolax, pydantic, sqlite3 (stdlib), pytest
- LLM: Anthropic API, claude-sonnet-4-6, structured output via a pydantic
  schema; temperature 0; every extraction stores the source text span
- GitHub Actions: weekly cron; commits db + rendered outputs (git history
  is the audit trail — never rewrite history, never squash)
- NO: Docker, Postgres, queues, Playwright, web frameworks, cloud services

## Data model (SQLite)
- sources(id, state, domain, url, fetcher, selector, active)
- fetches(id, source_id, fetched_at, http_status, raw_path, norm_hash)
- changes(id, source_id, detected_at, prev_hash, new_hash, diff_summary)
- records(id, change_id, state, domain, parameter, value, unit,
  effective_date, source_url, source_quote, confidence,
  status[unverified|verified|corrected|rejected], reviewed_by, reviewed_at)
- Domains: legislation | tariff | tax_incentive | water_siting | moratorium
- Core parameters (extend only via schema PR, never ad hoc):
  mw_threshold, take_or_pay_pct, min_contract_years, collateral_per_mw,
  exit_fee_terms, ramp_period, ciac_required, incentive_min_investment,
  incentive_clawback, moratorium_status, water_permit_trigger,
  bill_status, bill_effective_date

## Pilot scope (hard boundary)
States: TX, VA, OH, GA, AZ. Source lanes: (1) LegiScan API [key in env var
LEGISCAN_API_KEY], (2) PUC press/RSS feeds for the 5 states, (3) EEI
large-load tariff PDF diff, (4) DELTa database diff. Nothing else.

## Workflow rules
- TDD for parsers and diff logic: fixture files in tests/fixtures/ captured
  from real responses; never hit live endpoints in tests.
- Plan mode first for any task touching >2 files; show me the plan.
- Small commits, conventional commits format.
- When a fetcher fails, degrade gracefully: log, mark source stale in the
  digest, never crash the run.
- If a design decision trades accuracy for convenience, stop and ask.

## First session tasks (in order, confirm plan before executing)
1. Scaffold: uv project, package layout (juniper/{fetch,normalize,
   extract,render,review}/), pytest, ruff, GitHub Actions workflow
   (cron + CI), .env.example, this file saved as CLAUDE.md.
2. sources.yaml format + pydantic models for it, with the 5-state pilot
   entries stubbed (I'll fill real URLs from my manual inventory).
3. LegiScan client: search endpoint with keyword list ["data center",
   "large load", "colocation", "digital infrastructure"], per-state,
   using their change_hash for delta detection; store raw JSON.
4. Normalize + hash-gate for HTML sources (strip nav/scripts/timestamps/
   session tokens before hashing) with tests proving stable hashes across
   cosmetic page changes.
5. digest.md renderer v0: new/changed items grouped by state, LegiScan
   lane only.
Stop after each task; I review before the next.

## Definition of done for the PoC
A GitHub Actions run that: fetches all pilot sources, detects deltas,
extracts structured records for changed items, renders matrix.md +
digest.md, commits — for under $1 of LLM spend per weekly run — and a
domain expert can trace any matrix cell to its primary source in one click.
