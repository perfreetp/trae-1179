import json
import os
from datetime import datetime

PROJECT_CONFIG_FILE = "project.json"
DATA_DIR = "data"
PHOTOS_DIR = "photos"
LOGS_DIR = "device_logs"
QUESTIONNAIRES_DIR = "questionnaires"
SAMPLES_DIR = "samples"
MERGED_DIR = "merged"
EXPORT_DIR = "export"
REPORT_DIR = "report"
ERRORS_DIR = "errors"


def _default_config(name):
    return {
        "name": name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "required_fields": [
            "id",
            "name",
            "region",
            "date",
        ],
        "sensitive_fields": ["phone", "id_number", "address"],
        "duplicate_key_fields": ["id"],
        "region_field": "region",
        "date_field": "date",
        "photo_id_field": "id",
        "stats": {
            "total_records": 0,
            "total_photos": 0,
            "tagged_count": 0,
            "checked": False,
        },
    }


def init_project(project_dir, name=None):
    if os.path.exists(project_dir):
        raise FileExistsError(f"项目目录已存在: {project_dir}")

    os.makedirs(project_dir)
    for subdir in [
        DATA_DIR,
        PHOTOS_DIR,
        LOGS_DIR,
        QUESTIONNAIRES_DIR,
        SAMPLES_DIR,
        MERGED_DIR,
        EXPORT_DIR,
        REPORT_DIR,
        ERRORS_DIR,
    ]:
        os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)

    if name is None:
        name = os.path.basename(os.path.abspath(project_dir))

    config = _default_config(name)
    config_path = os.path.join(project_dir, PROJECT_CONFIG_FILE)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return config


def load_config(project_dir):
    config_path = os.path.join(project_dir, PROJECT_CONFIG_FILE)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"项目配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(project_dir, config):
    config_path = os.path.join(project_dir, PROJECT_CONFIG_FILE)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
