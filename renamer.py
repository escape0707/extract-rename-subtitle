from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import TypedDict

from subtitle_utils import (
    RENAME_CONFIG_FILENAME,
    SIMPLE_EP_PATTERN,
    get_ep_to_video_map,
    get_paths_with_glob,
    print_ep_to_video_map,
    prompt_for_user_confirmation,
)


class RenameConfig(TypedDict):
    # Optional. Used to extract episode information from the subtitle file.
    subtitle_ep_pattern: str
    # Optional. A mapping of glob patterns to tags. Used to collect subtitles to
    # rename and given them a tag in the resulting name. Tags can denote the
    # subtitle's language or the fan sub group name. Use an empty string as tag
    # to avoid adding/changing subtitle suffixes.
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


@dataclass
class SubtitleRenamer:
    ep_to_video_map: dict[str, Path]
    sub_glob_tag_filepaths: tuple[tuple[str, str, list[Path]], ...]
    sub_ep_pattern: Pattern[str]

    @staticmethod
    def new(video_dir: Path) -> SubtitleRenamer:
        config_filepath = video_dir / RENAME_CONFIG_FILENAME
        if not config_filepath.is_file():
            print("Metadata file doesn't exist.")
            config_filepath.write_text(json.dumps(DEFAULT_RENAME_CONFIG, indent=2))
            print("Template created.")
            raise SystemExit
        configs: RenameConfig = json.loads(config_filepath.read_bytes())
        video_ep_pattern = re.compile(configs["video_ep_pattern"])
        ep_to_video_map = get_ep_to_video_map(
            configs["video_glob"], video_ep_pattern, video_dir
        )
        sub_glob_tag_filepaths = tuple(
            (glob, tag, get_paths_with_glob(glob))
            for glob, tag in configs["glob_to_subtitle_tag_map"]
        )
        sub_ep_pattern = re.compile(configs["subtitle_ep_pattern"])
        return SubtitleRenamer(
            ep_to_video_map, sub_glob_tag_filepaths, sub_ep_pattern
        )

    def print_ep_to_video_map(self):
        print_ep_to_video_map(self.ep_to_video_map)
        print()

    def rename_subtitles(
        self,
        sub_ep_pattern: Pattern[str] = SIMPLE_EP_PATTERN,
        working_directory: Path = Path(),
    ):
        """
        1. Collect all subtitles matching `sub_glob`.
        2. For each subtitle, look for a matching video file of the same episode.
        3. If there is a matching video file, then prepare to rename the subtitle to
        `<video file stem>.<subtitle tag>.<subtitle file extension>`.
        4. Print each subtitle's name, its new name, and the matching video file's
        name.
        5. Prompt user for confirmation before renaming all subtitles.
        """

        for sub_glob, sub_tag, sub_filepaths in self.sub_glob_tag_filepaths:
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
                for sub_filepath in sub_filepaths
                if (match := sub_ep_pattern.search(sub_filepath.stem))
                and (video := self.ep_to_video_map.get(match[1]))
            ]
            # Tried to rewrite printing procedure with functional style but PEP 3113
            # (Removal of tuple parameter unpacking) made this so ugly.
            # print(
            #     *map(lambda change: "f{change[0].name};\t{change[1]}", proposed_changes),
            #     sep="\n",
            # )
            if not proposed_changes:
                print(f"No subtitle-video match found for subtitle glob: {sub_glob}")
                continue
            print("Subtitles matched;\tSubtitles new name:")
            for sub_filepath, sub_new_name in proposed_changes:
                print(f"{sub_filepath.name};\t{sub_new_name}")
            if prompt_for_user_confirmation("Apply renaming?"):
                for sub_filepath, sub_new_name in proposed_changes:
                    sub_filepath.rename(sub_filepath.with_name(sub_new_name))
