"""Pull job listings from the public GitHub new-grad / internship board repos."""

import json
import re
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "data" / "github_raw.json"

SOURCES = [
    ("https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json", "full-time"),
    ("https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json", "intern"),
    ("https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/dev/.github/scripts/listings.json", "intern"),
]

PRODUCT_RE = re.compile(
    r"(product manager|product management|associate product|\bapm\b|product owner|"
    r"forward deployed|solutions engineer|solutions architect|technical program manager)",
    re.I,
)
SOFTWARE_RE = re.compile(
    r"(software engineer|software developer|software development|\bswe\b|backend|"
    r"frontend|full.?stack|machine learning engineer|data engineer)",
    re.I,
)
SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|head of|vp|distinguished)\b", re.I
)
COOP_RE = re.compile(r"co.?op", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "job-tracker"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def kind_of(title, terms, default):
    if COOP_RE.search(title) or any(COOP_RE.search(t) for t in terms):
        return "co-op"
    if default == "intern" or re.search(r"intern", title, re.I):
        return "intern"
    return "full-time"


def main():
    out = {}
    for url, default_kind in SOURCES:
        try:
            listings = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"failed {url}: {exc}")
            continue
        kept = 0
        for x in listings:
            if not x.get("active") or not x.get("is_visible") or not x.get("url"):
                continue
            title = (x.get("title") or "").strip()
            if not title or SENIOR_RE.search(title):
                continue
            category = x.get("category") or ""
            if PRODUCT_RE.search(title) or category.startswith("Product"):
                track = "product"
            elif SOFTWARE_RE.search(title) or category.startswith("Software"):
                track = "software"
            else:
                continue
            terms = x.get("terms") or []
            kind = kind_of(title, terms, default_kind)
            if track == "software":
                if kind == "full-time":
                    continue
                blob = title + " " + " ".join(terms)
                if not re.search(r"fall|spring|co.?op", blob, re.I):
                    continue
            posted = x.get("date_posted")
            out[x["url"]] = {
                "title": title if not terms else f"{title} ({terms[0]})",
                "url": x["url"],
                "company": (x.get("company_name") or "").strip(),
                "location": ", ".join(x.get("locations") or []),
                "footer": "",
                "kind": kind,
                "track": track,
                "source": "github",
                "posted_ts": posted,
                "scraped_at": time.strftime("%Y-%m-%d"),
            }
            kept += 1
        print(f"{url.rsplit('/', 4)[1]}: {kept} kept")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(list(out.values()), indent=2))
    print(f"saved {len(out)} github jobs -> {OUT}")


if __name__ == "__main__":
    main()
