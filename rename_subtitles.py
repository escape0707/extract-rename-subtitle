#!/usr/bin/env python

import argparse
from argparse import Namespace
from pathlib import Path

from SubtitleRenamer import SubtitleRenamer


def parse_args() -> Namespace:
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


def main():
    cli_args = parse_args()
    video_dir: Path = cli_args.video_directory
    renamer = SubtitleRenamer.new(video_dir)
    renamer.print_ep_to_video_map()
    renamer.rename_subtitles()


if __name__ == "__main__":
    main()
