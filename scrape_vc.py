"""Scan VC portfolio job boards for the handful of roles worth surfacing.

Two board platforms cover most of the big funds:

* Consider (a16z, Sequoia, Lightspeed, Kleiner Perkins) — POST /api-boards/search-jobs
  behind a CSRF token lifted from the board page, paged with meta.sequence.
* Getro (General Catalyst, Accel) — POST api.getro.com/.../search/jobs, plain keyword
  search, paged with `page`.

Unlike scrape_companies.py this is discovery: the companies are not on the watchlist,
so build_site.py keeps these under the "discover" tier.
"""

import http.cookiejar
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "vc_raw.json"
SOURCES = ROOT / "sources.json"

# Consider board title slugs and the Getro free-text queries that mirror them.
TITLE_SLUGS = [
    "forward-deployed-engineer",
    "forward-deployed-software-engineer",
    "associate-product-manager",
    "product-manager",
    "product-manager-intern",
    "product-management-intern",
    "product-intern",
]
KEYWORD_QUERIES = [
    "forward deployed engineer",
    "associate product manager",
    "product manager intern",
    "product management intern",
    "new grad product manager",
]
PAGE = 100
MAX_PAGES = 6


def opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    return op


def post(op, url, payload, headers=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            **(headers or {}),
        },
    )
    with op.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def consider(board, host, out):
    """Consider-hosted board (a16z & co)."""
    op = opener()
    page = op.open(f"https://{host}/jobs", timeout=60).read().decode()
    m = re.search(r'"csrfToken":"([^"]+)"', page)
    if not m:
        print(f"{board}: no csrf token, skipped")
        return
    token = m.group(1)
    url = f"https://{host}/api-boards/search-jobs"
    kept = 0
    for slug in TITLE_SLUGS:
        sequence = None
        for _ in range(MAX_PAGES):
            meta = {"size": PAGE}
            if sequence:
                meta["sequence"] = sequence
            try:
                res = post(
                    op,
                    url,
                    {
                        "meta": meta,
                        "board": {"id": board, "isParent": True},
                        "query": {"titlePrefix": slug, "promoteFeatured": True},
                    },
                    {"x-csrf-token": token},
                )
            except Exception as exc:  # noqa: BLE001
                print(f"{board}/{slug}: {exc}")
                break
            jobs = res.get("jobs") or []
            for j in jobs:
                url_ = j.get("url") or j.get("applyUrl")
                if not url_:
                    continue
                ts = j.get("timeStamp")
                out[url_] = {
                    "title": (j.get("title") or "").strip(),
                    "url": url_,
                    "company": (j.get("companyName") or j.get("companyId") or "").strip(),
                    "location": ", ".join(j.get("locations") or [])
                    or ("Remote" if j.get("remote") else ""),
                    "footer": "",
                    "min_exp": j.get("minYearsExp"),
                    "source": f"vc:{board}",
                    "posted_ts": iso_ts(ts),
                    "scraped_at": time.strftime("%Y-%m-%d"),
                }
                kept += 1
            sequence = (res.get("meta") or {}).get("sequence")
            if len(jobs) < PAGE or not sequence:
                break
    print(f"{board}: {kept} postings")


def getro(collection, name, out):
    """Getro-hosted network (General Catalyst, Accel)."""
    op = opener()
    url = f"https://api.getro.com/api/v2/collections/{collection}/search/jobs"
    kept = 0
    for query in KEYWORD_QUERIES:
        for page in range(MAX_PAGES):
            try:
                res = post(op, url, {"hitsPerPage": PAGE, "page": page, "query": query})
            except Exception as exc:  # noqa: BLE001
                print(f"{name}/{query}: {exc}")
                break
            jobs = (res.get("results") or {}).get("jobs") or []
            for j in jobs:
                if not j.get("url"):
                    continue
                org = j.get("organization") or {}
                out[j["url"]] = {
                    "title": (j.get("title") or "").strip(),
                    "url": j["url"],
                    "company": (org.get("name") or "").strip(),
                    "location": ", ".join((j.get("searchable_locations") or [])[:2])
                    or ("Remote" if j.get("work_mode") == "remote" else ""),
                    "footer": "",
                    "min_exp": None,
                    "source": f"vc:{name}",
                    "posted_ts": j.get("created_at"),
                    "scraped_at": time.strftime("%Y-%m-%d"),
                }
                kept += 1
            if len(jobs) < PAGE:
                break
    print(f"{name}: {kept} postings")


def iso_ts(value):
    if not value:
        return None
    try:
        return int(time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))
    except (ValueError, TypeError):
        return None


def main():
    cfg = json.loads(SOURCES.read_text())
    out = {}
    for b in cfg.get("consider_boards", []):
        consider(b["board"], b["host"], out)
    for b in cfg.get("getro_networks", []):
        getro(b["collection"], b["name"], out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(list(out.values()), indent=2))
    print(f"saved {len(out)} VC-board postings -> {OUT}")


if __name__ == "__main__":
    main()
