# utils/typing.py
from __future__ import annotations
from typing import TypedDict, Optional

class BestSellerRow(TypedDict):
    asin: str
    rank: int

class ProductRow(TypedDict, total=False):
    rank: Optional[int]
    asin: str
    product_title: Optional[str]
    brand: Optional[str]
    sales_volume_raw: Optional[str]
    sales_volume_num: Optional[int]
    product_url: Optional[str]
