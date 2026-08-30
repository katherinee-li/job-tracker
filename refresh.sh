#!/usr/bin/env bash
# Daily refresh: re-scan the watchlist boards, rebuild the site payload.
set -euo pipefail
cd "$(dirname "$0")"
python scrape_companies.py
python scrape_github.py
python scrape_vc.py
python scrape_feeds.py
# X is off by default: syndication rate-limits to ~30 requests per window, so a
# full pass over sources.json's x_accounts can stall the run. Enable with X=1.
[ "${X:-0}" = "1" ] && python scrape_x.py || true
python build_site.py
cp site/index.html site/jobs.json kathyjobs/
python daily.py
