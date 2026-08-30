"""Turn scraped raw jobs into the site's jobs.json."""

import hashlib
import json
import re
import time
from pathlib import Path

from companies import canonical, tier_of
from roles import classify, kind_of

ROOT = Path(__file__).parent
GITHUB_RAW = ROOT / "data" / "github_raw.json"
COMPANIES_RAW = ROOT / "data" / "companies_raw.json"
VC_RAW = ROOT / "data" / "vc_raw.json"
FEEDS_RAW = ROOT / "data" / "feeds_raw.json"
X_RAW = ROOT / "data" / "x_raw.json"
OUT = ROOT / "site" / "jobs.json"


ROLE_ORDER = {"fde": 0, "apm": 1, "product-intern": 2, "fde-intern": 2, "swe-intern": 3}
TIER_ORDER = {
    "tier1": 0, "big-tech": 1, "robotics": 2, "agents": 3, "ai-infra": 4, "other": 5,
    "discover": 6,
}
MAX_AGE_DAYS = 45


US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
US_NAMES = [
    "united states", "usa", "u.s.", "remote - us", "alabama", "alaska", "arizona", "arkansas",
    "california", "colorado", "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
    "nevada", "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "nyc", "sf", "san francisco",
    "seattle", "boston", "chicago", "austin", "denver", "atlanta", "los angeles", "san jose",
    "palo alto", "mountain view", "bellevue", "redwood city", "menlo park",
]
NON_US_RE = re.compile(
    r"\b(canada|ontario|toronto|vancouver|montreal|uk|united kingdom|london|england|ireland|"
    r"dublin|germany|berlin|munich|france|paris|spain|portugal|lisbon|netherlands|amsterdam|"
    r"switzerland|zurich|sweden|poland|india|bangalore|hyderabad|singapore|japan|tokyo|china|"
    r"korea|australia|sydney|israel|tel aviv|brazil|mexico|argentina|emea|apac|latam)\b",
    re.I,
)


def is_us(location):
    loc = (location or "").strip()
    if not loc:
        return True
    low = loc.lower()
    if any(n in low for n in US_NAMES):
        return True
    if NON_US_RE.search(low):
        return False
    if re.search(r",\s*(" + "|".join(US_STATES) + r")\b", loc):
        return True
    return "remote" in low


def posted_str(ts):
    if not ts:
        return ""
    days = int((time.time() - ts) / 86400)
    if days <= 0:
        return "today"
    return f"{days} day{'s' if days != 1 else ''} ago"


def posted_of(footer):
    m = re.search(r"(\d+\s+(?:minute|hour|day|week|month)s?\s+ago)", footer or "", re.I)
    return m.group(1) if m else ""


UNIT_DAYS = {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}


def age_days(j):
    """How many days ago the posting went up, or None when unknown."""
    m = re.search(
        r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", j.get("footer") or "", re.I
    )
    if m:
        return int(m.group(1)) * UNIT_DAYS[m.group(2).lower()]
    ts = j.get("posted_ts")
    if ts:
        return max(0, int((time.time() - ts) / 86400))
    return None


def load(path):
    return json.loads(path.read_text()) if path.exists() else []


def signals():
    """Newsletter/blog/X hiring mentions — context, not postings."""
    out = []
    for s in load(FEEDS_RAW) + load(X_RAW):
        out.append(
            {
                "id": hashlib.sha1(s["url"].encode()).hexdigest()[:12],
                "title": s["title"],
                "company": s["company"],
                "url": s["url"],
                "snippet": s.get("snippet", ""),
                "links": s.get("links", []),
                "source": s.get("source", "feed"),
                "posted": posted_str(s.get("posted_ts")),
                "posted_ts": s.get("posted_ts") or 0,
            }
        )
    out.sort(key=lambda s: -s["posted_ts"])
    return out


def main():
    raw = load(COMPANIES_RAW) + load(GITHUB_RAW)
    # VC portfolio boards are discovery: companies off the watchlist are allowed.
    discovery = load(VC_RAW)
    for j in discovery:
        j["discover"] = True
    jobs = []
    seen = set()
    for j in raw + discovery:
        listed = canonical((j.get("company") or "").split("\n")[0])
        company = listed or (j.get("company") or "").split("\n")[0].strip()
        if not company or (not listed and not j.get("discover")):
            continue
        role = classify(j["title"])
        if not role:
            continue
        location = re.sub(r"\s+", " ", (j.get("location") or "").split("\n")[0])
        if not is_us(location):
            continue
        key = (re.sub(r"\s+", " ", j["title"].lower()).strip(), company.lower())
        if key in seen:
            continue
        seen.add(key)
        min_exp = j.get("min_exp")
        if min_exp is not None and min_exp > 3:
            continue
        age = age_days(j)
        if age is not None and age > MAX_AGE_DAYS:
            continue
        jobs.append(
            {
                "id": hashlib.sha1(j["url"].encode()).hexdigest()[:12],
                "title": j["title"],
                "company": company,
                "location": location,
                "url": j["url"],
                "kind": kind_of(j["title"]),
                "role": role[0],
                "track": role[1],
                "source": j.get("source", "company"),
                "tier": tier_of(company) if listed else "discover",
                "minExp": min_exp,
                "age": age,
                "posted": posted_of(j.get("footer")) or posted_str(j.get("posted_ts")),
            }
        )
    jobs.sort(key=lambda x: (
        ROLE_ORDER.get(x["role"], 9),
        TIER_ORDER.get(x["tier"], 9),
        x["age"] if x["age"] is not None else 99,
        x["company"].lower(),
    ))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sig = signals()
    OUT.write_text(
        json.dumps(
            {
                "updated": time.strftime("%Y-%m-%d %H:%M UTC"),
                "jobs": jobs,
                "signals": sig,
            },
            indent=2,
        )
    )
    print(f"{len(jobs)} jobs ({sum(1 for j in jobs if j['tier'] == 'discover')} discover), "
          f"{len(sig)} signals -> {OUT}")


if __name__ == "__main__":
    main()
