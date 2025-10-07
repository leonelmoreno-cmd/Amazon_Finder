# services/url_filter.py
from __future__ import annotations
from typing import List, Dict
from urllib.parse import urlparse
import os

# Default list (edit here to change globally)
DEFAULT_EXCLUDED = ["amazon.com", "ebay.com", "walmart.com"]

def _parse_domain(url: str) -> str:
    """
    Extracts the host:
    - lowercases
    - strips 'www.'
    - ignores ports
    """
    try:
        netloc = urlparse(url).netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":", 1)[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def _endswith_any(host: str, domains: List[str]) -> bool:
    # Allow subdomains: seller.amazon.com -> amazon.com
    return any(host.endswith(d.strip().lower()) for d in domains if d.strip())

def _parse_list(text: str) -> List[str]:
    # Accept comma- or newline-separated
    parts = [p.strip().lower() for p in text.replace(",", "\n").splitlines() if p.strip()]
    return parts

def get_excluded_domains() -> List[str]:
    """
    Returns excluded domains from:
      1) ENV var EXCLUDE_DOMAINS (comma/newline separated)
      2) DEFAULT_EXCLUDED (fallback)
    """
    raw = os.getenv("EXCLUDE_DOMAINS", "")
    if raw:
        parsed = _parse_list(raw)
        if parsed:
            return parsed
    return DEFAULT_EXCLUDED

def filter_items_by_domain(items: List[Dict], excluded: List[str]) -> List[Dict]:
    """
    Filters items by excluding links whose host matches any excluded domain.
    """
    out: List[Dict] = []
    for it in items:
        link = (it or {}).get("link") or it.get("url")
        if not link:
            continue
        host = _parse_domain(link)
        if not _endswith_any(host, excluded):
            out.append(it)
    return out
