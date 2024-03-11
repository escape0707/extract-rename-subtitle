#!/usr/bin/env python

import itertools
import json
import pathlib
import re
import subprocess
from typing import Any

simple_ep_pattern = re.compile(r"\s(\d{2})\s")
metadata_filename = "sub-utils.json"


def print_video_by_ep_collection(
    video_by_ep_collection: dict[str, pathlib.Path]
) -> None:
    print("Video Ep;\tVideo path:")
    print(
        *itertools.starmap("{};\t{}".format, video_by_ep_collection.items()), sep="\n"
    )


def get_video_collection_with_glob(
    video_glob: str, video_dir: pathlib.Path = pathlib.Path()
) -> tuple[pathlib.Path, ...]:
    return tuple(video_dir.glob(video_glob))


def generate_video_by_ep_collection_with_pattern(
    video_collection: tuple[pathlib.Path, ...],
    video_ep_pattern: re.Pattern[str] = simple_ep_pattern,
) -> dict[str, pathlib.Path]:
    video_by_ep_collection: dict[str, pathlib.Path] = {}
    for video in video_collection:
        m = video_ep_pattern.search(video.stem)
        if m:
            video_by_ep_collection[m[1]] = video
    return video_by_ep_collection


def get_video_by_ep_collection_with_glob_and_pattern(
    video_glob: str = "*.mkv",
    video_ep_pattern: re.Pattern[str] = simple_ep_pattern,
    video_dir: pathlib.Path = pathlib.Path(),
) -> dict[str, pathlib.Path]:
    video_collection = get_video_collection_with_glob(video_glob, video_dir)
    return generate_video_by_ep_collection_with_pattern(
        video_collection, video_ep_pattern
    )


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
