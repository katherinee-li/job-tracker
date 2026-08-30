"""Watch newsletter / blog RSS feeds for hiring signals.

Substack (and most blogs) expose a public feed at /feed, so this needs no account.
Posts are not job postings, so anything found here lands on the tracker's Signals
tab rather than the job lists: the value is spotting a company that just raised or
just announced a team before the role shows up on a board.
"""

import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "feeds_raw.json"
SOURCES = ROOT / "sources.json"
MAX_AGE_DAYS = 30

HIRING_RE = re.compile(
    r"(we(?:'| a)?re hiring|now hiring|join(?:ing)? (?:our|the) team|open roles?|"
    r"open positions?|careers page|apply here|hiring for|first (?:pm|product) hire|"
    r"forward.deployed|founding engineer|associate product manager|\bapm\b|internship)",
    re.I,
)
JOB_LINK_RE = re.compile(
    r"https?://[^\s\"'<>]*(?:greenhouse\.io|ashbyhq\.com|lever\.co|jobs\.[a-z0-9.-]+|"
    r"[a-z0-9.-]+/careers|workatastartup\.com)[^\s\"'<>]*",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def text_of(node):
    return html.unescape(TAG_RE.sub(" ", node or "")).strip()


def parse_date(value):
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return int(time.mktime(time.strptime(value, fmt)))
        except (ValueError, TypeError):
            continue
    return None


def main():
    feeds = json.loads(SOURCES.read_text()).get("feeds", [])
    out = []
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    for feed in feeds:
        try:
            root = ET.fromstring(fetch(feed["url"]))
        except Exception as exc:  # noqa: BLE001
            print(f"failed {feed['name']}: {exc}")
            continue
        kept = 0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            posted = parse_date(item.findtext("pubDate"))
            if posted and posted < cutoff:
                continue
            body = " ".join(
                filter(None, [item.findtext("description"), item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")])
            )
            blob = f"{title} {body}"
            if not HIRING_RE.search(blob):
                continue
            links = [u for u in dict.fromkeys(JOB_LINK_RE.findall(body))][:5]
            snippet = text_of(body)
            match = HIRING_RE.search(snippet)
            if match:
                start = max(0, match.start() - 120)
                snippet = ("..." if start else "") + snippet[start : match.end() + 200]
            out.append(
                {
                    "title": title,
                    "url": link,
                    "company": feed["name"],
                    "snippet": snippet[:400],
                    "links": links,
                    "source": f"feed:{feed['name']}",
                    "posted_ts": posted,
                    "scraped_at": time.strftime("%Y-%m-%d"),
                }
            )
            kept += 1
        print(f"{feed['name']}: {kept} hiring signals")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"saved {len(out)} signals -> {OUT}")


if __name__ == "__main__":
    main()
