# pages/2_📤_LOT上传与管理.py
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

st.set_page_config(page_title="LOT 上传与管理", page_icon="�", layout="wide")

# ===== 登录检查 =====
if "user" not in st.session_state:
    st.error("请先登录")
    st.stop()

from datetime import date, datetime
import pandas as pd
import plotly.express as px
from core.db import (
    create_project, list_projects, get_project,
    get_project_by_name, update_project, delete_project,
)
from utils.validators import is_valid_project_name, is_valid_date_range

from core.db import (
    init_db, list_projects, get_project,
    add_lot_file, bulk_insert_datasets, bulk_insert_tfls,
    list_lot_files, delete_lot_file, activate_lot_file,
    count_datasets, count_tfls,
    list_datasets_by_project, list_tfls_by_project,
)
from core.excel_parser import parse_lot_excel, ExcelParseError, preview_lot_excel
from utils.paths import project_upload_dir

st.title("📤 LOT 上传与管理")

# ============================================================
# 选择项目
# ============================================================
projects = list_projects()
if not projects:
    st.warning("还没有项目，请先到「📝 项目录入」页面创建。")
    st.stop()

options = {f"[{p['id']}] {p['project_name']}": p["id"] for p in projects}
selected_label = st.selectbox("选择项目", list(options.keys()))
project_id = options[selected_label]
project = get_project(project_id)

try:
    proj_path = project["project_path"] or ""
except Exception:
    proj_path = ""

st.caption(
    f"Lead Programmer: **{project['lead_programmer'] or '-'}** ｜ "
    f"阶段: **{project['task_stage'] or '-'}** ｜ "
    f"时间: **{project['start_date']} ~ {project['end_date']}**"
    + (f" ｜ 位置: `{proj_path}`" if proj_path else " ｜ 位置: ⚠️ 未配置")
)

st.divider()

# ============================================================
# 上传区
# ============================================================
st.subheader("📥 上传新的 LOT Excel")

uploaded = st.file_uploader(
    "拖拽或选择 .xlsx 文件（需包含 'Datasets' 和 'TFLs' sheet）",
    type=["xlsx", "xls"],
    accept_multiple_files=False,
)

if uploaded is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    try:
        ds_rows, tfl_rows, warns = parse_lot_excel(tmp_path)
    except ExcelParseError as e:
        st.error(f"❌ 解析失败：{e}")
        st.stop()

    for w in warns:
        st.warning(f"⚠️ {w}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Datasets 行数", len(ds_rows))
    c2.metric("TFLs 行数", len(tfl_rows))
    c3.metric("文件大小", f"{uploaded.size / 1024:.1f} KB")

    # ---------- 关键字段为空提示 ----------
    empty_prog = [r for r in ds_rows if not (r.get("program_name") or "").strip()]
    empty_txt = [r for r in tfl_rows if not (r.get("txtname") or "").strip()]
    if empty_prog:
        st.warning(f"⚠️ Datasets 中有 {len(empty_prog)} 行 Program Name 为空，batchrun 时会跳过。")
    if empty_txt:
        st.warning(f"⚠️ TFLs 中有 {len(empty_txt)} 行 TxtName 为空，batchrun 时会跳过。")

    # ---------- 与数据库重复检测 ----------
    existing_ds_programs = {
        (r["program_name"] or "").strip().lower()
        for r in list_datasets_by_project(project_id)
        if (r["program_name"] or "").strip()
    }
    existing_tfl_txts = {
        (r["txtname"] or "").strip().lower()
        for r in list_tfls_by_project(project_id)
        if (r["txtname"] or "").strip()
    }

    new_ds_programs = [(r.get("program_name") or "").strip() for r in ds_rows]
    new_tfl_txts = [(r.get("txtname") or "").strip() for r in tfl_rows]

    dup_ds = sorted({p for p in new_ds_programs
                     if p and p.lower() in existing_ds_programs})
    dup_tfl = sorted({t for t in new_tfl_txts
                      if t and t.lower() in existing_tfl_txts})

    if dup_ds:
        preview = ", ".join(dup_ds[:10]) + (" 等" if len(dup_ds) > 10 else "")
        st.warning(f"⚠️ 以下 Datasets Program Name 在当前项目中已存在（共 {len(dup_ds)} 条）：{preview}")
    if dup_tfl:
        preview = ", ".join(dup_tfl[:10]) + (" 等" if len(dup_tfl) > 10 else "")
        st.warning(f"⚠️ 以下 TFLs TxtName 在当前项目中已存在（共 {len(dup_tfl)} 条）：{preview}")

    # ---------- 文件内部重复检测 ----------
    seen, internal_dup_ds = set(), []
    for p in new_ds_programs:
        key = p.lower()
        if not key:
            continue
        if key in seen:
            internal_dup_ds.append(p)
        seen.add(key)

    seen, internal_dup_tfl = set(), []
    for t in new_tfl_txts:
        key = t.lower()
        if not key:
            continue
        if key in seen:
            internal_dup_tfl.append(t)
        seen.add(key)

    if internal_dup_ds:
        st.info(f"ℹ️ 本文件内 Datasets Program Name 重复 {len(internal_dup_ds)} 条："
                f"{', '.join(sorted(set(internal_dup_ds))[:10])}")
    if internal_dup_tfl:
        st.info(f"ℹ️ 本文件内 TFLs TxtName 重复 {len(internal_dup_tfl)} 条："
                f"{', '.join(sorted(set(internal_dup_tfl))[:10])}")

    # ---------- 预览 ----------
    with st.expander("👀 预览前 5 行", expanded=False):
        try:
            preview = preview_lot_excel(tmp_path, n=5)
            for sheet_name, df in preview.items():
                st.markdown(f"**{sheet_name}**")
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.info(f"预览失败：{e}")

    # ---------- 落盘 ----------
    pdir = project_upload_dir(project["project_name"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{ts}_{uploaded.name}"
    saved_path = pdir / saved_name

    if st.button("✅ 确认导入", type="primary", use_container_width=True):
        try:
            with open(saved_path, "wb") as f:
                f.write(uploaded.getbuffer())

            lot_id = add_lot_file(project_id, uploaded.name, str(saved_path))
            n_ds = bulk_insert_datasets(project_id, lot_id, ds_rows)
            n_tfl = bulk_insert_tfls(project_id, lot_id, tfl_rows)

            st.success(f"🎉 导入成功！LOT ID = {lot_id}，Datasets {n_ds} 条，TFLs {n_tfl} 条。")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"❌ 导入失败：{e}")
            try:
                Path(saved_path).unlink(missing_ok=True)
            except Exception:
                pass

st.divider()

# ============================================================
# 已上传 LOT 列表
# ============================================================
st.subheader("🗂️ 已上传的 LOT 文件")

lots = list_lot_files(project_id)
if not lots:
    st.info("该项目还没有上传 LOT。")
else:
    for lot in lots:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
            with col1:
                active_tag = "🟢 活跃" if lot["is_active"] else "⚪ 非活跃"
                st.markdown(f"**{lot['file_name']}**  {active_tag}")
                st.caption(f"上传时间：{lot['uploaded_at']}")
            with col2:
                st.metric("Datasets", count_datasets(lot["id"]))
            with col3:
                st.metric("TFLs", count_tfls(lot["id"]))
            with col4:
                try:
                    with open(lot["file_path"], "rb") as f:
                        st.download_button(
                            "⬇️ 下载原文件",
                            data=f.read(),
                            file_name=lot["file_name"],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{lot['id']}",
                            use_container_width=True,
                        )
                except Exception:
                    st.caption("原文件缺失")

                if not lot["is_active"]:
                    if st.button("🔁 设为活跃",
                                 key=f"act_{lot['id']}",
                                 use_container_width=True):
                        activate_lot_file(lot["id"])
                        st.success("已切换为活跃 LOT")
                        st.rerun()

                with st.popover("🗑️ 删除", use_container_width=True):
                    st.warning("删除后该 LOT 的 Datasets / TFLs 记录也会被删除。")
                    if st.button("确认删除", key=f"del_{lot['id']}", type="primary"):
                        delete_lot_file(lot["id"])
                        try:
                            Path(lot["file_path"]).unlink(missing_ok=True)
                        except Exception:
                            pass
                        st.success("已删除")
                        st.rerun()

# ============================================================
# 当前项目数据概览
# ============================================================
st.divider()
st.subheader("👀 当前项目数据概览")

ds = list_datasets_by_project(project_id)
tfl = list_tfls_by_project(project_id)

tab_ds, tab_tfl = st.tabs([f"📦 Datasets ({len(ds)})", f"📑 TFLs ({len(tfl)})"])

with tab_ds:
    if not ds:
        st.info("暂无 Datasets 数据。")
    else:
        df = pd.DataFrame([dict(r) for r in ds])
        cols = ["required", "dataset_label", "program_name", "output_name",
                "programmer", "output_date", "status",
                "qc_programmer", "qc_program_name",
                "qc_completion_date", "qc_status",
                "derived_type", "comments"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)

with tab_tfl:
    if not tfl:
        st.info("暂无 TFLs 数据。")
    else:
        df = pd.DataFrame([dict(r) for r in tfl])
        cols = ["required", "output_type", "tfl_category", "output_number",
                "title", "repeated", "txtname", "rtfname",
                "programmer", "output_date", "status",
                "qc_programmer", "qc_program_name",
                "qc_completion_date", "qc_status", "comments"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)