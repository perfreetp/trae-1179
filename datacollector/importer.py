import os
import shutil
import json
import pandas as pd
from .project import (
    load_config,
    save_config,
    DATA_DIR,
    PHOTOS_DIR,
    LOGS_DIR,
    QUESTIONNAIRES_DIR,
)
from .logger import log_operation


def import_questionnaire(project_dir, file_path):
    config = load_config(project_dir)
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError(f"不支持的问卷文件格式: {ext}")

    target_dir = os.path.join(project_dir, QUESTIONNAIRES_DIR)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    dest = os.path.join(target_dir, f"{base_name}.csv")
    df.to_csv(dest, index=False, encoding="utf-8-sig")

    data_csv = os.path.join(project_dir, DATA_DIR, "questionnaires.csv")
    if os.path.exists(data_csv):
        existing = pd.read_csv(data_csv, dtype=str)
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df
    combined.to_csv(data_csv, index=False, encoding="utf-8-sig")

    config["stats"]["total_records"] = len(combined)
    save_config(project_dir, config)

    log_operation(project_dir, "import_questionnaire", f"导入问卷 {file_path}，{len(df)} 条记录")
    return len(df)


def import_device_log(project_dir, file_path):
    config = load_config(project_dir)
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError("JSON 日志格式不支持，需为对象或数组")
    elif ext == ".txt":
        lines = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    lines.append({"raw_line": line})
        df = pd.DataFrame(lines)
    elif ext == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    else:
        raise ValueError(f"不支持的设备日志格式: {ext}")

    target_dir = os.path.join(project_dir, LOGS_DIR)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    dest = os.path.join(target_dir, f"{base_name}.csv")
    df.to_csv(dest, index=False, encoding="utf-8-sig")

    data_csv = os.path.join(project_dir, DATA_DIR, "device_logs.csv")
    if os.path.exists(data_csv):
        existing = pd.read_csv(data_csv, dtype=str)
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df
    combined.to_csv(data_csv, index=False, encoding="utf-8-sig")

    log_operation(project_dir, "import_device_log", f"导入设备日志 {file_path}，{len(df)} 条记录")
    return len(df)


def import_photos(project_dir, photo_dir, mapping_file=None):
    config = load_config(project_dir)
    if not os.path.isdir(photo_dir):
        raise NotADirectoryError(f"照片目录不存在: {photo_dir}")

    photo_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".heic"}
    target_dir = os.path.join(project_dir, PHOTOS_DIR)

    explicit_map = None
    if mapping_file:
        if not os.path.exists(mapping_file):
            raise FileNotFoundError(f"照片映射表不存在: {mapping_file}")
        explicit_map = pd.read_csv(mapping_file, dtype=str)
        required_cols = {"photo_file", "record_id"}
        if not required_cols.issubset(set(explicit_map.columns)):
            raise ValueError(f"映射表需包含 'photo_file' 和 'record_id' 两列，当前列: {list(explicit_map.columns)}")

    mapping = []
    count = 0

    if explicit_map is not None:
        for _, row in explicit_map.iterrows():
            photo_file = str(row["photo_file"]).strip()
            record_id = str(row["record_id"]).strip()
            src = os.path.join(photo_dir, photo_file)
            if not os.path.exists(src):
                for root, _dirs, files in os.walk(photo_dir):
                    for f in files:
                        if f == photo_file or f == os.path.basename(photo_file):
                            src = os.path.join(root, f)
                            break
                    else:
                        continue
                    break

            ext = os.path.splitext(photo_file)[1].lower()
            if ext not in photo_extensions:
                continue

            rel_path = photo_file
            dest = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(src):
                shutil.copy2(src, dest)
                mapping.append({"record_id": record_id, "photo_path": rel_path})
                count += 1
    else:
        for root, _dirs, files in os.walk(photo_dir):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in photo_extensions:
                    continue
                src = os.path.join(root, fname)
                rel_path = os.path.relpath(src, photo_dir)
                record_id = os.path.splitext(rel_path.replace(os.sep, "_"))[0]
                dest = os.path.join(target_dir, rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                mapping.append({"record_id": record_id, "photo_path": rel_path})
                count += 1

    mapping_data_file = os.path.join(project_dir, DATA_DIR, "photo_mapping.csv")
    new_map = pd.DataFrame(mapping) if mapping else pd.DataFrame(columns=["record_id", "photo_path"])

    if os.path.exists(mapping_data_file):
        existing_map = pd.read_csv(mapping_data_file, dtype=str)
        combined_map = pd.concat([existing_map, new_map], ignore_index=True)
    else:
        combined_map = new_map

    if not combined_map.empty:
        combined_map.to_csv(mapping_data_file, index=False, encoding="utf-8-sig")

    config["stats"]["total_photos"] = len(combined_map)
    save_config(project_dir, config)

    mode_desc = "映射表" if mapping_file else "文件名推断"
    log_operation(project_dir, "import_photos", f"导入照片目录 {photo_dir}，{count} 张照片（{mode_desc}）")
    return count
