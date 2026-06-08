import os
import pandas as pd
from .project import load_config, save_config, DATA_DIR, ERRORS_DIR
from .logger import log_operation


def check_project(project_dir, data_type="questionnaires"):
    config = load_config(project_dir)
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")

    if not os.path.exists(data_file):
        raise FileNotFoundError(f"数据文件不存在: {data_file}")

    df = pd.read_csv(data_file, dtype=str)
    errors = []

    required = config.get("required_fields", [])
    for idx, row in df.iterrows():
        for field in required:
            if field not in df.columns:
                errors.append(
                    {"row": idx + 1, "field": field, "type": "missing_field", "message": f"字段 '{field}' 不存在"}
                )
            elif pd.isna(row.get(field)) or str(row.get(field)).strip() == "":
                errors.append(
                    {"row": idx + 1, "field": field, "type": "empty_value", "message": f"第 {idx + 1} 行字段 '{field}' 为空"}
                )

    dup_keys = config.get("duplicate_key_fields", ["id"])
    existing_keys = [k for k in dup_keys if k in df.columns]
    if existing_keys:
        duplicated = df.duplicated(subset=existing_keys, keep=False)
        dup_rows = df[duplicated]
        for idx, row in dup_rows.iterrows():
            key_val = " / ".join(str(row[k]) for k in existing_keys)
            errors.append(
                {
                    "row": idx + 1,
                    "field": ", ".join(existing_keys),
                    "type": "duplicate",
                    "message": f"第 {idx + 1} 行键值 '{key_val}' 重复",
                }
            )

    error_file = os.path.join(project_dir, ERRORS_DIR, f"check_errors_{data_type}.csv")
    if errors:
        err_df = pd.DataFrame(errors)
        err_df.to_csv(error_file, index=False, encoding="utf-8-sig")
    else:
        if os.path.exists(error_file):
            os.remove(error_file)

    config["stats"]["checked"] = True
    save_config(project_dir, config)

    log_operation(
        project_dir,
        "check",
        f"校验 {data_type}：{len(df)} 条记录，{len(errors)} 个问题",
    )
    return errors


def get_duplicate_records(project_dir, data_type="questionnaires"):
    config = load_config(project_dir)
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")
    if not os.path.exists(data_file):
        return pd.DataFrame()

    df = pd.read_csv(data_file, dtype=str)
    dup_keys = config.get("duplicate_key_fields", ["id"])
    existing_keys = [k for k in dup_keys if k in df.columns]
    if not existing_keys:
        return pd.DataFrame()

    duplicated = df.duplicated(subset=existing_keys, keep=False)
    return df[duplicated]
