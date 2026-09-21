# core/aggregator.py
"""
合并所有项目（或指定项目）的 Datasets / TFLs，返回 DataFrame。
只取每个项目的“活跃” LOT 记录。
"""
from typing import List, Optional
import pandas as pd

from core.db import get_client


def _active_lot_map(project_ids: Optional[List[int]] = None) -> dict:
    """
    返回 {project_id: lot_file_id}，仅包含 is_active=1 的 LOT。
    project_ids=None 表示全部项目。
    """
    client = get_client()
    query = client.table("lot_files").select("project_id, id").eq("is_active", 1)
    if project_ids:
        query = query.in_("project_id", project_ids)
    res = query.execute()
    return {row["project_id"]: row["id"] for row in res.data}


def _fetch_table(table: str, lot_ids: List[int], columns: str) -> pd.DataFrame:
    """按活跃 lot_ids 拉取指定表，并 join 上 project_name"""
    if not lot_ids:
        return pd.DataFrame()

    client = get_client()

    # 拉取主表数据
    res = client.table(table).select(columns).in_("lot_file_id", lot_ids).execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)

    # 拉取项目名映射
    project_ids = df["project_id"].unique().tolist()
    proj_res = client.table("projects").select("id, project_name").in_("id", project_ids).execute()
    proj_map = {row["id"]: row["project_name"] for row in proj_res.data}

    # 附加 project_name 列
    df["project_name"] = df["project_id"].map(proj_map)

    # 按项目名 + 指定列排序
    sort_col = "program_name" if table == "datasets" else "output_number"
    if sort_col in df.columns:
        df = df.sort_values(["project_name", sort_col], na_position="last")

    return df


def get_all_datasets(project_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """返回合并后的 Datasets DataFrame，附加 project_name 列。"""
    active = _active_lot_map(project_ids)
    if not active:
        return pd.DataFrame()

    columns = (
        "id, project_id, lot_file_id, required, dataset_label, program_name, "
        "output_name, programmer, output_date, status, qc_programmer, "
        "qc_program_name, qc_completion_date, qc_status, derived_type, comments"
    )
    return _fetch_table("datasets", list(active.values()), columns)


def get_all_tfls(project_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """返回合并后的 TFLs DataFrame，附加 project_name 列。"""
    active = _active_lot_map(project_ids)
    if not active:
        return pd.DataFrame()

    columns = (
        "id, project_id, lot_file_id, required, output_type, tfl_category, "
        "output_number, title, repeated, txtname, rtfname, macro, "
        "programmer, output_date, status, qc_programmer, qc_program_name, "
        "qc_completion_date, qc_status, comments"
    )
    return _fetch_table("tfls", list(active.values()), columns)