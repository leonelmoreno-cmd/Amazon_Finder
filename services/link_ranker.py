# services/link_ranker.py
from __future__ import annotations
from typing import List, Dict
from urllib.parse import urlparse
from thefuzz import fuzz  # fuzzy string matching

def _extract_domain_part(url: str) -> str:
    """Get the domain string (without subdomain) from URL, e.g. amazon.com, sub.amazon.co.uk -> amazon"""
    netloc = urlparse(url).netloc.lower()
    # strip www. if present
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # split by dots, take the “second-level domain” part (before first dot)
    parts = netloc.split(".")
    if len(parts) >= 2:
        return parts[-2]  # e.g. for “sub.amazon.co.uk” parts = ["sub","amazon","co","uk"] → -2 is "co", wrong
    return netloc

def rank_links_by_brand(links: List[Dict], brand: str, threshold: int = 70) -> List[Dict]:
    """
    Given a list of items with 'url', 'title', etc., score each by similarity between domain (or domain part)
    and the brand string. If similarity ≥ threshold, we keep only those links (or rank them highest).
    Returns filtered/ordered list.
    """
    scored = []
    brand_norm = brand.lower().strip()
    for it in links:
        url = it.get("url")
        if not url:
            continue
        dom = _extract_domain_part(url)
        # compute fuzzy ratio
        score = fuzz.partial_ratio(brand_norm, dom)
        scored.append({**it, "brand_domain_score": score})

    # Filter those that pass threshold
    passed = [it for it in scored if it["brand_domain_score"] >= threshold]
    if passed:
        # Sort passed by descending score
        passed_sorted = sorted(passed, key=lambda x: x["brand_domain_score"], reverse=True)
        return passed_sorted
    else:
        # If none pass, return original links sorted by score descending
        return sorted(scored, key=lambda x: x["brand_domain_score"], reverse=True)
