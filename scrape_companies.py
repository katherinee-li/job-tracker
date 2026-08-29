"""Pull postings straight from the watchlist companies' own job boards."""

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

from companies import BOARDS, tier_of
from experience import entry_level, min_years
from roles import classify, kind_of

OUT = Path(__file__).parent / "data" / "companies_raw.json"
MAX_AGE_DAYS = 45
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"


def get(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def stamp(value):
    if not value:
        return None
    try:
        return time.mktime(time.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html or "")))


def add(out, company, title, url, location, posted_ts, desc):
    role = classify(title)
    if not role or not url:
        return
    if posted_ts and (time.time() - posted_ts) > MAX_AGE_DAYS * 86400:
        return
    text = plain(desc)
    exp = min_years(text)
    if exp is not None and exp > 3:
        return
    out[url] = {
        "title": title,
        "url": url,
        "company": company,
        "location": location or "",
        "role": role[0],
        "track": role[1],
        "kind": kind_of(title),
        "tier": tier_of(company),
        "min_exp": exp,
        "entry_level": entry_level(text),
        "source": "company",
        "footer": "",
        "posted_ts": posted_ts,
        "scraped_at": time.strftime("%Y-%m-%d"),
    }


def greenhouse(out, company, slug):
    jobs = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")["jobs"]
    for j in jobs:
        add(out, company, j["title"], j["absolute_url"],
            (j.get("location") or {}).get("name", ""),
            stamp(j.get("updated_at")), j.get("content"))
    return len(jobs)


def ashby(out, company, slug):
    jobs = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")["jobs"]
    for j in jobs:
        add(out, company, j["title"], j.get("jobUrl") or j.get("applyUrl"),
            j.get("location") or "", stamp(j.get("publishedAt")),
            j.get("descriptionPlain") or "")
    return len(jobs)


def lever(out, company, slug):
    jobs = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    for j in jobs:
        ts = j.get("createdAt")
        add(out, company, j["text"], j.get("hostedUrl") or j.get("applyUrl"),
            (j.get("categories") or {}).get("location", ""),
            ts / 1000 if ts else None,
            (j.get("descriptionPlain") or "") + " " + plain(j.get("additionalPlain") or ""))
    return len(jobs)


BOARD_FN = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever}

AMAZON_QUERIES = ["product manager", "forward deployed", "product management intern"]
NVIDIA_QUERIES = ["product manager", "forward deployed", "product intern"]


def amazon(out):
    seen = 0
    for q in AMAZON_QUERIES:
        url = ("https://www.amazon.jobs/en/search.json?result_limit=100&sort=recent"
               f"&base_query={urllib.parse.quote(q)}&country=USA")
        for j in get(url).get("jobs", []):
            seen += 1
            company = "Amazon Robotics" if "robotics" in (j.get("business_category") or "").lower() else "Amazon"
            add(out, company, j["title"], "https://www.amazon.jobs" + j["job_path"],
                j.get("normalized_location") or j.get("location") or "",
                stamp((j.get("posted_date") or "").replace(" ", "T")),
                (j.get("basic_qualifications") or "") + " " + (j.get("description") or ""))
    return seen


def nvidia(out):
    seen = 0
    for q in NVIDIA_QUERIES:
        data = get("https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
                   {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q})
        for j in data.get("jobPostings", []):
            seen += 1
            add(out, "NVIDIA", j["title"],
                "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite" + j["externalPath"],
                j.get("locationsText") or "", None, j.get("title", ""))
    return seen


def main():
    out = {}
    for company, cfg in BOARDS.items():
        fn = BOARD_FN[cfg["board"]]
        try:
            n = fn(out, company, cfg["slug"])
        except Exception as exc:  # noqa: BLE001
            print(f"{company} ({cfg['board']}) failed: {exc}")
            continue
        print(f"{company}: {n} scanned, {len(out)} kept so far", flush=True)

    for name, fn in (("Amazon", amazon), ("NVIDIA", nvidia)):
        try:
            n = fn(out)
            print(f"{name}: {n} scanned, {len(out)} kept so far", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"{name} failed: {exc}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(list(out.values()), indent=2))
    print(f"saved {len(out)} jobs -> {OUT}")


if __name__ == "__main__":
    main()
