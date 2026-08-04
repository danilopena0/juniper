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

## Ohio PUCO — news releases (`puc_rss` lane)

- **Candidate URL:** `https://puco.ohio.gov/news`
- **Checked:** 2026-08-04
- **Reason:** Not a robots.txt violation — `https://puco.ohio.gov/robots.txt`
  is permissive for this path (`User-agent: * / Disallow:` only lists a few
  internal admin/search paths, not `/news`). Instead, the site runs a WAF
  that blocks requests by User-Agent string: our real, descriptive UA
  (`juniper-regtracker/0.1 (contact: danilopena93@gmail.com)`) gets a 404 on
  every path tried, while an identical request using a generic browser UA
  string (`Mozilla/5.0 ... Chrome/124.0 ...`) succeeds and returns real
  content. Search engines are indexed fine, so this is specifically aimed
  at non-browser/bot clients.
- **Decision:** Getting past this would require our fetcher to send a
  browser-spoofed User-Agent instead of honestly identifying itself —
  which the site is evidently trying to prevent, even though it didn't say
  so via robots.txt. Chose not to do that; it contradicts the project's own
  "descriptive User-Agent with contact email" politeness principle. Left
  unconfigured (`active: false`, `url: null`) rather than worked around.
- **Status:** No automated alternative found for Ohio's large-load
  tariff/regulatory news during this pass.
