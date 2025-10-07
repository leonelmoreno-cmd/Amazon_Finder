# services/google_client.py
from __future__ import annotations
import logging, time, requests
from dataclasses import dataclass, field
from typing import List, Dict, Any
from config.settings import AppConfig

log = logging.getLogger(__name__)

@dataclass
class GoogleUsage:
    requests_made: int = 0
    last_call_ts: float = 0.0
    qps_target: float = 8.0

    def wait_for_qps(self) -> None:
        if self.qps_target <= 0: return
        now = time.time()
        min_interval = max(0.125, 1.0 / float(self.qps_target))
        delta = now - self.last_call_ts
        if delta < min_interval:
            time.sleep(min_interval - delta)
        self.last_call_ts = time.time()

class GoogleClient:
    """Interface-like base. Concrete: SimulatedGoogleClient | RealGoogleClient"""
    def search(self, query: str, exclude_domains: List[str], num: int = 10) -> Dict[str, Any]:
        raise NotImplementedError

@dataclass
class SimulatedGoogleClient(GoogleClient):
    usage: GoogleUsage = field(default_factory=GoogleUsage)

    def search(self, query: str, exclude_domains: List[str], num: int = 10) -> Dict[str, Any]:
        # No external calls. Return deterministic “plausible” items.
        self.usage.requests_made += 1
        base = query.strip() or "Unknown Product"
        items = []
        for i in range(1, min(num, 10) + 1):
            items.append({
                "title": f"{base} — Reference {i}",
                "link": f"https://example.com/{base.replace(' ', '-').lower()}/{i}",
                "snippet": f"Informational page #{i} about {base}.",
            })
        return {"items": items}

@dataclass
class RealGoogleClient(GoogleClient):
    cfg: AppConfig
    usage: GoogleUsage = field(default_factory=GoogleUsage)

    def search(self, query: str, exclude_domains: List[str], num: int = 10) -> Dict[str, Any]:
        if not self.cfg.GOOGLE_API_KEY or not self.cfg.GOOGLE_CSE_CX:
            raise RuntimeError("Missing GOOGLE_API_KEY or GOOGLE_CSE_CX.")
        self.usage.qps_target = self.cfg.GOOGLE_QPS_TARGET
        self.usage.wait_for_qps()

        excl = " ".join(f"-site:{d}" for d in exclude_domains) if exclude_domains else ""
        q = f"{query} {excl}".strip()
        params = {
            "key": self.cfg.GOOGLE_API_KEY,
            "cx": self.cfg.GOOGLE_CSE_CX,
            "q": q,
            "num": min(max(num, 1), 10),
            "start": 1,
        }
        url = self.cfg.GOOGLE_URL
        log.info("GoogleCSE: GET %s q='%s'", url, q)
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        self.usage.requests_made += 1
        return resp.json()

def make_google_client(cfg: AppConfig) -> GoogleClient:
    return SimulatedGoogleClient() if cfg.GOOGLE_MODE == "simulate" else RealGoogleClient(cfg)
