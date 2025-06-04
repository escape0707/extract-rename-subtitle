#!/usr/bin/env python

import itertools
import json
import pathlib
import re
import subprocess
from typing import Any, List

simple_ep_pattern = re.compile(r"\s(\d{2})\s")
config_filename = "sub-utils.json"


def print_ep_to_video_map(
    ep_to_video_map: dict[str, pathlib.Path],
) -> None:
    print("Video Ep;\tVideo path:")
    print(*itertools.starmap("{};\t{}".format, ep_to_video_map.items()), sep="\n")


def get_paths_with_glob(
    glob: str, directory: pathlib.Path = pathlib.Path()
) -> List[pathlib.Path]:
    return sorted(directory.glob(glob))


def extract_ep_info(
    videos: List[pathlib.Path],
    video_ep_pattern: re.Pattern[str] = simple_ep_pattern,
) -> dict[str, pathlib.Path]:
    return {
        match[1]: video
        for video in videos
        if (match := video_ep_pattern.search(video.stem))
    }


def get_ep_to_video_map(
    video_glob: str = "*.mkv",
    video_ep_pattern: re.Pattern[str] = simple_ep_pattern,
    video_dir: pathlib.Path = pathlib.Path(),
) -> dict[str, pathlib.Path]:
    videos = get_paths_with_glob(video_glob, video_dir)
    ep_to_video_map = extract_ep_info(videos, video_ep_pattern)
    return ep_to_video_map


def prompt_for_user_confirmation(request_text: str) -> bool:
    user_input = input(request_text + " [Y/n] ")
    return user_input.lower() in ("", "y")


def get_video_sub_info(video: pathlib.Path) -> Any:
    """extract all subtitle info from the video with ffprobe"""
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


def extract_sub_lang_by_track_collection_with_video_sub_info(
    video_sub_info: Any,
) -> dict[int, str]:
    """detect all subtitle's track index and languages from the video sub info"""
    return dict(
        enumerate(
            f'{sub_info["tags"]["language"]}-{sub_info["tags"]["title"]}'
            for sub_info in video_sub_info["streams"]
        )
    )
