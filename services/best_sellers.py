# services/best_sellers.py
from __future__ import annotations
import json, time, logging, requests
from typing import Any, Dict, List, Optional
from config.settings import AppConfig
from utils.typing import BestSellerRow

log = logging.getLogger(__name__)

def _to_int(v: Any) -> Optional[int]:
    try: return int(str(v).strip())
    except Exception: return None

def _normalize_best(payload: Dict[str, Any]) -> List[BestSellerRow]:
    data = (payload or {}).get("data") or {}
    arr = data.get("best_sellers") or []
    out: List[BestSellerRow] = []
    for it in arr:
        asin = (it or {}).get("asin")
        rank = _to_int((it or {}).get("rank"))
        if asin and rank is not None:
            out.append({"asin": str(asin).strip(), "rank": rank})
    return out

def fetch_best_sellers(category: str, cfg: AppConfig) -> List[BestSellerRow]:
    if not (cfg.RAPIDAPI_KEY or cfg.AMAZON_API_KEY):
        raise RuntimeError("Missing RAPIDAPI_KEY / AMAZON_API_KEY.")

    headers = {
        "x-rapidapi-key": cfg.RAPIDAPI_KEY or cfg.AMAZON_API_KEY,
        "x-rapidapi-host": cfg.API_HOST,
    }
    url = f"https://{cfg.API_HOST}/best-sellers"

    collected: List[BestSellerRow] = []
    page = 1
    while len(collected) < cfg.MAX_BEST_ITEMS:
        params = dict(category=category, country=cfg.COUNTRY, language=cfg.LANGUAGE, page=page)
        log.info("BestSellers: GET %s params=%s", url, params)
        chunk = []
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("status") != "OK":
                    raise ValueError(f"API status != OK (status={payload.get('status')})")
                chunk = _normalize_best(payload)
                collected.extend(chunk)
                break
            except (requests.HTTPError, requests.ConnectionError) as e:
                log.warning("BestSellers network error (attempt %s): %s", attempt+1, e)
                time.sleep(1.5)
            except json.JSONDecodeError:
                raise ValueError("BestSellers: invalid JSON")
        if not chunk or len(chunk) < 50:
            break
        page += 1

    collected = sorted(collected, key=lambda r: r["rank"])[:cfg.MAX_BEST_ITEMS]
    log.info("BestSellers: collected=%d", len(collected))
    return collected
