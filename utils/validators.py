
# utils/validators.py
import re
from datetime import date


def is_valid_project_name(name: str) -> bool:
    """项目名：非空，长度 1–50"""
    return bool(name and 1 <= len(name.strip()) <= 50)


def is_valid_date_range(start: date, end: date) -> bool:
    return start <= end


def is_valid_email_like(s: str) -> bool:
    """宽松校验用户名字段（可空）"""
    if not s:
        return True
    return bool(re.match(r"^[\w.\- ]+$", s))