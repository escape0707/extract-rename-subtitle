from __future__ import annotations

from dataclasses import dataclass
import pathlib
import re
from typing import Any

from .ffmpeg import run_ffprobe
from .utils import sorted_paths

SUB_FORMAT_BY_CODEC = {
    "subrip": "srt",
    "ass": "ass",
    "ssa": "ssa",
    "webvtt": "vtt",
}


@dataclass(frozen=True)
class ExtractOp:
    origin_video: pathlib.Path
    target_subtitle: pathlib.Path
    sub_index: int
    language_tag: str
    codec: str
    cmd: tuple[str, ...]


@dataclass(frozen=True)
class ExtractPlan:
    operations: list[ExtractOp]
    skipped: list[str]


def infer_sub_lang_by_track(video_sub_info: dict[str, Any]) -> dict[int, str]:
    streams = video_sub_info.get("streams", [])
    mapping: dict[int, str] = {}
    for index, stream in enumerate(streams):
        tags = stream.get("tags", {}) if isinstance(stream, dict) else {}
        language = tags.get("language") or "und"
        title = tags.get("title")
        label = f"{language}-{title}" if title else language
        mapping[index] = label
    return mapping


def plan_extract(
    origin_videos: list[pathlib.Path],
    sub_lang_by_track: dict[int, str] | None,
    target_video_by_episode: dict[str, pathlib.Path] | None,
    origin_episode_pattern: re.Pattern[str],
    overwrite: bool,
) -> ExtractPlan:
    operations: list[ExtractOp] = []
    skipped: list[str] = []
    for origin_video in sorted_paths(origin_videos):
        video_sub_info = run_ffprobe(origin_video)
        streams = video_sub_info.get("streams", [])
        mapping = sub_lang_by_track or infer_sub_lang_by_track(video_sub_info)
        target_video = origin_video
        if target_video_by_episode is not None:
            match = origin_episode_pattern.search(origin_video.stem)
            if not match:
                skipped.append(f"No episode match for origin video: {origin_video.name}")
                continue
            episode = match.group(1)
            target_video = target_video_by_episode.get(episode)
            if not target_video:
                skipped.append(
                    f"No target video match for episode {episode}: {origin_video.name}"
                )
                continue
        for sub_index, language_tag in mapping.items():
            if sub_index >= len(streams):
                skipped.append(
                    f"Subtitle track {sub_index} not found in {origin_video.name}"
                )
                continue
            stream = streams[sub_index]
            codec = stream.get("codec_name") if isinstance(stream, dict) else None
            codec_name = codec or "sub"
            ext = SUB_FORMAT_BY_CODEC.get(codec_name, codec_name)
            target_subtitle = target_video.with_suffix(f".{language_tag}.{ext}")
            cmd = (
                "ffmpeg",
                "-loglevel",
                "warning",
                "-i",
                str(origin_video),
                "-y" if overwrite else "-n",
                "-codec",
                "copy",
                "-map",
                f"0:s:{sub_index}",
                str(target_subtitle),
            )
            operations.append(
                ExtractOp(
                    origin_video=origin_video,
                    target_subtitle=target_subtitle,
                    sub_index=sub_index,
                    language_tag=language_tag,
                    codec=codec_name,
                    cmd=cmd,
                )
            )
    return ExtractPlan(operations=operations, skipped=skipped)


def apply_extract(plan: ExtractPlan) -> None:
    from .ffmpeg import run_ffmpeg

    for op in plan.operations:
        run_ffmpeg(op.cmd)
