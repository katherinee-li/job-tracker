#!/usr/bin/env bash
# Daily refresh: re-scan the watchlist boards, rebuild the site payload.
set -euo pipefail
cd "$(dirname "$0")"
python scrape_companies.py
python scrape_github.py
python build_site.py
cp site/index.html site/jobs.json kathyjobs/
python daily.py
