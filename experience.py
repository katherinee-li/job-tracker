"""Pull the minimum years of experience a posting asks for."""

import re

YEARS_RE = re.compile(
    r"(?:(\d{1,2})\s*(?:\+|plus)?\s*(?:-|to|–)?\s*(\d{1,2})?)\s*\+?\s*(?:years?|yrs?)"
    r"[^.\n]{0,40}?(?:experience|exp\b)",
    re.I,
)
NO_EXP_RE = re.compile(
    r"(no prior experience|new grad|recent graduate|graduating (?:in|by)|entry.level)", re.I
)


def min_years(text):
    """Smallest years-of-experience requirement in the text, or None."""
    if not text:
        return None
    found = []
    for m in YEARS_RE.finditer(text):
        lo = int(m.group(1))
        if lo <= 20:
            found.append(lo)
    if not found:
        return None
    return min(found)


def entry_level(text):
    """True when the description reads as open to a new grad (<= 3 yrs)."""
    if not text:
        return False
    if NO_EXP_RE.search(text):
        return True
    y = min_years(text)
    return y is not None and y <= 3
