import os
import json
import pandas as pd
from .project import load_config, DATA_DIR, PHOTOS_DIR, EXPORT_DIR
from .logger import log_operation


def _load_data(project_dir, data_type):
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"数据文件不存在: {data_file}")
    return pd.read_csv(data_file, dtype=str)


def _hide_sensitive(df, sensitive_fields):
    for field in sensitive_fields:
        if field in df.columns:
            df[field] = "***"
    return df


def _link_photos(df, project_dir, photo_id_field):
    mapping_file = os.path.join(project_dir, DATA_DIR, "photo_mapping.csv")
    if not os.path.exists(mapping_file):
        df["_photos"] = ""
        return df

    photo_map = pd.read_csv(mapping_file, dtype=str)
    photo_map = photo_map.rename(columns={"record_id": photo_id_field})
    photo_map = photo_map.groupby(photo_id_field)["photo_path"].apply(
        lambda x: ";".join(x.astype(str))
    ).reset_index()
    photo_map = photo_map.rename(columns={"photo_path": "_photos"})

    if photo_id_field in df.columns:
        df = df.merge(photo_map, on=photo_id_field, how="left")
    else:
        df["_photos"] = ""
    df["_photos"] = df["_photos"].fillna("")
    return df


def export_data(
    project_dir,
    data_type="questionnaires",
    fmt="csv",
    hide_sensitive=True,
    link_photos=True,
    split_by_region=False,
    region_field=None,
    output_dir=None,
):
    config = load_config(project_dir)
    df = _load_data(project_dir, data_type)

    if hide_sensitive:
        sensitive = config.get("sensitive_fields", [])
        df = _hide_sensitive(df, sensitive)

    if link_photos:
        photo_id = config.get("photo_id_field", "id")
        df = _link_photos(df, project_dir, photo_id)

    out_dir = output_dir or os.path.join(project_dir, EXPORT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    if split_by_region:
        region = region_field or config.get("region_field", "region")
        if region not in df.columns:
            raise ValueError(f"地区字段 '{region}' 不存在，无法按地区拆分")
        for region_val, group in df.groupby(region):
            safe_name = str(region_val).replace(" ", "_").replace("/", "_")
            _write_data(group, out_dir, f"{data_type}_{safe_name}", fmt)
        log_operation(
            project_dir,
            "export",
            f"按地区拆分导出 {data_type}，格式: {fmt}，地区数: {df[region].nunique()}",
        )
    else:
        _write_data(df, out_dir, data_type, fmt)
        log_operation(
            project_dir,
            "export",
            f"导出 {data_type}，格式: {fmt}，记录数: {len(df)}",
        )

    return out_dir


def _write_data(df, out_dir, name, fmt):
    if fmt == "csv":
        path = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt == "json":
        path = os.path.join(out_dir, f"{name}.json")
        df.to_json(path, orient="records", force_ascii=False, indent=2)
    elif fmt == "xlsx":
        path = os.path.join(out_dir, f"{name}.xlsx")
        df.to_excel(path, index=False)
    else:
        raise ValueError(f"不支持的导出格式: {fmt}")
    return path
