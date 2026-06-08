import os
import pandas as pd
from .project import load_config, DATA_DIR, SAMPLES_DIR
from .logger import log_operation


def extract_sample(project_dir, sample_size, method="random", data_type="questionnaires", seed=42):
    config = load_config(project_dir)
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")

    if not os.path.exists(data_file):
        raise FileNotFoundError(f"数据文件不存在: {data_file}")

    df = pd.read_csv(data_file, dtype=str)

    if sample_size >= len(df):
        sample_df = df.copy()
    elif method == "random":
        sample_df = df.sample(n=sample_size, random_state=seed)
    elif method == "stratified":
        region_field = config.get("region_field", "region")
        if region_field not in df.columns:
            raise ValueError(f"分区字段 '{region_field}' 不存在，无法分层抽样")
        n_per = max(1, sample_size // df[region_field].nunique())
        parts = []
        for _, group in df.groupby(region_field):
            parts.append(group.sample(n=min(n_per, len(group)), random_state=seed))
        sample_df = pd.concat(parts, ignore_index=True)
        if len(sample_df) > sample_size:
            sample_df = sample_df.head(sample_size)
    elif method == "sequential":
        sample_df = df.head(sample_size)
    else:
        raise ValueError(f"不支持的抽样方法: {method}")

    dup_keys = config.get("duplicate_key_fields", ["id"])
    key_field = dup_keys[0] if dup_keys else "id"

    if key_field in sample_df.columns:
        sample_ids = sample_df[key_field].tolist()
    else:
        sample_ids = list(range(len(sample_df)))

    sample_file = os.path.join(project_dir, SAMPLES_DIR, f"sample_{data_type}.csv")
    sample_df.to_csv(sample_file, index=False, encoding="utf-8-sig")

    log_operation(
        project_dir,
        "sample",
        f"抽取 {len(sample_df)} 条复核样本，方法: {method}",
    )
    return sample_df, sample_ids
