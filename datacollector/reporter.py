import os
from datetime import datetime
import pandas as pd
from .project import load_config, DATA_DIR, ERRORS_DIR, REPORT_DIR, PHOTOS_DIR
from .logger import read_logs


def _load_data_safe(project_dir, data_type):
    data_file = os.path.join(project_dir, DATA_DIR, f"{data_type}.csv")
    if os.path.exists(data_file):
        return pd.read_csv(data_file, dtype=str)
    return pd.DataFrame()


def get_progress(project_dir, start_date=None, end_date=None):
    config = load_config(project_dir)
    df = _load_data_safe(project_dir, "questionnaires")

    stats = dict(config.get("stats", {}))

    if not df.empty:
        date_field = config.get("date_field", "date")
        if date_field in df.columns:
            df[date_field] = pd.to_datetime(df[date_field], errors="coerce")
            if start_date:
                start = pd.to_datetime(start_date)
                df = df[df[date_field] >= start]
            if end_date:
                end = pd.to_datetime(end_date)
                df = df[df[date_field] <= end]
            stats["filtered_records"] = len(df)

        region_field = config.get("region_field", "region")
        if region_field in df.columns:
            stats["region_counts"] = df[region_field].value_counts().to_dict()
    else:
        stats["filtered_records"] = 0

    photo_dir = os.path.join(project_dir, PHOTOS_DIR)
    if os.path.exists(photo_dir):
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
        count = 0
        for root, _dirs, files in os.walk(photo_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in exts:
                    count += 1
        stats["total_photos"] = count

    errors_dir = os.path.join(project_dir, ERRORS_DIR)
    error_count = 0
    if os.path.exists(errors_dir):
        for f in os.listdir(errors_dir):
            if f.endswith(".csv"):
                err_df = pd.read_csv(os.path.join(errors_dir, f))
                error_count += len(err_df)
    stats["error_count"] = error_count

    return stats


def generate_report(project_dir, start_date=None, end_date=None, output_file=None):
    config = load_config(project_dir)
    progress = get_progress(project_dir, start_date, end_date)
    logs = read_logs(project_dir)

    report_dir = os.path.join(project_dir, REPORT_DIR)
    os.makedirs(report_dir, exist_ok=True)

    lines = []
    lines.append("=" * 60)
    lines.append("数据采集交付报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"项目名称: {config.get('name', 'N/A')}")
    lines.append(f"创建时间: {config.get('created_at', 'N/A')}")
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if start_date:
        lines.append(f"筛选起始日期: {start_date}")
    if end_date:
        lines.append(f"筛选截止日期: {end_date}")
    lines.append("")

    lines.append("-" * 40)
    lines.append("采集进度统计")
    lines.append("-" * 40)
    lines.append(f"总记录数: {progress.get('total_records', 0)}")
    lines.append(f"筛选后记录数: {progress.get('filtered_records', 0)}")
    lines.append(f"总照片数: {progress.get('total_photos', 0)}")
    lines.append(f"已打标签记录数: {progress.get('tagged_count', 0)}")
    lines.append(f"已校验: {'是' if progress.get('checked') else '否'}")
    lines.append(f"校验错误数: {progress.get('error_count', 0)}")
    lines.append("")

    region_counts = progress.get("region_counts", {})
    if region_counts:
        lines.append("-" * 40)
        lines.append("分地区统计")
        lines.append("-" * 40)
        for region, count in sorted(region_counts.items()):
            lines.append(f"  {region}: {count} 条")
        lines.append("")

    sensitive = config.get("sensitive_fields", [])
    if sensitive:
        lines.append("-" * 40)
        lines.append("敏感字段（已配置脱敏）")
        lines.append("-" * 40)
        lines.append(f"  {', '.join(sensitive)}")
        lines.append("")

    lines.append("-" * 40)
    lines.append("操作日志摘要")
    lines.append("-" * 40)
    action_summary = {}
    for entry in logs:
        action = entry.get("action", "unknown")
        action_summary[action] = action_summary.get(action, 0) + 1
    for action, count in sorted(action_summary.items()):
        lines.append(f"  {action}: {count} 次")
    lines.append("")

    lines.append("=" * 60)
    lines.append("报告结束")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    if not output_file:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(report_dir, f"report_{ts}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    return output_file, report_text
