"""Watch X accounts for hiring posts.

Uses X's public syndication timeline (the same feed that powers embedded tweets),
so it needs no login, no API key and no stored session: one request per handle in
sources.json's `x_accounts`. Only posts that read like a hiring announcement and
mention a role worth surfacing are kept, and they land on the Signals tab.
"""

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "x_raw.json"
SOURCES = ROOT / "sources.json"
TIMELINE = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
MAX_AGE_DAYS = 21
RATE_WAIT_CAP = 20 * 60

HIRING_RE = re.compile(
    r"(hiring|we'?re looking for|join (?:us|our|the team)|open role|open position|"
    r"apply (?:here|now)|come build|careers?\b|recruiting|new grad|internship)",
    re.I,
)
ROLE_RE = re.compile(
    r"(forward.deployed|\bfde\b|product manager|\bapm\b|product intern|"
    r"associate product|new grad|intern(ship)?\b|co.?op)",
    re.I,
)
NEXT_DATA_RE = re.compile(r'id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def fetch(handle):
    """Syndication allows ~30 requests per window; wait out a 429 once."""
    req = urllib.request.Request(
        TIMELINE.format(handle=handle),
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            reset = exc.headers.get("x-rate-limit-reset") if exc.headers else None
            wait = int(reset) - time.time() + 5 if reset else 60
            if exc.code != 429 or attempt or not 0 < wait <= RATE_WAIT_CAP:
                raise
            print(f"rate limited, waiting {int(wait)}s")
            time.sleep(wait)
    return ""


def tweets(handle):
    m = NEXT_DATA_RE.search(fetch(handle))
    if not m:
        return []
    data = json.loads(m.group(1))
    entries = (
        data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
    )
    out = []
    for e in entries:
        t = (e.get("content") or {}).get("tweet") or {}
        if not t.get("id_str"):
            continue
        out.append(t)
    return out


def parsed_time(value):
    try:
        return int(time.mktime(time.strptime(value, "%a %b %d %H:%M:%S +0000 %Y")))
    except (ValueError, TypeError):
        return None


def main():
    handles = json.loads(SOURCES.read_text()).get("x_accounts", [])
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    out = []
    for handle in handles:
        try:
            posts = tweets(handle)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
            print(f"@{handle}: {exc}")
            continue
        kept = 0
        for t in posts:
            text = t.get("full_text") or t.get("text") or ""
            if not (HIRING_RE.search(text) and ROLE_RE.search(text)):
                continue
            posted = parsed_time(t.get("created_at"))
            if posted and posted < cutoff:
                continue
            user = (t.get("user") or {}).get("screen_name") or handle
            out.append(
                {
                    "title": re.sub(r"\s+", " ", text)[:180],
                    "url": f"https://x.com/{user}/status/{t['id_str']}",
                    "company": f"@{user}",
                    "snippet": re.sub(r"\s+", " ", text)[:400],
                    "links": [
                        u["expanded_url"]
                        for u in ((t.get("entities") or {}).get("urls") or [])
                        if u.get("expanded_url")
                    ],
                    "source": "x",
                    "posted_ts": posted,
                    "scraped_at": time.strftime("%Y-%m-%d"),
                }
            )
            kept += 1
        print(f"@{handle}: {kept} hiring posts of {len(posts)}")
        time.sleep(4)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"saved {len(out)} X hiring posts -> {OUT}")


if __name__ == "__main__":
    main()
