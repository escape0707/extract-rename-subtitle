#!/usr/bin/env python

import argparse
from argparse import Namespace
from pathlib import Path

from SubtitleExtractor import SubtitleExtractor


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        description="Extract softsubs from a series of videos."
        ' Look at the globs / patterns / track information etc in a file named "sub-utils.json" to determine from which videos to extract and to what subtitle file name to write.'
        " Patterns are used to extract episode info from input videos and optionally match output subtitles to output videos names."
        " A template JSON file will be created in the working_directory if not exist and opened for editing.",
    )
    parser.add_argument(
        "video_directory",
        nargs="?",
        default=Path(),
        type=Path,
        help='The directory containing source videos and "sub-utils.json", also the place to put extracted subtitles. (Default: current working directory)',
    )
    return parser.parse_args()


def main() -> None:
    cli_args = parse_args()
    video_dir: Path = cli_args.video_directory
    extractor = SubtitleExtractor.new(video_dir)
    extractor.extract_subtitles()
    extractor.extract_fonts()


if __name__ == "__main__":
    main()
