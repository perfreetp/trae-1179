import os
import pandas as pd
from .project import load_config, DATA_DIR, SAMPLES_DIR
from .logger import log_operation

REVIEW_STATUS_PENDING = "待复核"
REVIEW_STATUS_PASSED = "已通过"
REVIEW_STATUS_ISSUES = "有问题"


def _review_file(project_dir, data_type="questionnaires"):
    return os.path.join(project_dir, DATA_DIR, f"review_{data_type}.csv")


def init_review(project_dir, sample_ids, data_type="questionnaires"):
    review_file = _review_file(project_dir, data_type)
    dup_keys_conf = load_config(project_dir).get("duplicate_key_fields", ["id"])
    key_field = dup_keys_conf[0] if dup_keys_conf else "id"

    records = []
    for sid in sample_ids:
        records.append({
            key_field: str(sid),
            "_review_status": REVIEW_STATUS_PENDING,
            "_review_conclusion": "",
        })

    new_df = pd.DataFrame(records)

    if os.path.exists(review_file):
        existing = pd.read_csv(review_file, dtype=str)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=[key_field], keep="last")
    else:
        combined = new_df

    combined.to_csv(review_file, index=False, encoding="utf-8-sig")
    log_operation(project_dir, "review_init", f"初始化复核清单 {len(sample_ids)} 条")
    return len(sample_ids)


def update_review(project_dir, record_id, status, conclusion="", data_type="questionnaires"):
    if status not in (REVIEW_STATUS_PENDING, REVIEW_STATUS_PASSED, REVIEW_STATUS_ISSUES):
        raise ValueError(f"无效复核状态: '{status}'，可选: {REVIEW_STATUS_PENDING}, {REVIEW_STATUS_PASSED}, {REVIEW_STATUS_ISSUES}")

    review_file = _review_file(project_dir, data_type)
    if not os.path.exists(review_file):
        raise FileNotFoundError(f"复核清单不存在，请先执行 sample 命令")

    dup_keys_conf = load_config(project_dir).get("duplicate_key_fields", ["id"])
    key_field = dup_keys_conf[0] if dup_keys_conf else "id"

    df = pd.read_csv(review_file, dtype=str)
    mask = df[key_field].astype(str) == str(record_id)

    if not mask.any():
        raise ValueError(f"复核清单中未找到记录 '{record_id}'")

    df.loc[mask, "_review_status"] = status
    if conclusion:
        df.loc[mask, "_review_conclusion"] = conclusion

    df.to_csv(review_file, index=False, encoding="utf-8-sig")
    log_operation(project_dir, "review_update", f"记录 {record_id} 状态: {status}，结论: {conclusion}")
    return True


def get_review_summary(project_dir, data_type="questionnaires"):
    review_file = _review_file(project_dir, data_type)
    if not os.path.exists(review_file):
        return {"pending": 0, "passed": 0, "issues": 0, "total": 0}

    df = pd.read_csv(review_file, dtype=str)
    status_col = "_review_status" if "_review_status" in df.columns else None
    if status_col is None:
        return {"pending": 0, "passed": 0, "issues": 0, "total": len(df)}

    counts = df[status_col].value_counts().to_dict()
    return {
        "pending": counts.get(REVIEW_STATUS_PENDING, 0),
        "passed": counts.get(REVIEW_STATUS_PASSED, 0),
        "issues": counts.get(REVIEW_STATUS_ISSUES, 0),
        "total": len(df),
    }


def generate_review_list(project_dir, data_type="questionnaires", output_file=None):
    review_file = _review_file(project_dir, data_type)
    if not os.path.exists(review_file):
        raise FileNotFoundError(f"复核清单不存在")

    df = pd.read_csv(review_file, dtype=str)

    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")
    if os.path.exists(data_file):
        main_df = pd.read_csv(data_file, dtype=str)
        dup_keys_conf = load_config(project_dir).get("duplicate_key_fields", ["id"])
        key_field = dup_keys_conf[0] if dup_keys_conf else "id"
        if key_field in main_df.columns and key_field in df.columns:
            merged = df.merge(main_df, on=key_field, how="left", suffixes=("", "_main"))
            df = merged

    if output_file is None:
        output_file = os.path.join(project_dir, SAMPLES_DIR, f"review_list_{data_type}.csv")

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    log_operation(project_dir, "review_list", f"生成复核清单 {len(df)} 条")
    return output_file
