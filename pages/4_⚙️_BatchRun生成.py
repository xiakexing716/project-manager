# pages/4_⚙️_BatchRun生成.py
import streamlit as st
from datetime import datetime
import pandas as pd

from core.db import list_projects
from core.aggregator import get_all_datasets, get_all_tfls
from core.batchrun import generate_batchrun

if "user" not in st.session_state:
    st.error("请先登录")
    st.stop()

from datetime import date, datetime
import pandas as pd
import plotly.express as px


# ===== 登录检查 =====
if "user" not in st.session_state:
    st.error("请先登录")
    st.stop()

from core.db import list_projects
from core.batchrun import generate_batchrun

st.set_page_config(page_title="BatchRun 生成", page_icon="⚙️", layout="wide")

st.title("⚙️ BatchRun 脚本生成")
st.caption(
    "每个项目使用自己的「项目位置」（在项目录入页配置）。"
    "未配置的项目将回退到下方「统一回退路径」。"
)

# ============================================================
# 项目 & 选项
# ============================================================
projects = list_projects()
if not projects:
    st.warning("暂无项目数据。")
    st.stop()

proj_options = {p["project_name"]: p["id"] for p in projects}

_all_ds = get_all_datasets(None)
_all_tfl = get_all_tfls(None)


def _unique_vals(dfs, col):
    vals = set()
    for df in dfs:
        if df is not None and not df.empty and col in df.columns:
            vals.update(v for v in df[col].dropna().astype(str).str.strip().unique() if v)
    return sorted(vals)


prog_options = _unique_vals([_all_ds, _all_tfl], "programmer")
qc_prog_options = _unique_vals([_all_ds, _all_tfl], "qc_programmer")
required_options = _unique_vals([_all_ds, _all_tfl], "required")
status_options = _unique_vals([_all_ds, _all_tfl], "status")
qc_status_options = _unique_vals([_all_ds, _all_tfl], "qc_status")

# ============================================================
# 表单
# ============================================================
st.subheader("1️⃣ 路径设置")
st.caption("每个项目的路径在「📝 项目录入」中配置。当前已配置情况：")

path_rows = []
for p in projects:
    try:
        pp = p["project_path"] or ""
    except Exception:
        pp = ""
    path_rows.append({"项目": p["project_name"],
                      "项目位置": pp if pp else "⚠️ 未配置"})
st.dataframe(pd.DataFrame(path_rows), use_container_width=True, hide_index=True)

fallback_dir = st.text_input(
    "统一回退路径（可选）",
    value="",
    placeholder=r"例如：\\server\study\default",
    help="只对「未配置项目位置」的项目生效。留空则这些项目只输出文件名。",
)

st.markdown("### 📁 子路径设置（相对项目根目录，可留空）")
c1, c2, c3 = st.columns(3)
with c1:
    sdtm_subdir = st.text_input("SDTM 子路径", value="02_extraction")
with c2:
    adam_subdir = st.text_input("ADaM 子路径", value="08_macro/adam")
with c3:
    tfl_subdir = st.text_input("TFL 子路径", value="09_txt")

st.subheader("2️⃣ 筛选条件")
col1, col2, col3 = st.columns(3)
with col1:
    selected_projects = st.multiselect(
        "项目（留空 = 全部）",
        options=list(proj_options.keys()),
        default=[],
    )
with col2:
    include_types = st.multiselect(
        "类型",
        options=["SDTM", "ADaM", "TFL"],
        default=["SDTM", "ADaM", "TFL"],
    )
with col3:
    required_choice = st.multiselect(
        "Required（可多选，留空=全部）",
        options=required_options,
        default=[],
    )

col4, col5 = st.columns(2)
with col4:
    prog_choice = st.selectbox("Programmer", options=["ALL"] + prog_options)
with col5:
    qc_prog_choice = st.selectbox("QC Programmer", options=["ALL"] + qc_prog_options)

col6, col7 = st.columns(2)
with col6:
    status_choice = st.multiselect(
        "Status（可多选，留空=全部）",
        options=status_options,
        default=[],
    )
with col7:
    qc_status_choice = st.multiselect(
        "QC Status（可多选，留空=全部）",
        options=qc_status_options,
        default=[],
    )

project_ids = [proj_options[n] for n in selected_projects] if selected_projects else None

# ============================================================
# 生成
# ============================================================
st.divider()
st.subheader("3️⃣ 生成结果")

if not include_types:
    st.warning("请至少选择一种类型（SDTM / ADaM / TFL）。")
    st.stop()

text, stats, df_ds_used, df_tfl_used, warnings = generate_batchrun(
    project_ids=project_ids,
    include_types=include_types,
    fallback_dir=fallback_dir.strip(),
    programmer=prog_choice,
    qc_programmer=qc_prog_choice,
    required_list=required_choice or None,
    status_list=status_choice or None,
    qc_status_list=qc_status_choice or None,
   subdirs={
        "sdtm": sdtm_subdir.strip(),
        "adam": adam_subdir.strip(),
        "tfl":  tfl_subdir.strip(),
    },
)

for w in warnings:
    st.warning(f"⚠️ {w}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("SDTM", stats["sdtm"])
c2.metric("ADaM", stats["adam"])
c3.metric("TFL", stats["tfl"])
c4.metric("总计", stats["total"])

if stats["total"] == 0:
    st.warning("没有匹配的记录，请调整筛选条件。")
    st.stop()

filename = f"batchrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

tab_preview, tab_ds, tab_tfl = st.tabs([
    "📝 脚本预览",
    f"📦 涉及 Datasets ({len(df_ds_used)})",
    f"📑 涉及 TFLs ({len(df_tfl_used)})",
])

with tab_preview:
    st.code(text, language="text")
    st.download_button(
        "⬇️ 下载 batchrun 脚本 (UTF-8 .txt)",
        data=text.encode("utf-8"),
        file_name=filename,
        mime="text/plain",
    )

with tab_ds:
    if df_ds_used.empty:
        st.info("无匹配的 Datasets。")
    else:
        show_cols = ["project_name", "required", "program_name", "dataset_label",
                     "programmer", "qc_programmer", "derived_type",
                     "status", "qc_status"]
        st.dataframe(
            df_ds_used[[c for c in show_cols if c in df_ds_used.columns]],
            use_container_width=True, hide_index=True,
        )

with tab_tfl:
    if df_tfl_used.empty:
        st.info("无匹配的 TFLs。")
    else:
        show_cols = ["project_name", "required", "output_number", "title",
                     "txtname", "programmer", "qc_programmer",
                     "status", "qc_status"]
        st.dataframe(
            df_tfl_used[[c for c in show_cols if c in df_tfl_used.columns]],
            use_container_width=True, hide_index=True,
        )