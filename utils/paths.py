
# utils/paths.py
from pathlib import Path

# 项目根目录：utils/paths.py -> utils -> 项目根
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "projects.db"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def project_upload_dir(project_name: str) -> Path:
    """返回某个项目的上传目录，若不存在则创建"""
    safe_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_", " "))
    p = UPLOAD_DIR / safe_name.strip()
    p.mkdir(parents=True, exist_ok=True)
    return p