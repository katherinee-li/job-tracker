"""Scrape LinkedIn job search results using the already-logged-in Chrome via CDP."""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:29229"
OUT = Path(__file__).parent / "data" / "linkedin_raw.json"

QUERIES = [
    "forward deployed engineer",
    "associate product manager",
    "product manager new grad",
    "product management intern",
    "solutions engineer new grad",
    "technical product manager new grad",
    "product intern 2027",
    "product management co-op",
    "product co-op fall",
    "product management co-op spring",
    "associate product manager co-op",
]

SOFTWARE_QUERIES = [
    "software engineering co-op fall",
    "software engineer co-op spring",
    "software engineering intern fall",
    "software engineering intern spring",
    "software developer co-op",
    "software engineering intern 2026",
]

PAGES = 3

TARGET_COMPANIES = [
    "google", "meta", "stripe", "databricks", "fireworks", "cognition", "exa",
    "openai", "anthropic", "scale ai", "notion", "figma", "ramp", "linear",
    "vercel", "perplexity", "sierra", "harvey", "glean", "airtable", "retool",
    "snowflake", "palantir", "datadog", "plaid", "brex", "rippling", "mercor",
    "anysphere", "cursor", "modal", "together ai", "baseten", "sourcegraph",
]

SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|head of|manager ii|iii|iv|"
    r"vp|president|distinguished)\b",
    re.I,
)
ROLE_RE = re.compile(
    r"(forward deployed|product manager|product management|associate product|"
    r"\bapm\b|solutions engineer|solutions architect|product analyst|"
    r"technical program manager|product owner)",
    re.I,
)
SOFTWARE_RE = re.compile(
    r"(software engineer|software developer|software development|swe\b|"
    r"backend engineer|frontend engineer|full.?stack|machine learning engineer|"
    r"data engineer|engineering co.?op)",
    re.I,
)
EARLY_RE = re.compile(r"(intern|co.?op|new.?grad|university|campus|entry.level)", re.I)


def search(page, query, geo="United States", start=0):
    url = (
        "https://www.linkedin.com/jobs/search/?keywords="
        + quote_plus(query)
        + "&location="
        + quote_plus(geo)
        + f"&f_TPR=r2592000&sortBy=DD&start={start}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(10):
        page.evaluate(
            """() => {
                const list = document.querySelector('.scaffold-layout__list > div, .jobs-search-results-list');
                if (list) list.scrollBy(0, 1200); else window.scrollBy(0, 1200);
            }"""
        )
        page.wait_for_timeout(900)
    cards = page.evaluate(
        """() => Array.from(document.querySelectorAll('li[data-occludable-job-id], div.job-card-container'))
            .map(li => {
                const a = li.querySelector('a.job-card-container__link, a.job-card-list__title--link, a[href*="/jobs/view/"]');
                const txt = s => { const e = li.querySelector(s); return e ? e.innerText.trim() : ''; };
                return {
                    title: a ? a.innerText.split('\\n')[0].trim() : '',
                    url: a ? a.href.split('?')[0] : '',
                    company: txt('.artdeco-entity-lockup__subtitle') || txt('.job-card-container__primary-description'),
                    location: txt('.job-card-container__metadata-wrapper') || txt('.artdeco-entity-lockup__caption'),
                    footer: txt('.job-card-container__footer-wrapper')
                };
            }).filter(j => j.url)"""
    )
    return cards


def classify(job, track="product"):
    title = job["title"]
    if SENIOR_RE.search(title):
        return None
    if track == "software":
        if not (SOFTWARE_RE.search(title) and EARLY_RE.search(title)):
            return None
    elif not ROLE_RE.search(title):
        return None
    if re.search(r"co.?op", title, re.I):
        kind = "co-op"
    elif re.search(r"intern", title, re.I):
        kind = "intern"
    else:
        kind = "full-time"
    job["track"] = track
    company = (job.get("company") or "").lower()
    tier = "other"
    for c in TARGET_COMPANIES:
        if c in company:
            tier = "target"
            break
    job["kind"] = kind
    job["tier"] = tier
    return job


def main():
    results = {}
    if OUT.exists():
        for j in json.loads(OUT.read_text()):
            j.setdefault("track", "product")
            results[j["url"]] = j
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0]
        page = ctx.new_page()
        product_queries = list(QUERIES) + [
            f"{c} product manager" for c in ("Stripe", "Databricks", "Google", "Meta")
        ] + [f"{c} forward deployed" for c in ("Cognition", "Fireworks AI", "Exa")]
        queries = [(q, "product") for q in product_queries] + [
            (q, "software") for q in SOFTWARE_QUERIES
        ]
        for q, track in queries:
            for start in range(0, PAGES * 25, 25):
                try:
                    cards = search(page, q, start=start)
                except Exception as exc:  # noqa: BLE001
                    print(f"query failed: {q} @{start}: {exc}", file=sys.stderr)
                    continue
                kept = 0
                for c in cards:
                    job = classify(dict(c), track)
                    if job:
                        job["query"] = q
                        job["scraped_at"] = time.strftime("%Y-%m-%d")
                        results[job["url"]] = job
                        kept += 1
                print(f"{q} @{start}: {len(cards)} cards, {kept} kept", flush=True)
                if not cards:
                    break
                page.wait_for_timeout(1500)
        page.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(list(results.values()), indent=2))
    print(f"saved {len(results)} jobs -> {OUT}")


if __name__ == "__main__":
    main()
