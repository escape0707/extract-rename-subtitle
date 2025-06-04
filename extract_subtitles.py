#!/usr/bin/env python

import pathlib
import re
import shlex
import subprocess
from typing import Any, Optional, TypedDict

from subtitle_utils import (
    extract_sub_lang_by_track_collection_with_video_sub_info,
    get_video_by_ep_collection_with_glob_and_pattern,
    get_video_collection_with_glob,
    get_video_sub_info,
    prompt_for_user_confirmation,
    simple_ep_pattern,
)


class ExtractionMetadata(TypedDict, total=False):
    origin_video_glob: str  # Mandatory. Used to collect videos to extract subtitles from.
    sub_lang_by_track_collection: dict[
        int, str
    ]  # Currently mandatory. Specified stream track should contain extractable subtitle stream. The string value (of the dict) will be used as extracted subtitle's language tag.
    target_video_glob: str  # Optional. If supplied, extracted subtitles will be renamed after another series of videos. If not supplied, origin_video_ep_pattern and target_video_ep_pattern will be ignored and extracted subtitles will be renamed after the original videos.
    origin_video_ep_pattern: str  # Optional. Only used when targeting another series of videos to identify the episode info from the original video. (Default: simple_ep_pattern)
    target_video_ep_pattern: str  # Optional. Only used when targeting another series of videos to identify the episode info from the targeting video. (Default: simple_ep_pattern)


def extract_subtitles(
    origin_video_collection: tuple[pathlib.Path, ...],
    sub_lang_by_track_collection: Optional[dict[int, str]] = None,
    target_video_by_ep_collection: Optional[dict[str, pathlib.Path]] = None,
    origin_video_ep_pattern: re.Pattern[str] = simple_ep_pattern,
) -> None:
    """
    1. We first extract all the subtitle tracks from the origin video.
    2. We then use the sub_lang_by_track_collection to map each sub_track to a subtitle language,
    which we can use to name the subtitle file.
    3. We then use the origin_video_collection to generate the command for each sub_track,
    and then use shlex.join to join the cmd tuple to a string, then print it to the terminal.
    """

    def _get_target_video() -> pathlib.Path:
        if target_video_by_ep_collection:
            m = origin_video_ep_pattern.search(origin_video.stem)
            if m:
                return target_video_by_ep_collection[m[1]]
        return origin_video

    def _get_sub_format() -> str:
        codec_name = video_sub_info["streams"][sub_index]["codec_name"]
        return {"subrip": "srt", "ass": "ass"}[codec_name]

    pending_subtitle_extraction: list[tuple[str, ...]] = []
    for origin_video in origin_video_collection:
        video_sub_info = get_video_sub_info(origin_video)
        if sub_lang_by_track_collection is None:
            sub_lang_by_track_collection = (
                extract_sub_lang_by_track_collection_with_video_sub_info(video_sub_info)
            )
        for sub_index, sub_lang in sub_lang_by_track_collection.items():
            sub_path = _get_target_video().with_suffix(
                f".{sub_lang}.{_get_sub_format()}"
            )
            cmd = (
                "ffmpeg",
                "-loglevel",
                "warning",
                "-i",  # input
                str(
                    origin_video
                ),  # shlex.join only accept str, or we can use pathlike object directly here.
                "-n",  # do not overwrite
                "-codec",
                "copy",
                "-map",
                f"0:s:{sub_index}",  # copy this sub_track from the input file
                str(sub_path),
            )
            print(shlex.join(cmd))
            pending_subtitle_extraction.append(cmd)
    if prompt_for_user_confirmation("Start subtitle extraction?"):
        for cmd in pending_subtitle_extraction:
            subprocess.run(cmd)


def extract_fonts(
    video_collection: tuple[pathlib.Path, ...], font_dir: Optional[pathlib.Path] = None
) -> None:
    if not video_collection:
        return
    pending_font_extraction: list[tuple[str, ...]] = []
    for video in video_collection:
        if font_dir is None:
            font_dir = video.with_name("fonts")
        # When extracting we will run ffmpeg under another working directory to put all attachments into it.
        #  So we have to resolve the absolute path now.
        cmd = (
            "ffmpeg",
            "-dump_attachment:t",  # dump all attachments
            "",  # with name guessed from attachments' filename field
            "-n",  # do not overwrite
            "-i",  # input file url follows
            str(video.resolve()),
        )
        print(shlex.join(cmd))
        pending_font_extraction.append(cmd)
    assert isinstance(font_dir, pathlib.Path)
    if prompt_for_user_confirmation(f'Extract font to folder "{font_dir}?"'):
        if not font_dir.is_dir():
            font_dir.mkdir(
                755, True, True
            )  # This might raise a FileExistsError by design.
            # User should then take care of the existing file and re-run the script.
        for cmd in pending_font_extraction:
            subprocess.run(cmd, cwd=font_dir)


if __name__ == "__main__":
    # Read command line argument(s)
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract softsubs from a series of videos."
        ' Look at the globs / patterns / track information etc in a file named "sub-utils.json" to determine from which videos to extract and to what subtitle file name to write.'
        " Patterns are used to extract episode info from input videos and optionally match output subtitles to output videos names."
        " A template JSON file will be created in the working_directory if not exist and opened for editing.",
    )
    parser.add_argument(
        "video_directory",
        nargs="?",
        default=pathlib.Path(),
        type=pathlib.Path,
        help='The directory containing source videos and "sub-utils.json", also the place to put extracted subtitles. (Default: current working directory)',
    )
    cli_args = parser.parse_args()

    # Read metadata
    metadata: ExtractionMetadata = {
        "origin_video_glob": "*.mkv",
        "sub_lang_by_track_collection": {0: "eng", 1: "enm"},
        # "target_video_glob": "*.mp4",
        # "origin_video_ep_pattern": r".*\s(\d{2})\s.*",
        # "target_video_ep_pattern": r".*\s(\d{2})\s.*",
    }

    # Process
    extraction_args: dict[str, Any] = {}
    try:
        origin_video_collection = get_video_collection_with_glob(
            metadata["origin_video_glob"], cli_args.video_directory
        )
        extraction_args["origin_video_collection"] = origin_video_collection
        extraction_args["sub_lang_by_track_collection"] = metadata[
            "sub_lang_by_track_collection"
        ]
    except KeyError:
        raise  # Explicitly catch and re-raise KeyError to comfort type checkers.
    if "target_video_glob" in metadata:
        target_video_ep_pattern = (
            re.compile(metadata["target_video_ep_pattern"])
            if "target_video_ep_pattern" in metadata
            else simple_ep_pattern
        )
        extraction_args[
            "target_video_by_ep_collection"
        ] = get_video_by_ep_collection_with_glob_and_pattern(
            metadata["target_video_glob"],
            target_video_ep_pattern,
            cli_args.video_directory,
        )
        origin_video_ep_pattern = (
            re.compile(metadata["origin_video_ep_pattern"])
            if "origin_video_ep_pattern" in metadata
            else simple_ep_pattern
        )
        extraction_args["origin_video_ep_pattern"] = origin_video_ep_pattern
    extract_subtitles(**extraction_args)
    extract_fonts(origin_video_collection)
