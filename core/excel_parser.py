# core/excel_parser.py
"""
解析 LOT Excel 文件：
- sheet "Datasets"：列 Required / Dataset Label / Program Name / Output Name /
  Programmer / Output Date / Status / QC Programmer / QC Program Name /
  QC Completion Date / QC Status / Comments/Resolutions
- sheet "TFLs"：列 Required / Output Type / TFL Category / Output Number /
  Title / Repeated / TxtName / RTFName / Macro / Programmer / Output Date /
  Status / QC Programmer / QC Program Name / QC Completion Date /
  QC Status / Comments/Resolutions
"""
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

from core.classifier import classify_dataset

# ---------- 列名映射：Excel 表头 -> 数据库字段 ----------
DATASET_COL_MAP = {
    "Required": "required",
    "Dataset Label": "dataset_label",
    "Program Name": "program_name",
    "Output Name": "output_name",
    "Programmer": "programmer",
    "Output Date": "output_date",
    "Status": "status",
    "QC Programmer": "qc_programmer",
    "QC Program Name": "qc_program_name",
    "QC Completion Date": "qc_completion_date",
    "QC Status": "qc_status",
    "Comments/Resolutions": "comments",
}

TFL_COL_MAP = {
    "Required": "required",
    "Output Type": "output_type",
    "TFL Category": "tfl_category",
    "Output Number": "output_number",
    "Title": "title",
    "Repeated": "repeated",
    "TxtName": "txtname",
    "RTFName": "rtfname",
    "Macro": "macro",
    "Programmer": "programmer",
    "Output Date": "output_date",
    "Status": "status",
    "QC Programmer": "qc_programmer",
    "QC Program Name": "qc_program_name",
    "QC Completion Date": "qc_completion_date",
    "QC Status": "qc_status",
    "Comments/Resolutions": "comments",
}


class ExcelParseError(Exception):
    pass


def _norm(s: str) -> str:
    """标准化表头：去掉首尾空格、多个空格合并，比较用"""
    if s is None:
        return ""
    return " ".join(str(s).strip().split())


def _build_rename_map(df: pd.DataFrame, expected: Dict[str, str]) -> Dict[str, str]:
    """
    根据 expected（Excel 表头 -> db 字段）找到 df 中实际匹配的列，
    返回 {df 里真实列名: db 字段名}
    """
    actual_norm = {_norm(c): c for c in df.columns}
    rename = {}
    missing = []
    for excel_col, db_field in expected.items():
        key = _norm(excel_col)
        if key in actual_norm:
            rename[actual_norm[key]] = db_field
        else:
            missing.append(excel_col)
    return rename, missing


def _clean_value(v):
    """把 NaN / NaT 转成空字符串"""
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if pd.isna(v):
        return ""
    return str(v).strip()


def parse_lot_excel(file_path: str | Path) -> Tuple[List[dict], List[dict], List[str]]:
    """
    解析 Excel，返回 (datasets, tfls, warnings)
    - datasets: List[dict]，字段名与 DB 列对齐（不含 project_id/lot_file_id，由调用方补）
    - tfls:     List[dict]，同上
    - warnings: List[str]，非致命问题提示（例如某 sheet 缺列）
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ExcelParseError(f"文件不存在：{file_path}")

    warnings: List[str] = []

    try:
        xls = pd.read_excel(file_path, sheet_name=None, dtype=str)
    except Exception as e:
        raise ExcelParseError(f"读取 Excel 失败：{e}") from e

    # ---------- 定位 sheet（允许名字大小写/空格差异） ----------
    def find_sheet(name_candidates):
        for actual in xls.keys():
            if _norm(actual).lower() in [n.lower() for n in name_candidates]:
                return actual
        return None

    ds_sheet = find_sheet(["Datasets"])
    tfl_sheet = find_sheet(["TFLs"])

    if ds_sheet is None and tfl_sheet is None:
        raise ExcelParseError("未找到 'Datasets' 或 'TFLs' sheet。")

    datasets: List[dict] = []
    tfls: List[dict] = []

    # ---------- 解析 Datasets ----------
    if ds_sheet is None:
        warnings.append("未找到 'Datasets' sheet，跳过。")
    else:
        df = xls[ds_sheet]
        df.columns = [_norm(c) for c in df.columns]
        rename_map, missing = _build_rename_map(df, DATASET_COL_MAP)
        if missing:
            warnings.append(f"Datasets sheet 缺少列：{missing}（已忽略）")
        df = df.rename(columns=rename_map)

        # 只保留识别的字段
        keep = [v for v in DATASET_COL_MAP.values() if v in df.columns]
        df = df[keep].copy()

        for _, row in df.iterrows():
            rec = {k: _clean_value(row.get(k, "")) for k in keep}
            # 全空行跳过
            if not any(rec.values()):
                continue
            rec["derived_type"] = classify_dataset(rec.get("program_name", ""))
            datasets.append(rec)

    # ---------- 解析 TFLs ----------
    if tfl_sheet is None:
        warnings.append("未找到 'TFLs' sheet，跳过。")
    else:
        df = xls[tfl_sheet]
        df.columns = [_norm(c) for c in df.columns]
        rename_map, missing = _build_rename_map(df, TFL_COL_MAP)
        if missing:
            warnings.append(f"TFLs sheet 缺少列：{missing}（已忽略）")
        df = df.rename(columns=rename_map)

        keep = [v for v in TFL_COL_MAP.values() if v in df.columns]
        df = df[keep].copy()

        for _, row in df.iterrows():
            rec = {k: _clean_value(row.get(k, "")) for k in keep}
            if not any(rec.values()):
                continue
            tfls.append(rec)

    return datasets, tfls, warnings


def preview_lot_excel(file_path: str | Path, n: int = 5) -> Dict[str, pd.DataFrame]:
    """
    返回预览用 DataFrame：{'Datasets': df, 'TFLs': df}，仅取前 n 行
    """
    xls = pd.read_excel(file_path, sheet_name=None, dtype=str)
    out = {}
    for k, df in xls.items():
        out[_norm(k)] = df.head(n)
    return out
