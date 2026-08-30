#!/usr/bin/env bash
# Refresh: re-scan the watchlist companies' career boards, rebuild the site payload.
# Supplemental sources (GitHub lists, VC portfolio boards, RSS, X) are opt-in —
# flip them on under "enabled" in sources.json.
set -euo pipefail
cd "$(dirname "$0")"

enabled() { python -c "import json,sys;print(json.load(open('sources.json'))['enabled'].get(sys.argv[1]) and 1 or '')" "$1"; }

python scrape_companies.py
if [ -n "$(enabled github_lists)" ]; then python scrape_github.py; fi
if [ -n "$(enabled vc_boards)" ]; then python scrape_vc.py; fi
if [ -n "$(enabled feeds)" ]; then python scrape_feeds.py; fi
if [ -n "$(enabled x)" ]; then python scrape_x.py; fi
python build_site.py
cp site/index.html site/jobs.json kathyjobs/
python daily.py
