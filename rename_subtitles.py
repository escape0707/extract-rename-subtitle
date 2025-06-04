#!/usr/bin/env python

import json
import pathlib
import re
from typing import Dict, List, Pattern, Tuple, TypedDict

from subtitle_utils import (
    get_video_by_ep_collection_with_glob_and_pattern,
    print_video_by_ep_collection,
    prompt_for_user_confirmation,
    simple_ep_pattern,
    metadata_filename,
)


class RenamingMetadata(TypedDict):
    subtitle_tag_by_glob_collection: Dict[
        str, str
    ]  # Optional. Used to collect subtitles to rename and given them a tag in the resulting name.Can be used to identify language or subtitle group. (Default: {"*.ass": "", "*.srt": ""})
    video_glob: str  # Optional. Used to collect videos to match. (Default: "*.mkv")
    subtitle_ep_pattern: str  # Optional. Used to identify the episode info from the subtitle file. (Default: simple_ep_pattern)
    video_ep_pattern: str  # Optional. Used to identify the episode info from the video file. (Default: simple_ep_pattern)


def rename_subtitles(
    video_stem_by_ep_collection: dict[str, pathlib.Path],
    sub_glob: str = "*.ass",
    sub_ep_pattern: Pattern[str] = simple_ep_pattern,
    sub_lang: str = "",
    working_directory: pathlib.Path = pathlib.Path(),
) -> None:
    """
    1. Search for all subtitles matching the sub_glob pattern.
    2. For each subtitle, see if there is a matching video file of the same episode.
    3. If there is a matching video file, then rename subtitle to
    the video file's stem + .<language> + .<file extension>
    4. Print each subtitle's name, its new name, and the video file's name.
    5. Prompt user for confirmation to rename all the subtitles.
    6. If user confirms, then rename all the subtitles.
    """
    pending_rename_operation_collection: List[Tuple[pathlib.Path, str]] = []
    print("Subtitles matched; Subtitles new name:")
    for sub_file in working_directory.glob(sub_glob):
        m = sub_ep_pattern.search(sub_file.stem)
        if m and m[1] in video_stem_by_ep_collection:
            sub_new_suffix = (
                f".{sub_lang}{sub_file.suffix}"
                if sub_lang
                else "".join(sub_file.suffixes)
            )
            video = video_stem_by_ep_collection[m[1]]
            sub_new_name = video.stem + sub_new_suffix
            print(sub_file.name, sub_new_name, sep=";\t")
            pending_rename_operation_collection.append((sub_file, sub_new_name))
    if prompt_for_user_confirmation("Apply renaming?"):
        for sub_file, sub_new_name in pending_rename_operation_collection:
            sub_file.rename(sub_file.with_name(sub_new_name))


if __name__ == "__main__":
    # Read command line argument(s)
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename softsubs to match a series of videos."
        ' Look at the globs / patterns etc in a file named "sub-utils.json" to determine to rename which subtitles to what file names.'
        " Patterns are used to extract episode info from videos and subtitles."
        " A template JSON file will be created in the working_directory if not exist and opened for editing.",
    )
    parser.add_argument(
        "video_directory",
        nargs="?",
        default=pathlib.Path(),
        type=pathlib.Path,
        help='The directory containing videos, "sub-utils.json", and the subtitles. (Default: current working directory)',
    )
    cli_args = parser.parse_args()

    # Read metadata
    json_file: pathlib.Path = cli_args.video_directory / metadata_filename
    if json_file.is_file():
        metadata: RenamingMetadata = json.loads(json_file.read_text())
    else:
        print("Metadata file doesn't exist.")
        metadata = {
            "subtitle_ep_pattern": r".*\s(\d{2})\s.*",
            "subtitle_tag_by_glob_collection": {"*.ass": "ja"},
            "video_ep_pattern": r".*\s(\d{2})\s.*",
            "video_glob": "*.mkv",
        }
        json_file.write_text(json.dumps(metadata, indent=2))
        print("Template created.")
        exit()

    video_ep_pattern = re.compile(metadata["video_ep_pattern"])
    subtitle_ep_pattern = re.compile(metadata["subtitle_ep_pattern"])
    video_by_ep_collection = get_video_by_ep_collection_with_glob_and_pattern(
        metadata["video_glob"], video_ep_pattern, cli_args.video_directory
    )
    print_video_by_ep_collection(video_by_ep_collection)
    print()
    for subtitle_glob, tag in metadata["subtitle_tag_by_glob_collection"].items():
        rename_subtitles(
            video_by_ep_collection,
            subtitle_glob,
            subtitle_ep_pattern,
            tag,
            cli_args.video_directory,
        )
