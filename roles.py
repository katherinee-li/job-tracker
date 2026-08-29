"""Decide whether a posting is one of the few role types worth surfacing."""

import re

SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|head of|vp|distinguished|"
    r"executive|architect|chief|iii|iv)\b",
    re.I,
)
# roles that are adjacent but not wanted: solutions/sales/support/program/marketing
ADJACENT_RE = re.compile(
    r"(solutions (engineer|architect|consultant)|sales|account (executive|manager)|"
    r"customer success|support engineer|technical program|program manager|"
    r"project manager|product marketing|product design|product support|"
    r"product operations|community|recruit|partner)",
    re.I,
)
FDE_RE = re.compile(r"(forward.deployed|deployment (engineer|strategist)|deployed engineer)", re.I)
APM_RE = re.compile(r"(\bapm\b|associate product manager|product manager,? (new grad|university|early))", re.I)
PM_RE = re.compile(r"(product manager|product management|product lead|group product)", re.I)
INTERN_RE = re.compile(r"(intern(ship)?\b|co.?op)", re.I)
NEWGRAD_RE = re.compile(r"(new.?grad|university grad|campus|early career|entry.level|\b20(2[6-9])\b)", re.I)
SWE_RE = re.compile(
    r"(software engineer|software developer|\bswe\b|engineering intern|"
    r"machine learning engineer|research engineer|ai engineer)",
    re.I,
)


def kind_of(title):
    if re.search(r"co.?op", title, re.I):
        return "co-op"
    if INTERN_RE.search(title):
        return "intern"
    return "full-time"


def classify(title):
    """Return (role, track) for wanted postings, else None.

    Wanted: forward-deployed engineering, APM/PM (early-career only), product
    internships and co-ops, plus SWE internships/co-ops on the software track.
    """
    if SENIOR_RE.search(title) or ADJACENT_RE.search(title):
        return None
    if re.search(r"\bmanagers?\b", title, re.I) and not PM_RE.search(title):
        return None
    kind = kind_of(title)
    intern = kind in ("intern", "co-op")
    if FDE_RE.search(title):
        return ("fde-intern" if intern else "fde"), "product"
    if APM_RE.search(title):
        return "apm", "product"
    if PM_RE.search(title):
        if intern:
            return "product-intern", "product"
        return ("apm", "product") if NEWGRAD_RE.search(title) else None
    if intern and SWE_RE.search(title):
        return "swe-intern", "software"
    return None
