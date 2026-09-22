# core/db.py
import os
import streamlit as st
from supabase import create_client, Client, ClientOptions
from typing import List, Optional


def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    token = st.session_state.get("access_token")

    if token:
        # 关键：在创建客户端时就把 JWT 写进全局 header
        options = ClientOptions(
            headers={"Authorization": f"Bearer {token}"}
        )
        client = create_client(url, key, options=options)
    else:
        client = create_client(url, key)

    return client

def init_db() -> None:
    """表已在 Supabase 建好，保留空函数兼容旧调用"""
    pass


# ============================================================
# Project CRUD
# ============================================================
def create_project(project_name: str,
                   lead_programmer: str,
                   task_stage: str,
                   start_date: str,
                   end_date: str,
                   project_path: str = "") -> int:
    """新增项目，返回新 id；若项目名重复抛 ValueError"""
    client = get_client()

    # 先检查重名
    existing = (
        client.table("projects")
        .select("id")
        .eq("project_name", project_name.strip())
        .eq("user_id", st.session_state["user"].id)
        .execute()
    )
    if existing.data:
        raise ValueError(f"项目名已存在：{project_name}")

    payload = {
        "project_name": project_name.strip(),
        "lead_programmer": lead_programmer,
        "task_stage": task_stage,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "project_path": project_path.strip(),
        "user_id": st.session_state["user"].id,  # ← 关键：显式带上当前用户 ID
    }
    res = client.table("projects").insert(payload).execute()
    return res.data[0]["id"]


def list_projects() -> List[dict]:
    """返回所有项目（按创建时间倒序）"""
    client = get_client()
    res = client.table("projects").select("*").order("created_at", desc=True).execute()
    return res.data


def get_project(project_id: int) -> Optional[dict]:
    client = get_client()
    res = client.table("projects").select("*").eq("id", project_id).execute()
    return res.data[0] if res.data else None


def get_project_by_name(project_name: str) -> Optional[dict]:
    client = get_client()
    res = client.table("projects").select("*").eq("project_name", project_name).execute()
    return res.data[0] if res.data else None


def update_project(project_id: int,
                   lead_programmer: str,
                   task_stage: str,
                   start_date: str,
                   end_date: str,
                   project_path: str = "") -> None:
    """更新项目（项目名不允许改）"""
    client = get_client()
    client.table("projects").update({
        "lead_programmer": lead_programmer,
        "task_stage": task_stage,
        "start_date": start_date or None,
        "end_date": end_date or None,
        "project_path": project_path.strip(),
        "updated_at": "now()",
    }).eq("id", project_id).execute()


def delete_project(project_id: int) -> None:
    """删除项目（级联删除 lot_files / datasets / tfls）"""
    client = get_client()
    client.table("projects").delete().eq("id", project_id).execute()


def project_exists(project_name: str) -> bool:
    client = get_client()
    res = client.table("projects").select("id").eq("project_name", project_name.strip()).limit(1).execute()
    return len(res.data) > 0


# ============================================================
# LOT 文件 & Datasets / TFLs CRUD
# ============================================================

def _clean(v):
    """空字符串转 None，供 date 类型字段使用"""
    if v is None or v is Ellipsis:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

def add_lot_file(project_id: int, file_name: str, file_path: str) -> int:
    client = get_client()
    client.table("lot_files").update({"is_active": 0}).eq("project_id", project_id).execute()
    
    payload = {
        "project_id": project_id,
        "file_name": file_name,
        "file_path": file_path,
        "is_active": 1,
        "user_id": st.session_state["user"].id,
    }
    print("[DEBUG] add_lot_file payload:", payload)  # ← 打印出来
    for k, v in payload.items():
        print(f"  {k}: {type(v)} = {v!r}")  # ← 逐个打印类型
    
    res = client.table("lot_files").insert(payload).execute()
    return res.data[0]["id"]


def bulk_insert_datasets(project_id: int, lot_file_id: int, rows: List[dict]) -> int:
    if not rows:
        return 0
    fields = [
        "required", "dataset_label", "program_name", "output_name",
        "programmer", "output_date", "status", "qc_programmer",
        "qc_program_name", "qc_completion_date", "qc_status",
        "comments", "derived_type",
    ]
    # date 类型字段，空值必须转 None
    date_fields = {"output_date", "qc_completion_date"}

    client = get_client()
    uid = st.session_state["user"].id
    payload = []
    for r in rows:
        item = {"project_id": project_id, "lot_file_id": lot_file_id, "user_id": uid}
        for f in fields:
            v = r.get(f, "")
            if f in date_fields:
                item[f] = _clean(v)   # 空字符串 → None
            else:
                item[f] = v if v is not None else ""
        payload.append(item)
    client.table("datasets").insert(payload).execute()
    return len(payload)


def _clean(v):
    """空字符串转 None，供 date 类型字段使用"""
    if v is None or v is Ellipsis:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def bulk_insert_tfls(project_id: int, lot_file_id: int, rows: List[dict]) -> int:
    if not rows:
        return 0
    fields = [
        "required", "output_type", "tfl_category", "output_number",
        "title", "repeated", "txtname", "rtfname", "macro",
        "programmer", "output_date", "status",
        "qc_programmer", "qc_program_name", "qc_completion_date",
        "qc_status", "comments",
    ]
    # date 类型字段，空值必须转 None
    date_fields = {"output_date", "qc_completion_date"}

    client = get_client()
    uid = st.session_state["user"].id
    payload = []
    for r in rows:
        item = {"project_id": project_id, "lot_file_id": lot_file_id, "user_id": uid}
        for f in fields:
            v = r.get(f, "")
            if f in date_fields:
                item[f] = _clean(v)   # 空字符串 → None
            else:
                item[f] = v if v is not None else ""
        payload.append(item)
    client.table("tfls").insert(payload).execute()
    return len(payload)


def list_lot_files(project_id: int) -> List[dict]:
    client = get_client()
    res = client.table("lot_files").select("*").eq("project_id", project_id).order("uploaded_at", desc=True).execute()
    return res.data


def get_lot_file(lot_file_id: int) -> Optional[dict]:
    client = get_client()
    res = client.table("lot_files").select("*").eq("id", lot_file_id).execute()
    return res.data[0] if res.data else None


def delete_lot_file(lot_file_id: int) -> None:
    """删除 LOT 记录（级联删除其 datasets / tfls）"""
    client = get_client()
    client.table("lot_files").delete().eq("id", lot_file_id).execute()


def activate_lot_file(lot_file_id: int) -> None:
    """把某个 LOT 设为活跃，同时该项目其它 LOT 置为非活跃"""
    client = get_client()
    lot = get_lot_file(lot_file_id)
    if not lot:
        return
    project_id = lot["project_id"]
    client.table("lot_files").update({"is_active": 0}).eq("project_id", project_id).execute()
    client.table("lot_files").update({"is_active": 1}).eq("id", lot_file_id).execute()


def count_datasets(lot_file_id: int) -> int:
    client = get_client()
    res = client.table("datasets").select("id", count="exact").eq("lot_file_id", lot_file_id).execute()
    return res.count or 0


def count_tfls(lot_file_id: int) -> int:
    client = get_client()
    res = client.table("tfls").select("id", count="exact").eq("lot_file_id", lot_file_id).execute()
    return res.count or 0


def list_datasets_by_project(project_id: int) -> List[dict]:
    client = get_client()
    res = client.table("datasets").select("*").eq("project_id", project_id).execute()
    return res.data


def list_tfls_by_project(project_id: int) -> List[dict]:
    client = get_client()
    res = client.table("tfls").select("*").eq("project_id", project_id).execute()
    return res.data


def get_project_paths(project_ids=None) -> dict:
    """返回 {project_id: project_path}，未设置的返回空字符串。"""
    client = get_client()
    if project_ids:
        res = client.table("projects").select("id, project_path").in_("id", project_ids).execute()
    else:
        res = client.table("projects").select("id, project_path").execute()
    return {row["id"]: (row["project_path"] or "") for row in res.data}