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
    total = len(df)

    if sample_size >= total:
        sample_df = df.copy()
        shortfall = sample_size - total
    elif method == "random":
        sample_df = df.sample(n=sample_size, random_state=seed)
        shortfall = 0
    elif method == "stratified":
        region_field = config.get("region_field", "region")
        if region_field not in df.columns:
            raise ValueError(f"分区字段 '{region_field}' 不存在，无法分层抽样")

        n_regions = df[region_field].nunique()
        base_per = sample_size // n_regions
        remainder = sample_size % n_regions

        parts = []
        region_groups = list(df.groupby(region_field))
        sorted_groups = sorted(region_groups, key=lambda x: len(x[1]), reverse=True)

        for idx, (region_val, group) in enumerate(sorted_groups):
            n_take = base_per + (1 if idx < remainder else 0)
            n_take = min(n_take, len(group))
            parts.append(group.sample(n=n_take, random_state=seed))

        sample_df = pd.concat(parts, ignore_index=True)

        if len(sample_df) < sample_size:
            sampled_ids = set()
            dup_keys = config.get("duplicate_key_fields", ["id"])
            key_field = dup_keys[0] if dup_keys else "id"
            if key_field in sample_df.columns:
                sampled_ids = set(sample_df[key_field].astype(str))

            remaining = df[~df[key_field].astype(str).isin(sampled_ids)] if key_field in df.columns else pd.DataFrame()
            if not remaining.empty:
                need = sample_size - len(sample_df)
                extra = remaining.sample(n=min(need, len(remaining)), random_state=seed)
                sample_df = pd.concat([sample_df, extra], ignore_index=True)

        shortfall = sample_size - len(sample_df)
    elif method == "sequential":
        sample_df = df.head(sample_size)
        shortfall = sample_size - len(sample_df)
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
    return sample_df, sample_ids, shortfall
