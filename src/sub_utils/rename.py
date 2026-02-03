from __future__ import annotations

from dataclasses import dataclass
import pathlib
import re
from typing import Iterable

from .utils import sorted_paths


@dataclass(frozen=True)
class RenameOp:
    source: pathlib.Path
    destination: pathlib.Path


@dataclass(frozen=True)
class RenamePlan:
    operations: list[RenameOp]
    skipped: list[str]


def build_video_by_episode(
    videos: Iterable[pathlib.Path], pattern: re.Pattern[str]
) -> tuple[dict[str, pathlib.Path], list[str]]:
    mapping: dict[str, pathlib.Path] = {}
    issues: list[str] = []
    for video in sorted_paths(videos):
        match = pattern.search(video.stem)
        if not match:
            issues.append(f"No episode match for video: {video.name}")
            continue
        episode = match.group(1)
        if episode in mapping:
            issues.append(
                f"Duplicate episode '{episode}' for videos: {mapping[episode].name}, {video.name}"
            )
            continue
        mapping[episode] = video
    return mapping, issues


def plan_rename(
    workdir: pathlib.Path,
    subtitle_glob: str,
    subtitle_pattern: re.Pattern[str],
    video_by_episode: dict[str, pathlib.Path],
    tag: str,
    overwrite: bool,
) -> RenamePlan:
    operations: list[RenameOp] = []
    skipped: list[str] = []
    for subtitle in sorted_paths(workdir.glob(subtitle_glob)):
        match = subtitle_pattern.search(subtitle.stem)
        if not match:
            skipped.append(f"No episode match for subtitle: {subtitle.name}")
            continue
        episode = match.group(1)
        video = video_by_episode.get(episode)
        if not video:
            skipped.append(f"No video match for subtitle: {subtitle.name}")
            continue
        if tag:
            new_suffix = f".{tag}{subtitle.suffix}"
        else:
            new_suffix = "".join(subtitle.suffixes) or subtitle.suffix
        destination = subtitle.with_name(f"{video.stem}{new_suffix}")
        if destination.exists() and not overwrite:
            skipped.append(f"Destination exists, skipping: {destination.name}")
            continue
        if subtitle.resolve() == destination.resolve():
            skipped.append(f"Already named correctly: {subtitle.name}")
            continue
        operations.append(RenameOp(source=subtitle, destination=destination))
    return RenamePlan(operations=operations, skipped=skipped)


def apply_rename(plan: RenamePlan) -> None:
    for op in plan.operations:
        op.source.rename(op.destination)
