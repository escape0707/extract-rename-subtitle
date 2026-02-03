from __future__ import annotations

from dataclasses import dataclass
import pathlib

from .utils import sorted_paths


@dataclass(frozen=True)
class FontOp:
    video: pathlib.Path
    cmd: tuple[str, ...]


@dataclass(frozen=True)
class FontPlan:
    operations: list[FontOp]
    output_dir: pathlib.Path
    skipped: list[str]


def plan_fonts(
    videos: list[pathlib.Path],
    output_dir: pathlib.Path,
    overwrite: bool,
) -> FontPlan:
    operations: list[FontOp] = []
    skipped: list[str] = []
    for video in sorted_paths(videos):
        cmd = (
            "ffmpeg",
            "-dump_attachment:t",
            "",
            "-y" if overwrite else "-n",
            "-i",
            str(video.resolve()),
        )
        operations.append(FontOp(video=video, cmd=cmd))
    if not operations:
        skipped.append("No videos matched for font extraction")
    return FontPlan(operations=operations, output_dir=output_dir, skipped=skipped)


def apply_fonts(plan: FontPlan) -> None:
    from .ffmpeg import run_ffmpeg

    plan.output_dir.mkdir(parents=True, exist_ok=True)
    for op in plan.operations:
        run_ffmpeg(op.cmd, cwd=plan.output_dir)
