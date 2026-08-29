#!/usr/bin/env python3
"""Diff the freshly built site payload against the last run's snapshot.

Writes data/seen.json (id -> first-seen date) and prints a short Slack-ready
summary of only the roles that appeared since the previous run.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent
JOBS = ROOT / "site" / "jobs.json"
SEEN = ROOT / "data" / "seen.json"

TIER_ORDER = {"tier1": 0, "big-tech": 1, "robotics": 2, "agents": 3, "ai-infra": 4}
ROLE_ORDER = {"fde": 0, "apm": 1, "product-intern": 2, "swe-intern": 3}
ROLE_LABEL = {
    "fde": "FDE",
    "fde-intern": "FDE intern",
    "apm": "APM / PM",
    "product-intern": "Product intern",
    "swe-intern": "SWE intern",
}
SITE = "https://kathyjobs-eeszqlct.devinapps.com"


def main():
    jobs = json.loads(JOBS.read_text())["jobs"]
    seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
    today = time.strftime("%Y-%m-%d")
    first_run = not seen

    new = [j for j in jobs if j["id"] not in seen]
    for j in jobs:
        seen.setdefault(j["id"], today)
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(seen, indent=0, sort_keys=True))

    if not jobs:
        print("SCRAPE_EMPTY")
        return
    if first_run:
        print(f"BASELINE {len(jobs)} roles recorded, no summary to send.")
        return
    if not new:
        print("NO_NEW_ROLES")
        return

    new.sort(key=lambda x: (
        ROLE_ORDER.get(x["role"], 9),
        TIER_ORDER.get(x["tier"], 9),
        x["company"].lower(),
    ))
    print(f"*{len(new)} new role{'s' if len(new) != 1 else ''} today* — <{SITE}|tracker>")
    for j in new:
        loc = f" · {j['location']}" if j.get("location") else ""
        print(f"• *{j['company']}* — <{j['url']}|{j['title']}> "
              f"({ROLE_LABEL.get(j['role'], j['role'])}{loc})")


if __name__ == "__main__":
    main()
