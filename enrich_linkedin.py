"""Fetch LinkedIn job descriptions to tag postings by required experience."""

import json
import random
import re
import time
import urllib.request
from pathlib import Path

from experience import entry_level, min_years

RAW = Path(__file__).parent / "data" / "linkedin_raw.json"
GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"


def description(url):
    m = re.search(r"/jobs/view/(\d+)", url)
    if not m:
        return None
    req = urllib.request.Request(GUEST.format(m.group(1)), headers={"User-Agent": UA})
    html = None
    for attempt in range(4):
        try:
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    if html is None:
        return None
    body = re.search(r'class="[^"]*show-more-less-html__markup[^"]*"(.*?)</div>', html, re.S)
    text = body.group(1) if body else html
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))


def main():
    jobs = json.loads(RAW.read_text())
    todo = [j for j in jobs if "/jobs/view/" in j["url"] and "min_exp" not in j]
    print(f"fetching {len(todo)} descriptions")
    hits = 0
    for i, j in enumerate(todo, 1):
        text = description(j["url"])
        time.sleep(random.uniform(1.0, 2.0))
        if text is None:
            continue
        hits += 1
        j["min_exp"] = min_years(text)
        j["entry_level"] = entry_level(text)
        if i % 25 == 0:
            RAW.write_text(json.dumps(jobs, indent=2))
            print(f"{i}/{len(todo)} ({hits} ok)", flush=True)
    RAW.write_text(json.dumps(jobs, indent=2))
    print(f"enriched {hits}/{len(todo)} -> {RAW}")


if __name__ == "__main__":
    main()
