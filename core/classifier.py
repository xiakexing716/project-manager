# core/classifier.py
"""
根据 Program Name 判断数据类型：
- SDTM：两个字母 + .sas，例如 dm.sas / ae.sas
- ADaM：ad 开头 + 若干字母数字 + .sas，长度 >= 6，例如 adae.sas / adsl.sas
- UNKNOWN：其他
"""
import re

_SDTM_RE = re.compile(r"^[a-z]{2}\.sas$", re.IGNORECASE)
_ADAM_RE = re.compile(r"^ad[a-z0-9]+\.sas$", re.IGNORECASE)


def classify_dataset(program_name: str) -> str:
    if not program_name:
        return "UNKNOWN"
    name = program_name.strip()
    if _SDTM_RE.fullmatch(name):
        return "SDTM"
    if _ADAM_RE.fullmatch(name) and len(name) >= 6:
        return "ADaM"
    return "UNKNOWN"
