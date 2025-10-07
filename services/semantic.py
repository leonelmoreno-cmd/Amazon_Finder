# services/semantic.py
from __future__ import annotations
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util
import streamlit as st

@st.cache_resource(show_spinner=False)
def get_semantic_model() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def semantic_filter(items: List[Dict], target_text: str, threshold: float = 0.50) -> List[Dict]:
    if not items: return []
    model = get_semantic_model()
    target_emb = model.encode(target_text, convert_to_tensor=True)
    scored = []
    for it in items:
        title = it.get("title") or ""
        snippet = it.get("snippet") or ""
        link = it.get("link")
        if not link: continue
        text = f"{title} {snippet}".strip()
        text_emb = model.encode(text, convert_to_tensor=True)
        sim = float(util.cos_sim(target_emb, text_emb).item())
        if sim >= threshold:
            scored.append({"title": title, "url": link, "snippet": snippet, "similarity": round(sim, 3)})
    scored.sort(key=lambda r: r["similarity"], reverse=True)
    return scored

def build_query(brand: str | None, title: str | None) -> str:
    parts = []
    if brand: parts.append(str(brand))
    if title: parts.append(str(title))
    q = " ".join(p for p in parts if p).strip()
    return q or "site:manufacturer.com"

def normalize_exclusions(text: str) -> list[str]:
    raw = text.replace(",", "\n").splitlines()
    return sorted({d.strip().lower() for d in raw if d.strip()})
