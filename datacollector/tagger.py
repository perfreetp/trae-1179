import os
import pandas as pd
from .project import load_config, save_config, DATA_DIR
from .logger import log_operation


def tag_records(project_dir, ids, tag_name, data_type="questionnaires"):
    config = load_config(project_dir)
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")

    if not os.path.exists(data_file):
        raise FileNotFoundError(f"数据文件不存在: {data_file}")

    df = pd.read_csv(data_file, dtype=str)

    if "_tags" not in df.columns:
        df["_tags"] = ""

    dup_keys = config.get("duplicate_key_fields", ["id"])
    key_field = dup_keys[0] if dup_keys else "id"

    count = 0
    for record_id in ids:
        mask = df[key_field].astype(str) == str(record_id)
        if mask.any():
            for idx in df[mask].index:
                existing = str(df.at[idx, "_tags"])
                tags = [t.strip() for t in existing.split(",") if t.strip()] if existing else []
                if tag_name not in tags:
                    tags.append(tag_name)
                df.at[idx, "_tags"] = ",".join(tags)
                count += 1

    df.to_csv(data_file, index=False, encoding="utf-8-sig")

    config["stats"]["tagged_count"] = int((df["_tags"] != "").sum())
    save_config(project_dir, config)

    log_operation(
        project_dir,
        "tag",
        f"为 {count} 条记录打标签 '{tag_name}'",
    )
    return count


def remove_tag(project_dir, ids, tag_name, data_type="questionnaires"):
    config = load_config(project_dir)
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")

    if not os.path.exists(data_file):
        raise FileNotFoundError(f"数据文件不存在: {data_file}")

    df = pd.read_csv(data_file, dtype=str)

    if "_tags" not in df.columns:
        return 0

    dup_keys = config.get("duplicate_key_fields", ["id"])
    key_field = dup_keys[0] if dup_keys else "id"

    count = 0
    for record_id in ids:
        mask = df[key_field].astype(str) == str(record_id)
        if mask.any():
            for idx in df[mask].index:
                existing = str(df.at[idx, "_tags"])
                tags = [t.strip() for t in existing.split(",") if t.strip() and t.strip() != tag_name]
                df.at[idx, "_tags"] = ",".join(tags)
                count += 1

    df.to_csv(data_file, index=False, encoding="utf-8-sig")

    config["stats"]["tagged_count"] = int((df["_tags"] != "").sum())
    save_config(project_dir, config)

    log_operation(project_dir, "tag_remove", f"从 {count} 条记录移除标签 '{tag_name}'")
    return count
