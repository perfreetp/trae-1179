import click
import os

from .project import init_project, load_config, view_config, set_config
from .importer import import_questionnaire, import_device_log, import_photos
from .checker import check_project, get_duplicate_records
from .tagger import tag_records, remove_tag
from .merger import merge_projects
from .sampler import extract_sample
from .exporter import export_data
from .reporter import get_progress, generate_report
from .reviewer import (
    init_review,
    update_review,
    get_review_summary,
    generate_review_list,
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_PASSED,
    REVIEW_STATUS_ISSUES,
)


@click.group()
@click.version_option(version="1.0.0", prog_name="dc")
def cli():
    """数据采集命令行工具 - 批量整理问卷、设备日志和现场照片"""
    pass


@cli.command()
@click.argument("project_dir", type=click.Path())
@click.option("--name", "-n", default=None, help="项目名称（默认取目录名）")
def init(project_dir, name):
    """创建采集项目"""
    try:
        config = init_project(project_dir, name)
        click.echo(f"✓ 项目已创建: {os.path.abspath(project_dir)}")
        click.echo(f"  名称: {config['name']}")
        click.echo(f"  时间: {config['created_at']}")
    except FileExistsError as e:
        click.echo(f"✗ 错误: {e}", err=True)


@cli.command("import")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--type", "data_type", type=click.Choice(["questionnaire", "device_log", "photos"]), required=True, help="导入类型")
@click.option("--file", "file_path", type=click.Path(exists=True), default=None, help="文件路径（问卷/日志）")
@click.option("--dir", "photo_dir", type=click.Path(exists=True), default=None, help="照片目录路径")
@click.option("--mapping", "mapping_file", type=click.Path(exists=True), default=None, help="照片映射表 CSV（含 photo_file, record_id 列）")
def import_data(project_dir, data_type, file_path, photo_dir, mapping_file):
    """导入问卷、设备日志或现场照片"""
    try:
        if data_type == "questionnaire":
            if not file_path:
                click.echo("✗ 问卷导入需要指定 --file 参数", err=True)
                return
            count = import_questionnaire(project_dir, file_path)
            click.echo(f"✓ 导入问卷完成: {count} 条记录")
        elif data_type == "device_log":
            if not file_path:
                click.echo("✗ 设备日志导入需要指定 --file 参数", err=True)
                return
            count = import_device_log(project_dir, file_path)
            click.echo(f"✓ 导入设备日志完成: {count} 条记录")
        elif data_type == "photos":
            if not photo_dir:
                click.echo("✗ 照片导入需要指定 --dir 参数", err=True)
                return
            count = import_photos(project_dir, photo_dir, mapping_file)
            mode = "（映射表模式）" if mapping_file else "（文件名推断模式）"
            click.echo(f"✓ 导入照片完成: {count} 张 {mode}")
    except Exception as e:
        click.echo(f"✗ 导入失败: {e}", err=True)


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--type", "data_type", default="questionnaires", help="数据类型 (默认: questionnaires)")
@click.option("--show-duplicates", is_flag=True, default=False, help="显示重复记录")
def check(project_dir, data_type, show_duplicates):
    """按字段校验缺项、检查重复记录"""
    try:
        errors = check_project(project_dir, data_type)

        if not errors:
            click.echo("✓ 校验通过，未发现缺项或重复")
        else:
            missing = [e for e in errors if e["type"] == "empty_value"]
            missing_fields = [e for e in errors if e["type"] == "missing_field"]
            dups = [e for e in errors if e["type"] == "duplicate"]

            click.echo(f"✗ 校验发现 {len(errors)} 个问题:")
            if missing_fields:
                fields = set(e["field"] for e in missing_fields)
                click.echo(f"  缺失字段: {', '.join(fields)}")
            if missing:
                field_counts = {}
                for e in missing:
                    f = e["field"]
                    field_counts[f] = field_counts.get(f, 0) + 1
                for f, c in field_counts.items():
                    click.echo(f"  字段 '{f}' 缺项: {c} 处")
            if dups:
                click.echo(f"  重复记录: {len(dups)} 条")

            error_file = os.path.join(project_dir, "errors", f"check_errors_{data_type}.csv")
            click.echo(f"  错误清单已保存: {error_file}")

        if show_duplicates:
            dup_df = get_duplicate_records(project_dir, data_type)
            if not dup_df.empty:
                click.echo("\n重复记录详情:")
                click.echo(dup_df.to_string(index=False))
    except Exception as e:
        click.echo(f"✗ 校验失败: {e}", err=True)


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--ids", required=True, help="记录ID列表，逗号分隔")
@click.option("--tag", "tag_name", required=True, help="标签名称")
@click.option("--type", "data_type", default="questionnaires", help="数据类型")
@click.option("--remove", is_flag=True, default=False, help="移除标签而非添加")
def tag(project_dir, ids, tag_name, data_type, remove):
    """给样本打标签或移除标签"""
    try:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]

        if remove:
            count = remove_tag(project_dir, id_list, tag_name, data_type)
            click.echo(f"✓ 从 {count} 条记录移除标签 '{tag_name}'")
        else:
            count = tag_records(project_dir, id_list, tag_name, data_type)
            click.echo(f"✓ 为 {count} 条记录打标签 '{tag_name}'")
    except Exception as e:
        click.echo(f"✗ 标签操作失败: {e}", err=True)


@cli.command()
@click.argument("target_project_dir", type=click.Path(exists=True))
@click.argument("source_dirs", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--type", "data_type", default="questionnaires", help="合并的数据类型")
def merge(target_project_dir, source_dirs, data_type):
    """合并多次采集结果"""
    try:
        total = merge_projects(target_project_dir, list(source_dirs), data_type)
        click.echo(f"✓ 合并完成，总计 {total} 条记录（已去重）")
    except Exception as e:
        click.echo(f"✗ 合并失败: {e}", err=True)


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--size", required=True, type=int, help="抽样数量")
@click.option("--method", type=click.Choice(["random", "stratified", "sequential"]), default="random", help="抽样方法")
@click.option("--type", "data_type", default="questionnaires", help="数据类型")
@click.option("--seed", default=42, type=int, help="随机种子")
def sample(project_dir, size, method, data_type, seed):
    """抽取复核样本"""
    try:
        sample_df, sample_ids, shortfall = extract_sample(project_dir, size, method, data_type, seed)

        init_review(project_dir, sample_ids, data_type)

        click.echo(f"✓ 抽样完成: {len(sample_df)} 条，方法: {method}")
        if shortfall > 0:
            click.echo(f"  ⚠ 记录总数不足，请求 {size} 条，实际只能抽到 {len(sample_df)} 条（差 {shortfall} 条）")
        if len(sample_ids) <= 20:
            click.echo(f"  样本ID: {', '.join(str(i) for i in sample_ids)}")
    except Exception as e:
        click.echo(f"✗ 抽样失败: {e}", err=True)


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["csv", "json", "xlsx"]), default="csv", help="导出格式")
@click.option("--type", "data_type", default="questionnaires", help="数据类型")
@click.option("--no-hide-sensitive", is_flag=True, default=False, help="不隐藏敏感字段")
@click.option("--no-link-photos", is_flag=True, default=False, help="不关联照片")
@click.option("--split-by-region", is_flag=True, default=False, help="按地区拆分数据")
@click.option("--region-field", default=None, help="地区字段名")
@click.option("--output", "output_dir", default=None, help="输出目录")
@click.option("--with-review", is_flag=True, default=False, help="导出时带上复核状态和结论")
def export(project_dir, fmt, data_type, no_hide_sensitive, no_link_photos, split_by_region, region_field, output_dir, with_review):
    """导出数据为通用格式"""
    try:
        out = export_data(
            project_dir,
            data_type=data_type,
            fmt=fmt,
            hide_sensitive=not no_hide_sensitive,
            link_photos=not no_link_photos,
            split_by_region=split_by_region,
            region_field=region_field,
            output_dir=output_dir,
            with_review=with_review,
        )
        click.echo(f"✓ 导出完成，输出目录: {os.path.abspath(out)}")
    except Exception as e:
        click.echo(f"✗ 导出失败: {e}", err=True)


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--start-date", default=None, help="筛选起始日期 (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="筛选截止日期 (YYYY-MM-DD)")
@click.option("--output", "output_file", default=None, help="报告输出文件路径")
@click.option("--progress-only", is_flag=True, default=False, help="仅显示进度统计")
def report(project_dir, start_date, end_date, output_file, progress_only):
    """统计采集进度、生成交付报告"""
    try:
        if progress_only:
            progress = get_progress(project_dir, start_date, end_date)
            click.echo("采集进度统计:")
            click.echo(f"  总记录数: {progress.get('total_records', 0)}")
            click.echo(f"  筛选后记录数: {progress.get('filtered_records', 0)}")
            click.echo(f"  总照片数: {progress.get('total_photos', 0)}")
            click.echo(f"  已打标签记录数: {progress.get('tagged_count', 0)}")
            click.echo(f"  已校验: {'是' if progress.get('checked') else '否'}")
            click.echo(f"  校验错误数: {progress.get('error_count', 0)}")

            review_total = progress.get("review_total", 0)
            if review_total > 0:
                click.echo(f"  复核统计:")
                click.echo(f"    待复核: {progress.get('review_pending', 0)} 条")
                click.echo(f"    已通过: {progress.get('review_passed', 0)} 条")
                click.echo(f"    有问题: {progress.get('review_issues', 0)} 条")

            region_counts = progress.get("region_counts", {})
            if region_counts:
                click.echo("  分地区统计:")
                for region, count in sorted(region_counts.items()):
                    click.echo(f"    {region}: {count} 条")
        else:
            path, text = generate_report(project_dir, start_date, end_date, output_file)
            click.echo(f"✓ 交付报告已生成: {os.path.abspath(path)}")
            click.echo("")
            click.echo(text)
    except Exception as e:
        click.echo(f"✗ 报告生成失败: {e}", err=True)


@cli.group()
def config():
    """查看或修改项目配置"""
    pass


@config.command("view")
@click.argument("project_dir", type=click.Path(exists=True))
def config_view(project_dir):
    """查看当前项目配置"""
    try:
        cfg = view_config(project_dir)
        click.echo("项目配置:")
        for key, value in cfg.items():
            if isinstance(value, list):
                click.echo(f"  {key}: {', '.join(str(v) for v in value)}")
            else:
                click.echo(f"  {key}: {value}")
    except Exception as e:
        click.echo(f"✗ 查看配置失败: {e}", err=True)


@config.command("set")
@click.argument("project_dir", type=click.Path(exists=True))
@click.argument("key")
@click.argument("value")
def config_set(project_dir, key, value):
    """修改项目配置项（列表类型用逗号分隔）"""
    try:
        parsed = set_config(project_dir, key, value)
        if isinstance(parsed, list):
            click.echo(f"✓ 配置 '{key}' 已更新为: {', '.join(str(v) for v in parsed)}")
        else:
            click.echo(f"✓ 配置 '{key}' 已更新为: {parsed}")
    except Exception as e:
        click.echo(f"✗ 配置修改失败: {e}", err=True)


@cli.command("review")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--id", "record_id", required=True, help="记录ID")
@click.option("--status", required=True, type=click.Choice(["待复核", "已通过", "有问题"]), help="复核状态")
@click.option("--conclusion", default="", help="复核结论")
@click.option("--type", "data_type", default="questionnaires", help="数据类型")
def review(project_dir, record_id, status, conclusion, data_type):
    """标记复核状态、录入复核结论"""
    try:
        update_review(project_dir, record_id, status, conclusion, data_type)
        click.echo(f"✓ 记录 {record_id} 复核状态: {status}")
        if conclusion:
            click.echo(f"  结论: {conclusion}")
    except Exception as e:
        click.echo(f"✗ 复核操作失败: {e}", err=True)


@cli.command("review-summary")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--type", "data_type", default="questionnaires", help="数据类型")
@click.option("--generate-list", is_flag=True, default=False, help="同时生成复核清单文件")
def review_summary(project_dir, data_type, generate_list):
    """查看复核摘要或生成复核清单"""
    try:
        summary = get_review_summary(project_dir, data_type)
        click.echo("复核统计:")
        click.echo(f"  待复核: {summary['pending']} 条")
        click.echo(f"  已通过: {summary['passed']} 条")
        click.echo(f"  有问题: {summary['issues']} 条")
        click.echo(f"  复核总计: {summary['total']} 条")

        if generate_list:
            path = generate_review_list(project_dir, data_type)
            click.echo(f"✓ 复核清单已生成: {os.path.abspath(path)}")
    except Exception as e:
        click.echo(f"✗ 复核摘要失败: {e}", err=True)


if __name__ == "__main__":
    cli()
