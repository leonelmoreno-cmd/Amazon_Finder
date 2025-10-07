# utils/data_ops.py
from __future__ import annotations
import pandas as pd
from typing import Any

def clean_text(value: Any) -> str:
    """
    Safe string cleaner:
    - None or NaN -> ""
    - else -> stripped string
    """
    if value is None:
        return ""
    # Pandas NaN is a float
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()

def sanitize_for_stage3(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make sure Stage 3 receives a safe DataFrame:
    - Ensure columns exist
    - Replace NaN with ""
    - Strip strings for 'brand' and 'product_title'
    - Keep other columns untouched
    """
    out = df.copy()

    # Ensure columns exist
    for col in ["brand", "product_title"]:
        if col not in out.columns:
            out[col] = ""

    # Replace NaN with "" only in these two columns (avoid touching numerics)
    out["brand"] = out["brand"].map(clean_text)
    out["product_title"] = out["product_title"].map(clean_text)

    return out

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert a DataFrame to CSV bytes for Streamlit download_button.
    """
    return df.to_csv(index=False).encode("utf-8")
