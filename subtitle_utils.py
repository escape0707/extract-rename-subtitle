#!/usr/bin/env python

import itertools
import json
import re
import subprocess
from pathlib import Path
from re import Pattern
from typing import Any

EXTRACTION_CONFIG_FILENAME = "sub-extraction-config.json"
SIMPLE_EP_PATTERN = re.compile(r"\s(\d{2})\s")
SUB_CODEC_TO_SUFFIX_MAP = {"subrip": "srt", "ass": "ass"}


def print_ep_to_video_map(
    ep_to_video_map: dict[str, Path],
) -> None:
    print("Video Ep;\tVideo path:")
    print(*itertools.starmap("{};\t{}".format, ep_to_video_map.items()), sep="\n")


def get_paths_with_glob(glob: str, directory: Path = Path()) -> list[Path]:
    return sorted(directory.glob(glob))


def extract_ep_info(
    videos: list[Path],
    video_ep_pattern: Pattern[str] = SIMPLE_EP_PATTERN,
) -> dict[str, Path]:
    return {
        match[1]: video
        for video in videos
        if (match := video_ep_pattern.search(video.stem))
    }


def get_ep_to_video_map(
    video_glob: str = "*.mkv",
    video_ep_pattern: Pattern[str] = SIMPLE_EP_PATTERN,
    video_dir: Path = Path(),
) -> dict[str, Path]:
    videos = get_paths_with_glob(video_glob, video_dir)
    ep_to_video_map = extract_ep_info(videos, video_ep_pattern)
    return ep_to_video_map


def prompt_for_user_confirmation(request_text: str) -> bool:
    user_input = input(request_text + " [Y/n] ")
    return user_input.lower() in ("", "y")


def get_sub_streams_info(video: Path) -> Any:
    """Extract all subtitle info from the video with ffprobe."""
    cmd = (
        "ffprobe",
        "-loglevel",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        "s",
        video,
    )
    return json.loads(subprocess.run(cmd, capture_output=True).stdout)


def get_sub_stream_id_to_tag_map(
    video_sub_info: Any, track_id_indexed_within_subtitle_streams: bool = True
) -> dict[int, str]:
    """Detect all subtitle's track index and languages from the video sub info."""
    if track_id_indexed_within_subtitle_streams:
        return dict(
            enumerate(
                f'{sub_info["tags"]["language"]}-{sub_info["tags"]["title"]}'
                for sub_info in video_sub_info["streams"]
            )
        )
    # Track ID indexed within all streams.
    return {
        int(
            sub_info["index"]
        ): f'{sub_info["tags"]["language"]}-{sub_info["tags"]["title"]}'
        for sub_info in video_sub_info["streams"]
    }
