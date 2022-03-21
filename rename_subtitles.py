#!/usr/bin/env python

import pathlib
import re
from typing import List, Pattern, Tuple

from subtitle_utils import (
    get_video_by_ep_collection_with_glob_and_pattern,
    print_video_by_ep_collection,
    prompt_for_user_confirmation,
    simple_ep_pattern,
)


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
        m = sub_ep_pattern.match(sub_file.stem)
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
    video_glob = "*.mkv"
    # video_ep_pattern = simple_ep_pattern
    video_ep_pattern = re.compile(r".*\s(\d{2})[v\s].*")
    # video_ep_pattern = re.compile(r".*\[(\d{2})\].*")
    sub_glob = "*.ass"
    # sub_ep_pattern = simple_ep_pattern
    sub_ep_pattern = re.compile(r".*\[(\d{2})\].*")
    # sub_ep_pattern = re.compile(r".*\s(\d{2})\..*")
    # sub_ep_pattern = re.compile(r".*第(\d{2})話.*")
    sub_lang = ""
    # sub_lang = "zh-Hant"

    video_by_ep_collection = get_video_by_ep_collection_with_glob_and_pattern(
        video_glob, video_ep_pattern
    )
    print_video_by_ep_collection(video_by_ep_collection)
    print()
    rename_subtitles(video_by_ep_collection, sub_glob, sub_ep_pattern, sub_lang)
