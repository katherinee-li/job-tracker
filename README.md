# job-tracker

Daily watchlist scan for FDE / APM / product-internship roles at a fixed list of
companies, published as a static tracker site.

## Daily run

```bash
pip install requests beautifulsoup4
./refresh.sh          # scrape -> build -> copy into kathyjobs/ -> print new roles
```

`refresh.sh` ends with `daily.py`, which diffs `site/jobs.json` against
`data/seen.json` and prints a Slack-ready list of only the roles that appeared
since the last run. Commit `data/seen.json` after each run so the next run knows
what is new. Output markers: `SCRAPE_EMPTY` (scrape produced nothing — treat as a
failure, do not deploy), `NO_NEW_ROLES`, or the summary itself.

Then deploy the `kathyjobs/` directory as a static frontend to
https://kathyjobs-eeszqlct.devinapps.com

## Layout

- `companies.py` — watchlist and priority tiers, alias canonicalization.
- `roles.py` — the narrow relevance classifier (FDE, APM/early-career PM,
  product interns, SWE interns; excludes senior, manager, solutions-architect
  and other adjacent titles).
- `experience.py` — years-of-experience parsing from job descriptions (>3 yrs is
  dropped).
- `scrape_companies.py` — Greenhouse / Ashby / Lever boards plus the Amazon and
  NVIDIA job APIs.
- `scrape_github.py` — supplementary new-grad / internship GitHub lists, filtered
  down to watchlist companies.
- `build_site.py` — writes `site/jobs.json`.
- `site/index.html` — the tracker UI (state kept in browser localStorage).
- `find_boards.py`, `find_boards2.py` — one-off board discovery, writes
  `data/boards.json`.
- `scrape_linkedin.py`, `enrich_linkedin.py` — legacy, not part of the daily run.
