#!/usr/bin/env python

import json
import re
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, TypedDict

from subtitle_utils import (
    SIMPLE_EP_PATTERN,
    get_ep_to_video_map,
    get_paths_with_glob,
    print_ep_to_video_map,
    prompt_for_user_confirmation,
)

if TYPE_CHECKING:
    from argparse import Namespace

RENAME_CONFIG_FILENAME = "sub-rename-config.json"


class RenameConfig(TypedDict):
    # Optional. Used to extract episode information from the subtitle file.
    subtitle_ep_pattern: str
    # Optional. A mapping of glob patterns to tags. Used to collect subtitles to
    # rename and given them a tag in the resulting name. Tags can denote the
    # subtitle's language or the fan sub group name.
    glob_to_subtitle_tag_map: dict[str, str]
    # Optional. Used to extract episode information from the video file.
    video_ep_pattern: str
    # Optional. Used to collect video files.
    video_glob: str


DEFAULT_RENAME_CONFIG: RenameConfig = {
    "subtitle_ep_pattern": r".*\s(\d{2})\s.*",
    "glob_to_subtitle_tag_map": {"*.ass": "", "*.srt": ""},
    "video_ep_pattern": r".*\s(\d{2})\s.*",
    "video_glob": "*.mkv",
}


def rename_subtitles(
    ep_to_video_map: dict[str, Path],
    sub_glob: str = "*.ass",
    sub_ep_pattern: Pattern[str] = SIMPLE_EP_PATTERN,
    sub_tag: str = "",
    working_directory: Path = Path(),
) -> None:
    """
    1. Collect all subtitles matching `sub_glob`.
    2. For each subtitle, look for a matching video file of the same episode.
    3. If there is a matching video file, then prepare to rename the subtitle to
       `<video file stem>.<subtitle tag>.<subtitle file extension>`.
    4. Print each subtitle's name, its new name, and the matching video file's
       name.
    5. Prompt user for confirmation before renaming all subtitles.
    """
    # I already miss Rust's `.collect()`.
    proposed_changes: list[tuple[Path, str]] = [
        (
            sub_filepath,
            video.stem
            + (
                # Replace extra suffixes with sub_tag if provided
                f".{sub_tag}{sub_filepath.suffix}"
                if sub_tag
                else "".join(sub_filepath.suffixes)
            ),
        )
        for sub_filepath in get_paths_with_glob(sub_glob, working_directory)
        if (match := sub_ep_pattern.search(sub_filepath.stem))
        and (video := ep_to_video_map.get(match[1]))
    ]
    # Tried to rewrite printing procedure with functional style but PEP 3113
    # (Removal of tuple parameter unpacking) made this so ugly.
    # print(
    #     *map(lambda change: "f{change[0].name};\t{change[1]}", proposed_changes),
    #     sep="\n",
    # )
    if not proposed_changes:
        print("No subtitle-video match found.")
        return
    print("Subtitles matched;\tSubtitles new name:")
    for sub_filepath, sub_new_name in proposed_changes:
        print(sub_filepath.name, sub_new_name, sep=";\t")
    if prompt_for_user_confirmation("Apply renaming?"):
        for sub_filepath, sub_new_name in proposed_changes:
            sub_filepath.rename(sub_filepath.with_name(sub_new_name))


def parse_args() -> Namespace:
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename softsubs to match a series of videos."
        ' Look at the globs / patterns etc in a file named "sub-utils.json" to determine to rename which subtitles to what file names.'
        " Patterns are used to extract episode info from videos and subtitles."
        " A template JSON file will be created in the working_directory if not already existed, and the program will exit to give you a chance to edit it.",
    )
    parser.add_argument(
        "video_directory",
        nargs="?",
        default=Path(),
        type=Path,
        help='The directory containing videos, "sub-utils.json", and the subtitles. (Default: current working directory)',
    )
    return parser.parse_args()


def build_configs(config_filepath: Path) -> RenameConfig:
    if config_filepath.is_file():
        metadata: RenameConfig = json.loads(config_filepath.read_bytes())
        return metadata

    print("Metadata file doesn't exist.")
    config_filepath.write_text(json.dumps(DEFAULT_RENAME_CONFIG, indent=2))
    print("Template created.")
    raise SystemExit


def main() -> None:
    cli_args = parse_args()
    video_dir: Path = cli_args.video_directory
    configs = build_configs(video_dir / RENAME_CONFIG_FILENAME)

    video_ep_pattern = re.compile(configs["video_ep_pattern"])
    subtitle_ep_pattern = re.compile(configs["subtitle_ep_pattern"])
    ep_to_video_map = get_ep_to_video_map(
        configs["video_glob"], video_ep_pattern, video_dir
    )
    print_ep_to_video_map(ep_to_video_map)
    print()
    for subtitle_glob, tag in configs["glob_to_subtitle_tag_map"].items():
        rename_subtitles(
            ep_to_video_map,
            subtitle_glob,
            subtitle_ep_pattern,
            tag,
            video_dir,
        )


if __name__ == "__main__":
    main()
