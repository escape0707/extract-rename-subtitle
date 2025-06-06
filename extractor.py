from __future__ import annotations

import itertools
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Any, Iterator, Optional, Required, TypedDict

from subtitle_utils import (
    EXTRACTION_CONFIG_FILENAME,
    SIMPLE_EP_PATTERN,
    SUB_CODEC_TO_SUFFIX_MAP,
    get_ep_to_video_map,
    get_paths_with_glob,
    get_sub_stream_id_to_tag_map,
    get_sub_streams_info,
    prompt_for_user_confirmation,
)


class ExtractionConfig(TypedDict, total=False):
    # Mandatory. Used to collect videos to extract subtitles from.
    origin_video_glob: Required[str]
    # Optional. Extract subtitle streams from specified subtitle stream track
    # id. Track id corresponds to ffmpeg's `-map 0:s:<sub_index>`. The string
    # will be used as extracted subtitle's language tag.
    sub_stream_id_to_tag_map: dict[int, str]
    # Optional. If supplied, extracted subtitles will be renamed after another
    # series of videos. If not supplied, origin_video_ep_pattern and
    # target_video_ep_pattern will be ignored and extracted subtitles will be
    # renamed after the original videos.
    target_video_glob: str
    # Optional. Only used when targeting another series of videos to identify
    # the episode info from the targeting video. (Default: simple_ep_pattern)
    target_video_ep_pattern: str
    # Optional. Only used when targeting another series of videos to identify
    # the episode info from the original video. (Default: simple_ep_pattern)
    origin_video_ep_pattern: str


DEFAULT_EXTRACTION_CONFIG: ExtractionConfig = {
    "origin_video_glob": "*.mkv",
    "sub_stream_id_to_tag_map": {0: "eng", 1: "jpn"},
    # "target_video_glob": "*.mp4",
    # "target_video_ep_pattern": r".*\s(\d{2})\s.*",
    # "origin_video_ep_pattern": r".*\s(\d{2})\s.*",
}


@dataclass
class SubtitleExtractor:
    origin_videos: list[Path]
    sub_stream_id_to_tag_map: Optional[dict[int, str]] = None
    ep_to_target_video_map: Optional[dict[str, Path]] = None
    origin_video_ep_pattern: Pattern[str] = SIMPLE_EP_PATTERN
    font_dir: Optional[Path] = None

    @staticmethod
    def new(video_dir: Path) -> SubtitleExtractor:
        config_filepath = video_dir / EXTRACTION_CONFIG_FILENAME
        if not config_filepath.is_file():
            print("Metadata file doesn't exist.")
            config_filepath.write_text(json.dumps(DEFAULT_EXTRACTION_CONFIG, indent=2))
            print("Template created.")
            raise SystemExit
        configs: ExtractionConfig = json.loads(config_filepath.read_bytes())
        origin_videos = get_paths_with_glob(configs["origin_video_glob"], video_dir)
        sub_stream_id_to_tag_map = configs.get("sub_stream_id_to_tag_map")
        if not (target_video_glob := configs.get("target_video_glob")):
            return SubtitleExtractor(origin_videos, sub_stream_id_to_tag_map)
        target_video_ep_pattern = (
            re.compile(p)
            if (p := configs.get("target_video_ep_pattern"))
            else SIMPLE_EP_PATTERN
        )
        ep_to_target_video_map = get_ep_to_video_map(
            target_video_glob,
            target_video_ep_pattern,
            video_dir,
        )
        origin_video_ep_pattern = (
            re.compile(p)
            if (p := configs.get("origin_video_ep_pattern"))
            else SIMPLE_EP_PATTERN
        )
        return SubtitleExtractor(
            origin_videos,
            sub_stream_id_to_tag_map,
            ep_to_target_video_map,
            origin_video_ep_pattern,
        )

    def extract_subtitles(self):
        """
        1. Extract all the subtitle tracks from the origin video.
        2. Use sub_stream_id_to_tag_map to map each subtitle track to a language,
        which we can use to name the subtitle file.
        3. Use origin_videos to generate the command for each sub_track,
        and then use shlex.join to join the cmd tuple to a string, then print it to the terminal.
        """
        assert self.origin_videos
        pending_subtitle_extraction: tuple[tuple[str, ...], ...] = tuple(
            itertools.chain.from_iterable(
                map(
                    self._generate_extraction_cmds,
                    self.origin_videos,
                )
            )
        )
        print("Subtitle extraction commands to be executed:")
        print(*map(shlex.join, pending_subtitle_extraction), sep="\n")
        if prompt_for_user_confirmation("Start subtitle extraction?"):
            for cmd in pending_subtitle_extraction:
                subprocess.run(cmd)

    def extract_fonts(self):
        assert self.origin_videos
        font_dir = self.font_dir or self.origin_videos[0].with_name("fonts")
        pending_font_extraction: tuple[tuple[str, ...], ...] = tuple(
            (
                "ffmpeg",
                "-dump_attachment:t",  # dump all attachments
                "",  # with name guessed from attachments' filename field
                "-n",  # do not overwrite
                "-i",  # input file url follows
                # When extracting we will run ffmpeg from another directory to store
                # all attachments there. Thus we resolve the absolute path now.
                str(video.resolve()),
            )
            for video in self.origin_videos
        )
        print("Font extraction commands to be executed:")
        print(*map(shlex.join, pending_font_extraction), sep="\n")
        if prompt_for_user_confirmation(f'Extract font to folder "{font_dir}?"'):
            if not font_dir.is_dir():
                # If exist_ok is true, FileExistsError will not be raised unless the
                # given path already exists in the file system and is not a
                # directory. This is by design and the user should then take care of
                # the existing file and re-run the script.
                font_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
            for cmd in pending_font_extraction:
                subprocess.run(cmd, cwd=font_dir)

    def _get_sub_suffix(self, sub_index: int, sub_streams_info: Any) -> str:
        codec_name: str = sub_streams_info["streams"][sub_index]["codec_name"]
        return SUB_CODEC_TO_SUFFIX_MAP[codec_name]

    def _get_target_video(self, origin_video: Path) -> Path:
        if (
            self.ep_to_target_video_map
            and (match := self.origin_video_ep_pattern.search(origin_video.stem))
            and (target_video := self.ep_to_target_video_map.get(match[1]))
        ):
            return target_video
        return origin_video

    def _generate_extraction_cmds(
        self, origin_video: Path
    ) -> Iterator[tuple[str, ...]]:
        sub_streams_info = get_sub_streams_info(origin_video)
        sub_stream_id_to_tag_map = (
            self.sub_stream_id_to_tag_map
            or get_sub_stream_id_to_tag_map(sub_streams_info)
        )
        for sub_index, sub_lang in sub_stream_id_to_tag_map.items():
            new_suffix = (
                f".{sub_lang}.{self._get_sub_suffix(sub_index, sub_streams_info)}"
            )
            sub_path = self._get_target_video(origin_video).with_suffix(new_suffix)
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
                f"0:s:{sub_index}",  # extract this track from the input file
                str(sub_path),
            )
            yield cmd
