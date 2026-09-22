# pages/1_📝_项目录入.py
import streamlit as st
from datetime import date, datetime
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="项目录入", page_icon="🔧", layout="wide")

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

st.title("📝 项目录入")
# 显示上一次操作的结果提示
if "flash_msg" in st.session_state:
    st.success(st.session_state.pop("flash_msg"))

# ============================================================
# 任务阶段：预置 + 自定义
# ============================================================
PRESET_STAGES = [
    "dry-run1",
    "dry-run2",
    "dry-run3",
    "dry-run4",
    "期中分析",
    "锁库分析",
    "DSUR",
    "ISS",
    "POPPK",
]
CUSTOM_LABEL = "➕ 自定义…"


def resolve_stage(select_value: str, custom_value: str) -> str:
    """根据选择框的值决定最终 stage"""
    if select_value == CUSTOM_LABEL:
        return (custom_value or "").strip()
    return select_value


def parse_date(s, default=None):
    if not s:
        return default
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return default


tab_add, tab_manage = st.tabs(["➕ 新增项目", "🗂️ 管理项目"])

# ============================================================
# 新增
# ============================================================
with tab_add:
    st.subheader("新增项目")

    with st.form("form_add_project", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("项目名 *", placeholder="例如：STUDY-2026-001")
            lead_programmer = st.text_input("Lead Programmer *", placeholder="例如：kongyy")
        with col2:
            stage_choice = st.selectbox(
                "任务阶段 *",
                PRESET_STAGES + [CUSTOM_LABEL],
            )
            if stage_choice == CUSTOM_LABEL:
                custom_stage = st.text_input(
                    "自定义任务阶段 *",
                    placeholder="例如：中期分析-第一次",
                )
            else:
                custom_stage = ""

        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("开始时间 *", value=date.today())
        with col4:
            end_date = st.date_input("结束日期 *", value=date.today())

        project_path = st.text_input(
            "项目位置（batchrun 用，可留空）",
            placeholder=r"例如：\\server\study\project01",
            help="生成 batchrun 时，这个项目下所有文件名会拼在此路径后。留空则用页面临时填的路径。",
        )

        submitted = st.form_submit_button("✅ 提交", use_container_width=True)

    if submitted:
        final_stage = resolve_stage(stage_choice, custom_stage)
        errors = []
        if not is_valid_project_name(project_name):
            errors.append("项目名不能为空，长度 1–50 字符。")
        if not lead_programmer.strip():
            errors.append("Lead Programmer 不能为空。")
        if not final_stage:
            errors.append("任务阶段不能为空。")
        if not is_valid_date_range(start_date, end_date):
            errors.append("结束日期不能早于开始时间。")
        if not errors and get_project_by_name(project_name.strip()):
            errors.append(f"项目名已存在：{project_name.strip()}")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                new_id = create_project(
                    project_name=project_name.strip(),
                    lead_programmer=lead_programmer.strip(),
                    task_stage=final_stage,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    project_path=project_path.strip(),
                )
                st.success(f"✅ 项目创建成功！ID = {new_id}，名称 = {project_name.strip()}，阶段 = {final_stage}")
                st.balloons()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"创建失败：{e}")

# ============================================================
# 管理
# ============================================================
with tab_manage:
    st.subheader("已有项目列表")

    projects = list_projects()
    if not projects:
        st.info("暂无项目，请先到「➕ 新增项目」创建。")
    else:
        df = pd.DataFrame([dict(p) for p in projects])

        show_cols = ["id", "project_name", "lead_programmer",
                     "task_stage", "start_date", "end_date",
                     "project_path", "created_at", "updated_at"]
        show_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### 📅 项目甘特图")

        gantt_df = df.copy()
        gantt_df["start_date"] = pd.to_datetime(gantt_df["start_date"], errors="coerce")
        gantt_df["end_date"] = pd.to_datetime(gantt_df["end_date"], errors="coerce")
        gantt_df = gantt_df.dropna(subset=["start_date", "end_date"])

        # 如果 end <= start，把 end 设为 start + 1 天，保证至少有一条可见的条
        mask = gantt_df["end_date"] <= gantt_df["start_date"]
        gantt_df.loc[mask, "end_date"] = gantt_df.loc[mask, "start_date"] + pd.Timedelta(days=1)

        if gantt_df.empty:
            st.info("暂无有效的日期数据，无法生成甘特图。")
        else:
            gantt_df["项目"] = gantt_df["project_name"] + "（" + gantt_df["task_stage"].fillna("") + "）"
            fig = px.timeline(
                gantt_df,
                x_start="start_date",
                x_end="end_date",
                y="项目",
                color="lead_programmer",
                hover_data=["project_name", "task_stage", "lead_programmer", "start_date", "end_date"],
            )
            fig.update_yaxes(autorange="reversed", title=None)
            fig.update_xaxes(title=None)
            fig.update_layout(
                height=max(300, 40 * len(gantt_df) + 80),
                legend_title_text="Lead Programmer",
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("### ✏️ 编辑 / 🗑️ 删除")

        options = {f"[{p['id']}] {p['project_name']}": p["id"] for p in projects}
        selected_label = st.selectbox("选择项目", list(options.keys()))
        selected_id = options[selected_label]
        proj = get_project(selected_id)

        if proj:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("项目名（不可改）", value=proj["project_name"],
                              disabled=True, key=f"name_{selected_id}")
                new_lead = st.text_input("Lead Programmer",
                                         value=proj["lead_programmer"] or "",
                                         key=f"lead_{selected_id}")

            with col2:
                current_stage = proj["task_stage"] or ""
                # 决定下拉的默认选中项
                if current_stage in PRESET_STAGES:
                    stage_idx = PRESET_STAGES.index(current_stage)
                    stage_default = current_stage
                    custom_default = ""
                elif current_stage == "":
                    stage_idx = 0
                    stage_default = PRESET_STAGES[0]
                    custom_default = ""
                else:
                    # 非预置 -> 切到自定义
                    stage_idx = len(PRESET_STAGES)  # 指向 CUSTOM_LABEL
                    stage_default = CUSTOM_LABEL
                    custom_default = current_stage

                stage_choice = st.selectbox(
                    "任务阶段",
                    PRESET_STAGES + [CUSTOM_LABEL],
                    index=stage_idx,
                    key=f"stage_{selected_id}",
                )

                if stage_choice == CUSTOM_LABEL:
                    new_custom_stage = st.text_input(
                        "自定义任务阶段",
                        value=custom_default,
                        key=f"custom_stage_{selected_id}",
                    )
                else:
                    new_custom_stage = ""

            col3, col4 = st.columns(2)
            with col3:
                new_start = st.date_input(
                    "开始时间",
                    value=parse_date(proj["start_date"], date.today()),
                    key=f"start_{selected_id}",
                )
            with col4:
                new_end = st.date_input(
                    "结束日期",
                    value=parse_date(proj["end_date"], date.today()),
                    key=f"end_{selected_id}",
                )

            current_path = ""
            try:
                current_path = proj["project_path"] or ""
            except Exception:
                current_path = ""

            new_path = st.text_input(
                "项目位置（batchrun 用，可留空）",
                value=current_path,
                placeholder=r"例如：\\server\study\project01",
                key=f"path_{selected_id}",
            )

            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button("💾 保存修改", key=f"save_{selected_id}",
                             use_container_width=True):
                    final_stage = resolve_stage(stage_choice, new_custom_stage)
                    if not new_lead.strip():
                        st.error("Lead Programmer 不能为空。")
                    elif not final_stage:
                        st.error("任务阶段不能为空。")
                    elif not is_valid_date_range(new_start, new_end):
                        st.error("结束日期不能早于开始时间。")
                    else:
                        update_project(
                            selected_id,
                            new_lead.strip(),
                            final_stage,
                            new_start.strftime("%Y-%m-%d"),
                            new_end.strftime("%Y-%m-%d"),
                            new_path.strip(),
                        )
                        st.session_state["flash_msg"] = f"✅ 已保存（阶段 = {final_stage}）"
                        st.cache_data.clear()
                        st.rerun()
            with c2:
                with st.popover("🗑️ 删除该项目", use_container_width=True):
                    st.warning("删除项目会同时删除其 LOT、Datasets、TFLs 记录，且不可恢复。")
                    confirm = st.text_input(
                        f"请输入项目名确认删除：{proj['project_name']}",
                        key=f"confirm_del_{selected_id}",
                    )
                    if st.button("确认删除", key=f"do_del_{selected_id}",
                                 type="primary"):
                        if confirm.strip() != proj["project_name"]:
                            st.error("项目名不匹配，取消删除。")
                        else:
                            delete_project(selected_id)
                            st.success("🗑️ 已删除")
                            st.cache_data.clear()
                            st.rerun()