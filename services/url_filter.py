# services/url_filter.py
from __future__ import annotations
from typing import List, Dict
from urllib.parse import urlparse
import os

# Path to the exclusion file (relative to project root)
DEFAULT_EXCLUDED_FILE = os.path.join(os.path.dirname(__file__), "excluded_domains.txt")

def _parse_domain(url: str) -> str:
    """Extracts the host: lowercase, strips 'www.', ignores ports."""
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
    return any(host.endswith(d.strip().lower()) for d in domains if d.strip())

def _load_default_excluded() -> List[str]:
    """Reads default excluded domains from a text file."""
    try:
        with open(DEFAULT_EXCLUDED_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip().lower() for line in f.readlines() if line.strip()]
        return lines or ["amazon.com", "ebay.com", "walmart.com"]
    except FileNotFoundError:
        # Fallback if file missing
        return ["amazon.com", "ebay.com", "walmart.com"]

def get_excluded_domains() -> List[str]:
    """
    Returns excluded domains from excluded_domains.txt.
    Can also override with environment variable EXCLUDE_DOMAINS (optional).
    """
    env_val = os.getenv("EXCLUDE_DOMAINS", "")
    if env_val:
        return [d.strip().lower() for d in env_val.replace(",", "\n").splitlines() if d.strip()]
    return _load_default_excluded()

def filter_items_by_domain(items: List[Dict], excluded: List[str]) -> List[Dict]:
    """Filters Google CSE results by excluding unwanted domains."""
    out: List[Dict] = []
    for it in items:
        link = (it or {}).get("link") or it.get("url")
        if not link:
            continue
        host = _parse_domain(link)
        if not _endswith_any(host, excluded):
            out.append(it)
    return out
