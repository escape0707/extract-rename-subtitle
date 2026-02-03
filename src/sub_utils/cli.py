from __future__ import annotations

import argparse
import pathlib
import sys

from .config import CONFIG_FILENAME, ConfigError, config_template, load_config
from .extract import apply_extract, plan_extract
from .ffmpeg import FfmpegError, format_cmd, run_ffprobe
from .fonts import apply_fonts, plan_fonts
from .rename import apply_rename, build_video_by_episode, plan_rename, RenamePlan
from .utils import prompt_yes_no, sorted_paths


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    workdir = pathlib.Path(args.dir).resolve()
    config_path = _resolve_config_path(args.config, workdir)

    if args.command == "init":
        _cmd_init(config_path, force=args.force)
        return

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        if args.command == "probe":
            _cmd_probe(args, config, workdir)
        elif args.command == "extract":
            _cmd_extract(args, config, workdir)
        elif args.command == "rename":
            _cmd_rename(args, config, workdir)
        elif args.command == "fonts":
            _cmd_fonts(args, config, workdir)
    except FfmpegError as exc:
        print(f"ffmpeg error: {exc}", file=sys.stderr)
        sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sub-utils",
        description="Utilities to extract and rename subtitle files.",
    )
    parser.add_argument(
        "--config",
        default=CONFIG_FILENAME,
        help=f"Config file name or path (default: {CONFIG_FILENAME})",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Working directory containing videos and subtitle files",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a config template")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing")

    probe_parser = subparsers.add_parser(
        "probe", help="Show subtitle streams detected by ffprobe"
    )
    probe_parser.add_argument(
        "--video",
        action="append",
        help="Specific video file(s) to probe (repeatable)",
    )

    extract_parser = subparsers.add_parser(
        "extract", help="Extract subtitle streams from videos"
    )
    _add_apply_flags(extract_parser)

    rename_parser = subparsers.add_parser(
        "rename", help="Rename subtitles to match video names"
    )
    _add_apply_flags(rename_parser)

    fonts_parser = subparsers.add_parser(
        "fonts", help="Extract embedded fonts from videos"
    )
    _add_apply_flags(fonts_parser)

    return parser


def _add_apply_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Plan only")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files"
    )


def _resolve_config_path(config_arg: str, workdir: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(config_arg)
    if not path.is_absolute():
        path = workdir / path
    return path


def _cmd_init(config_path: pathlib.Path, force: bool) -> None:
    if config_path.exists() and not force:
        print(f"Config already exists: {config_path}")
        print("Use --force to overwrite.")
        return
    config_path.write_text(config_template(), encoding="utf-8")
    print(f"Created config template at {config_path}")


def _cmd_probe(args: argparse.Namespace, config, workdir: pathlib.Path) -> None:
    if args.video:
        videos = [workdir / pathlib.Path(v) for v in args.video]
    else:
        videos = sorted_paths(workdir.glob(config.extract.origin_video_glob))
    if not videos:
        print("No videos found to probe.")
        return
    for video in videos:
        if not video.exists():
            print(f"Missing video: {video}")
            continue
        print(f"{video.name}:")
        info = run_ffprobe(video)
        streams = info.get("streams", [])
        if not streams:
            print("  No subtitle streams found.")
            continue
        for index, stream in enumerate(streams):
            codec = stream.get("codec_name", "unknown") if isinstance(stream, dict) else "unknown"
            tags = stream.get("tags", {}) if isinstance(stream, dict) else {}
            language = tags.get("language", "und")
            title = tags.get("title", "")
            extra = f", title={title}" if title else ""
            print(f"  {index}: codec={codec}, lang={language}{extra}")


def _cmd_extract(args: argparse.Namespace, config, workdir: pathlib.Path) -> None:
    origin_videos = sorted_paths(workdir.glob(config.extract.origin_video_glob))
    if not origin_videos:
        print("No origin videos matched.")
        return

    target_video_by_episode = None
    if config.extract.target_video_glob:
        target_videos = sorted_paths(workdir.glob(config.extract.target_video_glob))
        target_video_by_episode, issues = build_video_by_episode(
            target_videos, config.extract.target_video_ep_pattern
        )
        for issue in issues:
            print(f"Note: {issue}")

    plan = plan_extract(
        origin_videos=origin_videos,
        sub_lang_by_track=config.extract.sub_lang_by_track,
        target_video_by_episode=target_video_by_episode,
        origin_episode_pattern=config.extract.origin_video_ep_pattern,
        overwrite=args.overwrite,
    )
    _print_extract_plan(plan)
    if plan.skipped:
        _print_skipped(plan.skipped)
    if _should_apply(plan.operations, args) and (
        args.yes or prompt_yes_no("Start subtitle extraction?")
    ):
        apply_extract(plan)


def _cmd_rename(args: argparse.Namespace, config, workdir: pathlib.Path) -> None:
    video_paths = sorted_paths(workdir.glob(config.rename.video_glob))
    video_by_episode, issues = build_video_by_episode(
        video_paths, config.rename.video_ep_pattern
    )
    for issue in issues:
        print(f"Note: {issue}")

    combined_ops: list = []
    skipped: list[str] = []
    for subtitle_glob, tag in sorted(config.rename.subtitle_tag_by_glob.items()):
        plan = plan_rename(
            workdir=workdir,
            subtitle_glob=subtitle_glob,
            subtitle_pattern=config.rename.subtitle_ep_pattern,
            video_by_episode=video_by_episode,
            tag=tag,
            overwrite=args.overwrite,
        )
        combined_ops.extend(plan.operations)
        skipped.extend(plan.skipped)

    combined_plan = RenamePlan(operations=combined_ops, skipped=skipped)
    _print_rename_plan(combined_plan)
    if combined_plan.skipped:
        _print_skipped(combined_plan.skipped)
    if _should_apply(combined_plan.operations, args) and (
        args.yes or prompt_yes_no("Apply renaming?")
    ):
        apply_rename(combined_plan)


def _cmd_fonts(args: argparse.Namespace, config, workdir: pathlib.Path) -> None:
    video_paths = sorted_paths(workdir.glob(config.fonts.video_glob))
    output_dir = pathlib.Path(config.fonts.output_dir)
    if not output_dir.is_absolute():
        output_dir = workdir / output_dir
    plan = plan_fonts(video_paths, output_dir, overwrite=args.overwrite)
    _print_font_plan(plan)
    if plan.skipped:
        _print_skipped(plan.skipped)
    if _should_apply(plan.operations, args) and (
        args.yes or prompt_yes_no("Extract fonts?")
    ):
        apply_fonts(plan)


def _should_apply(operations, args: argparse.Namespace) -> bool:
    if args.dry_run:
        print("Dry-run mode: no changes will be applied.")
        return False
    if not operations:
        print("Nothing to do.")
        return False
    return True


def _print_rename_plan(plan: RenamePlan) -> None:
    print(f"Planned renames: {len(plan.operations)}")
    for op in plan.operations:
        print(f"  {op.source.name} -> {op.destination.name}")


def _print_extract_plan(plan) -> None:
    print(f"Planned subtitle extractions: {len(plan.operations)}")
    for op in plan.operations:
        print(
            f"  {op.origin_video.name} -> {op.target_subtitle.name} "
            f"(track {op.sub_index}, lang={op.language_tag}, codec={op.codec})"
        )
        print(f"    {format_cmd(op.cmd)}")


def _print_font_plan(plan) -> None:
    print(f"Planned font extractions: {len(plan.operations)}")
    print(f"Output directory: {plan.output_dir}")
    for op in plan.operations:
        print(f"  {op.video.name}")


def _print_skipped(skipped: list[str]) -> None:
    print("Skipped:")
    for item in skipped:
        print(f"  {item}")
