# job-tracker

Watchlist scan for FDE / APM / product-internship roles at a fixed list of
companies, published as a static tracker site. It is run on demand, not on a
schedule.

## Run

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

## Sources

Only the watchlist companies' own career boards are scanned. The supplemental
sources live behind the `enabled` flags in `sources.json` and are all off:

| flag | source |
| --- | --- |
| `github_lists` | SimplifyJobs / vanshb03 new-grad + internship lists |
| `vc_boards` | a16z, Sequoia, Lightspeed, Kleiner, General Catalyst, Accel portfolio boards (off-watchlist hits are tagged `discover`) |
| `feeds` | newsletter RSS hiring mentions, shown on the Signals tab |
| `x` | X account hiring posts, also Signals; rate-limits to ~30 requests per window |

`refresh.sh` skips the scraper and `build_site.py` ignores its `data/*_raw.json`
when a flag is false, so flipping one back on takes effect on the next run with
no code change. The rest of `sources.json` (board ids, feed urls, X handles) and
the watchlist in `companies.py` are likewise editable by hand.

## Layout

- `companies.py` — watchlist and priority tiers, alias canonicalization.
- `roles.py` — the narrow relevance classifier (FDE, APM/early-career PM,
  product interns, SWE interns; excludes senior, manager, solutions-architect
  and other adjacent titles).
- `experience.py` — years-of-experience parsing from job descriptions (>3 yrs is
  dropped).
- `scrape_companies.py` — Greenhouse / Ashby / Lever boards plus the Amazon and
  NVIDIA job APIs.
- `scrape_github.py` — supplemental new-grad / internship GitHub lists, filtered
  down to watchlist companies.
- `scrape_vc.py`, `scrape_feeds.py`, `scrape_x.py` — the other supplemental
  sources; see the table above.
- `sources.json` — source configuration and the on/off flags.
- `build_site.py` — writes `site/jobs.json`.
- `site/index.html` — the tracker UI (state kept in browser localStorage).
- `find_boards.py`, `find_boards2.py` — one-off board discovery, writes
  `data/boards.json`.
- `scrape_linkedin.py`, `enrich_linkedin.py` — legacy, must not run.
