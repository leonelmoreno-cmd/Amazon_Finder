# app.py
from __future__ import annotations

import logging
import pandas as pd
import streamlit as st

from config.settings import AppConfig
from utils.logging_setup import setup_logging
from services.best_sellers import fetch_best_sellers
from services.product_details import build_stage2_dataframe
from services.google_client import make_google_client
from services.semantic import build_query, normalize_exclusions, semantic_filter

from utils.data_ops import sanitize_for_stage3, df_to_csv_bytes, clean_text

# -------------------------
# Page / App configuration
# -------------------------
st.set_page_config(
    page_title="Amazon Best Sellers: Insight Helper",
    page_icon="🛒",
    layout="wide",
)

# -------------------------
# App config & logging
# -------------------------
cfg = AppConfig()
mem_handler = setup_logging(logging.INFO)
log = logging.getLogger("app")


# -------------------------
# Sidebar (settings)
# -------------------------
st.sidebar.header("Settings")

st.sidebar.caption("RapidAPI (Best Sellers & Product Details)")
st.sidebar.write(f"Country: **{cfg.COUNTRY}**  |  Language: **{cfg.LANGUAGE}**")

st.sidebar.write("---")
st.sidebar.caption("Google CSE")
st.sidebar.write(f"Mode: **{cfg.GOOGLE_MODE}**  |  Threshold: **{cfg.GOOGLE_THRESHOLD}**  |  Max links/row: **{cfg.GOOGLE_MAX_LINKS}**  |  QPS: **{cfg.GOOGLE_QPS_TARGET}**")

st.sidebar.write("---")
if not (cfg.RAPIDAPI_KEY or cfg.AMAZON_API_KEY):
    st.sidebar.warning("RAPIDAPI_KEY / AMAZON_API_KEY is missing (required for Stage 1 & 2).")
if cfg.GOOGLE_MODE == "real" and (not cfg.GOOGLE_API_KEY or not cfg.GOOGLE_CSE_CX):
    st.sidebar.warning("GOOGLE_API_KEY or GOOGLE_CSE_CX is missing (required in real mode).")


# -------------------------
# UI: Main inputs
# -------------------------
st.title("Amazon Best Sellers — Streamlit App")
st.caption("One-page app. Clean and modular. Run stages in order (1 → 2 → 3).")

category_input = st.text_input(
    "Enter category path (e.g., lawn-garden/3737941):",
    value="lawn-garden/3737941",
    placeholder="department/subcategory_id",
    help="This value is sent as `category` to the Best Sellers endpoint.",
)

colA, colB, colC = st.columns([1, 1, 3])
with colA:
    fetch_btn = st.button("Fetch Best Sellers (Stage 1)", type="primary")
with colB:
    clear_btn = st.button("Clear Session")
with colC:
    st.caption("Stages: 1) Best Sellers → 2) Details+DF → 3) Google links")

if clear_btn:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("Session cleared.")

# -------------------------
# Placeholders for live progress
# -------------------------
stage_status = st.empty()
stage_progress = st.progress(0)
results_container = st.container()

# -------------------------
# Session containers
# -------------------------
st.session_state.setdefault("stage1_best", None)  # list[{'asin','rank'}]
st.session_state.setdefault("stage2_df", None)    # pd.DataFrame
st.session_state.setdefault("stage3_df", None)    # pd.DataFrame

# -------------------------
# Helpers
# -------------------------
def render_stage_header(title: str) -> None:
    st.subheader(title)


# =========================
# Stage 1 — Best Sellers
# =========================
if fetch_btn:
    if not category_input.strip():
        st.error("Please enter a valid category path (e.g., lawn-garden/3737941).")
    else:
        try:
            render_stage_header("Stage 1 — Fetch Best Sellers")
            stage_status.info("Contacting RapidAPI (Best Sellers)…")
            stage_progress.progress(10)

            best = fetch_best_sellers(category_input.strip(), cfg)

            stage_status.info("Normalizing results…")
            stage_progress.progress(70)

            # Ensure unique ASINs & sorted by rank
            seen = set()
            deduped = []
            for row in best:
                a = row["asin"]
                if a not in seen:
                    seen.add(a)
                    deduped.append(row)
            deduped = sorted(deduped, key=lambda r: r["rank"])

            st.session_state["stage1_best"] = deduped
            stage_status.success(f"Fetched {len(deduped)} items (asin + rank).")
            stage_progress.progress(100)

            with results_container:
                st.caption("Stage 1 output preview (top 10):")
                st.write(deduped[:10])

        except Exception as e:
            log.exception("Stage 1 failed")
            stage_status.error(f"Stage 1 failed: {e}")
            stage_progress.progress(0)


# Divider
st.write("---")


# =========================
# Stage 2 — Details + DataFrame
# =========================
col1, col2 = st.columns([1, 5])
with col1:
    stage2_btn = st.button("Build DataFrame (Stage 2)", type="secondary")

if stage2_btn:
    if not st.session_state.get("stage1_best"):
        st.error("Stage 1 data not found. Please run Stage 1 first.")
    else:
        try:
            render_stage_header("Stage 2 — Build DataFrame with details")
            stage_status.info("Initializing Stage 2…")
            stage_progress.progress(5)

            df = build_stage2_dataframe(
                st.session_state["stage1_best"],
                cfg,
                stage_status=stage_status,
                stage_progress=stage_progress,
            )
            df = sanitize_for_stage3(df)
            st.session_state["stage2_df"] = df
            stage_status.success(f"Stage 2 complete. Rows: {len(df)}")
            stage_progress.progress(100)

            with results_container:
                st.caption("Stage 2 preview (top 20 by sales volume):")
                st.dataframe(df.head(5), use_container_width=True)
                # 🔽 NUEVO: Botón para descargar Stage 2 CSV
                st.download_button(
                    label="⬇️ Download Stage 2 CSV",
                    data=df_to_csv_bytes(df),
                    file_name="stage2_products.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        except Exception as e:
            log.exception("Stage 2 failed")
            stage_status.error(f"Stage 2 failed: {e}")
            stage_progress.progress(0)


# Divider
st.write("---")


# =========================
# Stage 3 — Google search + semantic filtering
# =========================
st.subheader(f"Stage 3 — Google search + semantic filtering (mode: {cfg.GOOGLE_MODE})")

colA, colB, colC = st.columns([1, 1, 1])
with colA:
    max_links = st.number_input("Max links per row", min_value=1, max_value=10, value=cfg.GOOGLE_MAX_LINKS, step=1)
with colB:
    threshold = st.slider("Similarity threshold", min_value=0.0, max_value=1.0, value=float(cfg.GOOGLE_THRESHOLD), step=0.05)
with colC:
    qps = st.number_input("Google QPS target (≤10)", min_value=1.0, max_value=10.0, value=float(cfg.GOOGLE_QPS_TARGET), step=0.5)

exclude_domains_text = st.text_area(
    "Exclude domains (one per line or comma-separated)",
    value="amazon.com\nebay.com\nwalmart.com",
    height=120,
)

stage3_btn = st.button("Run Stage 3", type="primary")

if stage3_btn:
    if st.session_state.get("stage2_df") is None:
        st.error("Stage 2 table not found. Please run Stage 2 first.")
    else:
        try:
            render_stage_header("Stage 3 — Searching & filtering")
            stage_status.info("Initializing Stage 3…")
            stage_progress.progress(5)

            client = make_google_client(cfg)
            # If real client, allow live QPS override from UI
            if hasattr(client, "usage"):
                client.usage.qps_target = float(qps)

            df2 = st.session_state["stage2_df"].copy()
            exclude = normalize_exclusions(exclude_domains_text)

            # Prepare link columns
            for j in range(int(max_links)):
                col = f"link_{j+1}"
                if col not in df2.columns:
                    df2[col] = None

            total = len(df2)
            for i, row in df2.iterrows():
                brand = clean_text(row.get("brand"))
                title = clean_text(row.get("product_title"))
                target = f"{brand} {title}".strip() or title or brand
                if not target:
                    continue

                stage_status.info(f"Stage 3: searching links ({i+1}/{total}) …")
                stage_progress.progress(min(99, int(5 + ((i + 1) / max(1, total)) * 90)))

                query = build_query(brand, title)
                try:
                    payload = client.search(query, exclude_domains=exclude, num=10)
                    items = payload.get("items", []) or []
                except Exception as e:
                    log.warning("Google search failed for row %d: %s", i, e)
                    items = []

                filtered = semantic_filter(items, target_text=target, threshold=float(threshold))
                for j in range(int(max_links)):
                    df2.at[i, f"link_{j+1}"] = (filtered[j]["url"] if j < len(filtered) else None)

            st.session_state["stage3_df"] = df2
            # Requests made (works for simulate and real)
            requests_made = getattr(getattr(client, "usage", None), "requests_made", "n/a")
            stage_status.success(f"Stage 3 complete. Google requests: {requests_made}")
            stage_progress.progress(100)

            with results_container:
                st.caption("Stage 3 preview (top 20):")
                st.dataframe(df2.head(5), use_container_width=True)
                st.download_button(
                label="⬇️ Download Stage 3 CSV",
                data=df_to_csv_bytes(df2),
                file_name="stage3_with_links.csv",
                mime="text/csv",
                use_container_width=True,
                 )
        except Exception as e:
            log.exception("Stage 3 failed")
            stage_status.error(f"Stage 3 failed: {e}")
            stage_progress.progress(0)


# -------------------------
# Logs & quick stats
# -------------------------
with st.expander("Logs (latest)"):
    for line in mem_handler.records[-300:]:
        st.text(line)

if st.session_state.get("stage3_df") is not None:
    df3 = st.session_state["stage3_df"]
    total_links = (df3.filter(like="link_").notna()).sum().sum()
    st.caption(f"Total populated links: {int(total_links)}")
