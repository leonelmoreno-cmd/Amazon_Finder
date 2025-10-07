# services/product_details.py
from __future__ import annotations
import logging, re, requests
from typing import Any, Dict, List
import pandas as pd
from config.settings import AppConfig
from utils.typing import BestSellerRow, ProductRow

log = logging.getLogger(__name__)

_sales_pat = re.compile(r"(?P<num>[\d,.]+)\s*(?P<suf>[kKmM]?)\s*\+?")

def parse_sales_volume(text: str | None) -> int | None:
    if not text: return None
    m = _sales_pat.search(text)
    if not m: return None
    raw = m.group("num").replace(",", "")
    try:
        base = float(raw)
    except ValueError:
        return None
    suf = m.group("suf").lower()
    mult = 1_000 if suf == "k" else (1_000_000 if suf == "m" else 1)
    return int(round(base * mult))

def _extract_brand(item: dict) -> str | None:
    info = (item or {}).get("product_information") or {}
    details = (item or {}).get("product_details") or {}
    for d in (info, details):
        for key in ("Brand Name", "Brand"):
            v = d.get(key)
            if v: return str(v).strip()
    top = (item or {}).get("brand")
    return str(top).strip() if top else None

def _normalize_details_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = (payload or {}).get("data")
    if data is None: return []
    if isinstance(data, list): return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict): return [data]
    return []

def fetch_details_batch(asins: List[str], cfg: AppConfig) -> List[Dict[str, Any]]:
    headers = {"x-rapidapi-key": cfg.RAPIDAPI_KEY or cfg.AMAZON_API_KEY, "x-rapidapi-host": cfg.API_HOST}
    params = {"asin": ",".join(asins), "country": cfg.COUNTRY}
    url = f"https://{cfg.API_HOST}/product-details"
    log.info("Details: GET %s asins=%d", url, len(asins))
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "OK":
        raise ValueError(f"product-details status != OK (status={payload.get('status')})")
    return _normalize_details_payload(payload)

def build_stage2_dataframe(best: List[BestSellerRow], cfg: AppConfig, stage_status=None, stage_progress=None) -> pd.DataFrame:
    rows: List[ProductRow] = []
    asins_sorted = [r["asin"] for r in sorted(best, key=lambda x: x["rank"])]
    batches = [asins_sorted[i:i+cfg.DETAILS_BATCH_SIZE] for i in range(0, len(asins_sorted), cfg.DETAILS_BATCH_SIZE)]
    total = max(1, len(batches))

    for i, batch in enumerate(batches, start=1):
        if stage_status: stage_status.info(f"Fetching details batch {i}/{total} …")
        if stage_progress: stage_progress.progress(int(5 + (i/total)*85))
        try:
            items = fetch_details_batch(batch, cfg)
        except Exception as e:
            log.exception("Details batch failed: %s", e)
            for a in batch:
                rank = next((r["rank"] for r in best if r["asin"] == a), None)
                rows.append({"asin": a, "rank": rank})
            continue

        by_asin = {str(it.get("asin")).strip(): it for it in items if it and it.get("asin")}
        for a in batch:
            it = by_asin.get(a)
            rank = next((r["rank"] for r in best if r["asin"] == a), None)
            if not it:
                rows.append({"asin": a, "rank": rank})
                continue
            title = it.get("product_title")
            sales_raw = it.get("sales_volume")
            brand = _extract_brand(it)
            url = it.get("product_url")
            rows.append({
                "asin": a, "rank": rank, "product_title": title, "brand": brand,
                "sales_volume_raw": sales_raw, "sales_volume_num": parse_sales_volume(sales_raw),
                "product_url": url,
            })

    df = pd.DataFrame(rows, columns=[
        "rank", "asin", "product_title", "brand", "sales_volume_raw", "sales_volume_num", "product_url"
    ])

    df = df.sort_values(
        by=["sales_volume_num", "rank"],
        ascending=[False, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)

    return df
