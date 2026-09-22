# core/batchrun.py
"""
生成 batchrun 脚本（UTF-8 txt）。
每个项目的路径来自 projects.project_path；未配置则回退 fallback_dir。
"""
import re
from typing import Iterable, List, Optional, Tuple
import pandas as pd

from core.aggregator import get_all_datasets, get_all_tfls
from core.db import get_project_paths

# 默认子路径（页面不传时使用）
DEFAULT_SUBDIRS = {
    "sdtm": "02_extraction",
    "adam": "08_macro/adam",
    "tfl":  "09_txt",
}

_SDTM_RE = re.compile(r"^[a-z]{2}\.sas$", re.IGNORECASE)
_ADAM_RE = re.compile(r"^ad[a-z0-9]+\.sas$", re.IGNORECASE)


def _is_sdtm(program_name: str) -> bool:
    return bool(program_name) and bool(_SDTM_RE.fullmatch(program_name.strip()))


def _is_adam(program_name: str) -> bool:
    if not program_name:
        return False
    name = program_name.strip()
    return bool(_ADAM_RE.fullmatch(name)) and len(name) >= 6


def _join(base_dir: str, filename: str, subdir: str = "") -> str:
    if not filename:
        return ""

    base = (base_dir or "").rstrip("\\/")
    sub = (subdir or "").strip("\\/")

    # 判断 base 的主分隔符
    if base:
        sep = "\\" if "\\" in base else "/"
    else:
        sep = "/"

    # 把 sub 里的分隔符统一成 sep
    if sub:
        sub = sub.replace("\\", sep).replace("/", sep)

    # 拼接
    if base and sub:
        base = f"{base}{sep}{sub}"
    elif sub:
        base = sub

    if not base:
        return filename
    return f"{base}{sep}{filename}"


def _apply_list_filter(df, col, values):
    """values 为 None 或空 -> 不过滤"""
    if df is None or df.empty or not values:
        return df
    if col not in df.columns:
        return df
    return df[df[col].fillna("").isin(values)]


def _apply_required(df, required_list):
    return _apply_list_filter(df, "required", required_list)


def _apply_status(df, status_list):
    return _apply_list_filter(df, "status", status_list)


def _apply_qc_status(df, qc_status_list):
    return _apply_list_filter(df, "qc_status", qc_status_list)


# ------------------------------------------------------------
# 筛选
# ------------------------------------------------------------
def filter_datasets(df, types, programmer=None, qc_programmer=None,
                    required_list=None, status_list=None, qc_status_list=None):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    wanted = set(t for t in types if t in ("SDTM", "ADaM"))
    if not wanted:
        return pd.DataFrame()

    def _type_ok(row):
        name = row.get("program_name", "") or ""
        if "SDTM" in wanted and _is_sdtm(name):
            return True
        if "ADaM" in wanted and _is_adam(name):
            return True
        return False

    out = out[out.apply(_type_ok, axis=1)]
    if programmer and programmer != "ALL":
        out = out[out["programmer"].fillna("") == programmer]
    if qc_programmer and qc_programmer != "ALL":
        out = out[out["qc_programmer"].fillna("") == qc_programmer]

    out = _apply_required(out, required_list)
    out = _apply_status(out, status_list)
    out = _apply_qc_status(out, qc_status_list)
    return out


def filter_tfls(df, programmer=None, qc_programmer=None, required_list=None,
                status_list=None, qc_status_list=None):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if programmer and programmer != "ALL":
        out = out[out["programmer"].fillna("") == programmer]
    if qc_programmer and qc_programmer != "ALL":
        out = out[out["qc_programmer"].fillna("") == qc_programmer]

    out = _apply_required(out, required_list)
    out = _apply_status(out, status_list)
    out = _apply_qc_status(out, qc_status_list)

    out = out[out["txtname"].fillna("").str.strip() != ""]
    return out


# ------------------------------------------------------------
# 生成
# ------------------------------------------------------------
def build_batchrun_lines(df_datasets, df_tfls, project_paths,
                         fallback_dir="", subdirs=None):
    """
    返回 (lines, stats, warnings)
    subdirs: {"sdtm": "...", "adam": "...", "tfl": "..."}
    """
    subdirs = subdirs or DEFAULT_SUBDIRS
    sdtm_sub = subdirs.get("sdtm", "")
    adam_sub = subdirs.get("adam", "")
    tfl_sub = subdirs.get("tfl", "")

    lines: List[str] = []
    warnings: List[str] = []
    n_sdtm = n_adam = n_tfl = 0

    def _path_for(project_id, project_name):
        p = (project_paths or {}).get(project_id, "") or ""
        if p.strip():
            return p.strip()
        if fallback_dir and fallback_dir.strip():
            warnings.append(f"项目 [{project_name}] 未配置项目位置，已回退到统一路径。")
            return fallback_dir.strip()
        warnings.append(f"项目 [{project_name}] 未配置项目位置，且未提供统一路径，输出仅文件名。")
        return ""

    # ---- Datasets (SDTM / ADaM) ----
    if df_datasets is not None and not df_datasets.empty:
        for _, row in df_datasets.iterrows():
            name = (row.get("program_name") or "").strip()
            if not name:
                continue
            if _is_sdtm(name):
                n_sdtm += 1
                subdir = sdtm_sub
            elif _is_adam(name):
                n_adam += 1
                subdir = adam_sub
            else:
                continue
            base = _path_for(row.get("project_id"), row.get("project_name", ""))
            lines.append(_join(base, name, subdir))

    # ---- TFLs ----
    if df_tfls is not None and not df_tfls.empty:
        for _, row in df_tfls.iterrows():
            txt = (row.get("txtname") or "").strip()
            if not txt:
                continue
            n_tfl += 1
            base = _path_for(row.get("project_id"), row.get("project_name", ""))
            lines.append(_join(base, txt, tfl_sub))

    warnings = list(dict.fromkeys(warnings))
    stats = {"sdtm": n_sdtm, "adam": n_adam, "tfl": n_tfl, "total": len(lines)}
    return lines, stats, warnings

def build_batchrun_text(lines: List[str]) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------
# 一次性入口
# ------------------------------------------------------------
def generate_batchrun(
    project_ids: Optional[List[int]],
    include_types: Iterable[str],
    fallback_dir: str = "",
    programmer: Optional[str] = None,
    qc_programmer: Optional[str] = None,
    required_list: Optional[List[str]] = None,
    status_list: Optional[List[str]] = None,
    qc_status_list: Optional[List[str]] = None,
    subdirs: Optional[dict] = None,
) -> Tuple[str, dict, pd.DataFrame, pd.DataFrame, List[str]]:
    """
    返回 (text, stats, df_ds_used, df_tfl_used, warnings)
    """
    include_types = set(include_types or [])

    df_ds_all = get_all_datasets(project_ids)
    df_tfl_all = get_all_tfls(project_ids)

    ds_types = {t for t in include_types if t in ("SDTM", "ADaM")}
    if ds_types:
        df_ds_used = filter_datasets(
            df_ds_all, ds_types, programmer, qc_programmer,
            required_list, status_list, qc_status_list,
        )
    else:
        df_ds_used = pd.DataFrame()

    if "TFL" in include_types:
        df_tfl_used = filter_tfls(
            df_tfl_all, programmer, qc_programmer,
            required_list, status_list, qc_status_list,
        )
    else:
        df_tfl_used = pd.DataFrame()

    involved_pids = set()
    for df in (df_ds_used, df_tfl_used):
        if df is not None and not df.empty and "project_id" in df.columns:
            involved_pids.update(df["project_id"].dropna().astype(int).tolist())
    project_paths = get_project_paths(list(involved_pids)) if involved_pids else {}

    lines, stats, warnings = build_batchrun_lines(
        df_ds_used, df_tfl_used, project_paths, fallback_dir
    )
    text = build_batchrun_text(lines)
    return text, stats, df_ds_used, df_tfl_used, warnings