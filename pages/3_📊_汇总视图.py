# pages/3_📊_汇总视图.py
import io
import streamlit as st
import pandas as pd

st.set_page_config(page_title="汇总视图", page_icon="📊", layout="wide")

# ===== 登录检查 =====
if "user" not in st.session_state:
    st.error("请先登录")
    st.stop()

from core.db import list_projects
from core.aggregator import get_all_datasets, get_all_tfls

st.title("📊 汇总视图")
st.caption("合并展示所有项目的 Datasets 与 TFLs（仅包含每个项目的活跃 LOT）")

# ============================================================
# 项目 & 全量数据
# ============================================================
projects = list_projects()
if not projects:
    st.warning("暂无项目数据。")
    st.stop()

proj_options = {p["project_name"]: p["id"] for p in projects}

_all_ds = get_all_datasets(None)
_all_tfl = get_all_tfls(None)


def _all_unique_values(dfs, col):
    vals = set()
    for df in dfs:
        if df is not None and not df.empty and col in df.columns:
            vals.update(v for v in df[col].dropna().astype(str).str.strip().unique() if v)
    return sorted(vals)


prog_options = _all_unique_values([_all_ds, _all_tfl], "programmer")
qc_prog_options = _all_unique_values([_all_ds, _all_tfl], "qc_programmer")
required_options = _all_unique_values([_all_ds, _all_tfl], "required")
status_options = _all_unique_values([_all_ds, _all_tfl], "status")
qc_status_options = _all_unique_values([_all_ds, _all_tfl], "qc_status")

# ============================================================
# 筛选区
# ============================================================
with st.expander("🔎 筛选条件", expanded=True):
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        selected_projects = st.multiselect(
            "项目（可多选，留空=全部）",
            options=list(proj_options.keys()),
            default=[],
        )
    with row1_col2:
        selected_types = st.multiselect(
            "数据类型（仅 Datasets 生效）",
            options=["SDTM", "ADaM", "UNKNOWN"],
            default=["SDTM", "ADaM", "UNKNOWN"],
        )
    with row1_col3:
        keyword = st.text_input("关键词搜索（Program / TxtName / Title 等）", "")

    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        selected_programmers = st.multiselect(
            "Programmer（可多选，留空=全部）",
            options=prog_options,
            default=[],
        )
    with row2_col2:
        selected_qc_programmers = st.multiselect(
            "QC Programmer（可多选，留空=全部）",
            options=qc_prog_options,
            default=[],
        )
    with row2_col3:
        selected_required = st.multiselect(
            "Required（可多选，留空=全部）",
            options=required_options,
            default=[],
        )

    row3_col1, row3_col2, _ = st.columns(3)
    with row3_col1:
        selected_status = st.multiselect(
            "Status（可多选，留空=全部）",
            options=status_options,
            default=[],
        )
    with row3_col2:
        selected_qc_status = st.multiselect(
            "QC Status（可多选，留空=全部）",
            options=qc_status_options,
            default=[],
        )

project_ids = [proj_options[n] for n in selected_projects] if selected_projects else None

# ============================================================
# 拉取数据
# ============================================================
df_ds = get_all_datasets(project_ids)
df_tfl = get_all_tfls(project_ids)


def _apply_common_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if selected_programmers and "programmer" in df.columns:
        df = df[df["programmer"].fillna("").isin(selected_programmers)]
    if selected_qc_programmers and "qc_programmer" in df.columns:
        df = df[df["qc_programmer"].fillna("").isin(selected_qc_programmers)]
    if selected_required and "required" in df.columns:
        df = df[df["required"].fillna("").isin(selected_required)]
    if selected_status and "status" in df.columns:
        df = df[df["status"].fillna("").isin(selected_status)]
    if selected_qc_status and "qc_status" in df.columns:
        df = df[df["qc_status"].fillna("").isin(selected_qc_status)]
    return df


# ---- Datasets 过滤 ----
if not df_ds.empty:
    if selected_types:
        df_ds = df_ds[df_ds["derived_type"].isin(selected_types)]
    if keyword:
        kw = keyword.lower()
        mask = (
            df_ds["program_name"].fillna("").str.lower().str.contains(kw) |
            df_ds["dataset_label"].fillna("").str.lower().str.contains(kw) |
            df_ds["output_name"].fillna("").str.lower().str.contains(kw) |
            df_ds["programmer"].fillna("").str.lower().str.contains(kw) |
            df_ds["qc_programmer"].fillna("").str.lower().str.contains(kw)
        )
        df_ds = df_ds[mask]
    df_ds = _apply_common_filters(df_ds)

# ---- TFLs 过滤 ----
if not df_tfl.empty:
    if keyword:
        kw = keyword.lower()
        mask = (
            df_tfl["txtname"].fillna("").str.lower().str.contains(kw) |
            df_tfl["rtfname"].fillna("").str.lower().str.contains(kw) |
            df_tfl["title"].fillna("").str.lower().str.contains(kw) |
            df_tfl["output_number"].fillna("").str.lower().str.contains(kw) |
            df_tfl["programmer"].fillna("").str.lower().str.contains(kw) |
            df_tfl["qc_programmer"].fillna("").str.lower().str.contains(kw)
        )
        df_tfl = df_tfl[mask]
    df_tfl = _apply_common_filters(df_tfl)

# ============================================================
# 展示
# ============================================================
tab_ds, tab_tfl = st.tabs([
    f"📦 Datasets ({len(df_ds)})",
    f"📑 TFLs ({len(df_tfl)})",
])

with tab_ds:
    if df_ds.empty:
        st.info("无匹配的 Datasets 数据。")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总记录", len(df_ds))
        c2.metric("SDTM", int((df_ds["derived_type"] == "SDTM").sum()))
        c3.metric("ADaM", int((df_ds["derived_type"] == "ADaM").sum()))
        c4.metric("涉及项目", df_ds["project_name"].nunique())

        st.dataframe(
            df_ds.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_ds.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore").to_excel(
                w, sheet_name="Datasets", index=False)
        st.download_button(
            "⬇️ 导出 Datasets 汇总 (xlsx)",
            data=buf.getvalue(),
            file_name="All_Datasets_Summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with tab_tfl:
    if df_tfl.empty:
        st.info("无匹配的 TFLs 数据。")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("总记录", len(df_tfl))
        c2.metric("涉及项目", df_tfl["project_name"].nunique())
        c3.metric("状态 Ready",
                  int(df_tfl["status"].fillna("").str.lower().eq("ready").sum()))

        st.dataframe(
            df_tfl.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_tfl.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore").to_excel(
                w, sheet_name="TFLs", index=False)
        st.download_button(
            "⬇️ 导出 TFLs 汇总 (xlsx)",
            data=buf.getvalue(),
            file_name="All_TFLs_Summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ============================================================
# 合并导出
# ============================================================
st.divider()
if not df_ds.empty or not df_tfl.empty:
    buf_all = io.BytesIO()
    with pd.ExcelWriter(buf_all, engine="openpyxl") as w:
        if not df_ds.empty:
            df_ds.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore").to_excel(
                w, sheet_name="Datasets", index=False)
        if not df_tfl.empty:
            df_tfl.drop(columns=["id", "lot_file_id", "project_id"], errors="ignore").to_excel(
                w, sheet_name="TFLs", index=False)
    st.download_button(
        "📦 导出完整合并文件（Datasets + TFLs 两个 sheet）",
        data=buf_all.getvalue(),
        file_name="All_Projects_Datasets_TFLs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )