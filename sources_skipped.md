# Skipped sources

Sources deliberately not configured because automated access is disallowed.
Per `CLAUDE.md`'s politeness rule: honor robots.txt, skip anything a site's
own rules prohibit rather than working around it.

## Virginia SCC — press releases (`puc_rss` lane)

- **Candidate URL:** `https://www.scc.virginia.gov/about-the-scc/newsreleases/`
- **Checked:** 2026-08-03
- **Reason:** `https://www.scc.virginia.gov/robots.txt` explicitly disallows
  generic bots — the catch-all rule is `User-agent: * / Disallow: /`, and
  only a short allowlist of named crawlers (Googlebot, Bingbot,
  DuckDuckBot, SiteimproveBot, msnbot, Terminalfour Nutch Spider) are
  permitted. Our fetcher's User-Agent (`juniper-regtracker/0.1`) is not on
  that list, so fetching this URL would violate the site's stated policy.
- **Status:** Not configured in `sources.yaml` (left `active: false`,
  `url: null` for VA's `puc_rss` entry). No automated alternative found for
  Virginia's large-load tariff/regulatory news during this pass — would
  need a different source (e.g. a specific docket search page, if one
  exists with a permissive robots.txt) to cover VA in this lane.
