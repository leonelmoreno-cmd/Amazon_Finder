# config/settings.py
from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    # RapidAPI (Best Sellers & Product Details)
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "")
    AMAZON_API_KEY: str = os.getenv("AMAZON_API_KEY", "")
    API_HOST: str = os.getenv("API_HOST", "real-time-amazon-data.p.rapidapi.com")
    COUNTRY: str = os.getenv("COUNTRY", "US")
    LANGUAGE: str = os.getenv("LANGUAGE", "en_US")

    # Google CSE
    GOOGLE_MODE: str = os.getenv("GOOGLE_MODE", "simulate").lower()  # simulate | real
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_CX: str = os.getenv("GOOGLE_CSE_CX", "")
    GOOGLE_URL: str = "https://www.googleapis.com/customsearch/v1"

    # App behavior
    MAX_BEST_ITEMS: int = 50
    DETAILS_BATCH_SIZE: int = 10
    GOOGLE_MAX_LINKS: int = 3
    GOOGLE_THRESHOLD: float = 0.50
    GOOGLE_QPS_TARGET: float = 8.0  # ≤ 10
