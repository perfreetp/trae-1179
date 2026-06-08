import os
import pandas as pd
from .project import load_config, save_config, DATA_DIR, MERGED_DIR
from .logger import log_operation


def merge_projects(target_project_dir, source_project_dirs, data_type="questionnaires"):
    config = load_config(target_project_dir)
    target_file = os.path.join(target_project_dir, DATA_DIR, f"{data_type}.csv")

    if os.path.exists(target_file):
        combined = pd.read_csv(target_file, dtype=str)
    else:
        combined = pd.DataFrame()

    total_new = 0
    for src_dir in source_project_dirs:
        src_file = os.path.join(src_dir, DATA_DIR, f"{data_type}.csv")
        if not os.path.exists(src_file):
            continue
        src_df = pd.read_csv(src_file, dtype=str)
        src_name = os.path.basename(os.path.abspath(src_dir))
        if "_source" not in src_df.columns:
            src_df["_source"] = src_name
        combined = pd.concat([combined, src_df], ignore_index=True)
        total_new += len(src_df)

    dup_keys = config.get("duplicate_key_fields", ["id"])
    existing_keys = [k for k in dup_keys if k in combined.columns]
    if existing_keys:
        combined = combined.drop_duplicates(subset=existing_keys, keep="first")

    combined.to_csv(target_file, index=False, encoding="utf-8-sig")

    merged_file = os.path.join(target_project_dir, MERGED_DIR, f"merged_{data_type}.csv")
    combined.to_csv(merged_file, index=False, encoding="utf-8-sig")

    config["stats"]["total_records"] = len(combined)
    save_config(target_project_dir, config)

    log_operation(
        target_project_dir,
        "merge",
        f"合并 {len(source_project_dirs)} 个项目，新增 {total_new} 条，去重后 {len(combined)} 条",
    )
    return len(combined)
