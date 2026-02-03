from __future__ import annotations

from dataclasses import dataclass
import pathlib
import re
import tomllib
from typing import Any, Mapping

CONFIG_FILENAME = "sub-utils.toml"
DEFAULT_EP_PATTERN = r"\s(\d{2})\s"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenameConfig:
    video_glob: str
    video_ep_pattern: re.Pattern[str]
    subtitle_ep_pattern: re.Pattern[str]
    subtitle_tag_by_glob: dict[str, str]


@dataclass(frozen=True)
class ExtractConfig:
    origin_video_glob: str
    sub_lang_by_track: dict[int, str] | None
    target_video_glob: str | None
    origin_video_ep_pattern: re.Pattern[str]
    target_video_ep_pattern: re.Pattern[str]


@dataclass(frozen=True)
class FontsConfig:
    video_glob: str
    output_dir: str


@dataclass(frozen=True)
class Config:
    rename: RenameConfig
    extract: ExtractConfig
    fonts: FontsConfig
    path: pathlib.Path


def load_config(path: pathlib.Path) -> Config:
    if not path.is_file():
        raise ConfigError(
            f"Config not found: {path}. Run `sub-utils init` to create one."
        )
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("Invalid TOML structure.")
    rename = _parse_rename_config(_get_table(data, "rename"))
    extract = _parse_extract_config(_get_table(data, "extract"))
    fonts = _parse_fonts_config(_get_table(data, "fonts"), extract)
    return Config(rename=rename, extract=extract, fonts=fonts, path=path)


def config_template() -> str:
    return """# sub-utils.toml
# Regex patterns use single quotes to avoid escaping backslashes.

[rename]
video_glob = "*.mkv"
video_ep_pattern = '\\s(\\d{2})\\s'
subtitle_ep_pattern = '\\s(\\d{2})\\s'

[rename.subtitle_tag_by_glob]
"*.ass" = "ja"
"*.srt" = "en"

[extract]
origin_video_glob = "*.mkv"
# target_video_glob = "*.mp4"
# origin_video_ep_pattern = '\\s(\\d{2})\\s'
# target_video_ep_pattern = '\\s(\\d{2})\\s'

# If omitted, sub-utils will infer language tags from ffprobe.
[extract.sub_lang_by_track]
0 = "eng"
1 = "jpn"

[fonts]
video_glob = "*.mkv"
output_dir = "fonts"
"""


def _parse_rename_config(table: Mapping[str, Any]) -> RenameConfig:
    video_glob = _expect_str(table.get("video_glob", "*.mkv"), "rename.video_glob")
    video_ep_pattern = _compile_pattern(
        _expect_str(
            table.get("video_ep_pattern", DEFAULT_EP_PATTERN),
            "rename.video_ep_pattern",
        ),
        "rename.video_ep_pattern",
    )
    subtitle_ep_pattern = _compile_pattern(
        _expect_str(
            table.get("subtitle_ep_pattern", DEFAULT_EP_PATTERN),
            "rename.subtitle_ep_pattern",
        ),
        "rename.subtitle_ep_pattern",
    )
    tag_table = table.get("subtitle_tag_by_glob", {"*.ass": "", "*.srt": ""})
    subtitle_tag_by_glob = _expect_str_mapping(
        tag_table, "rename.subtitle_tag_by_glob"
    )
    return RenameConfig(
        video_glob=video_glob,
        video_ep_pattern=video_ep_pattern,
        subtitle_ep_pattern=subtitle_ep_pattern,
        subtitle_tag_by_glob=subtitle_tag_by_glob,
    )


def _parse_extract_config(table: Mapping[str, Any]) -> ExtractConfig:
    origin_video_glob = _expect_str(
        table.get("origin_video_glob", "*.mkv"), "extract.origin_video_glob"
    )
    target_video_glob = table.get("target_video_glob")
    if target_video_glob is not None:
        target_video_glob = _expect_str(
            target_video_glob, "extract.target_video_glob"
        )
    origin_video_ep_pattern = _compile_pattern(
        _expect_str(
            table.get("origin_video_ep_pattern", DEFAULT_EP_PATTERN),
            "extract.origin_video_ep_pattern",
        ),
        "extract.origin_video_ep_pattern",
    )
    target_video_ep_pattern = _compile_pattern(
        _expect_str(
            table.get("target_video_ep_pattern", DEFAULT_EP_PATTERN),
            "extract.target_video_ep_pattern",
        ),
        "extract.target_video_ep_pattern",
    )
    sub_lang_by_track = table.get("sub_lang_by_track")
    parsed_sub_lang_by_track: dict[int, str] | None = None
    if sub_lang_by_track is not None:
        if not isinstance(sub_lang_by_track, dict):
            raise ConfigError("extract.sub_lang_by_track must be a table")
        parsed_sub_lang_by_track = {}
        for key, value in sub_lang_by_track.items():
            try:
                index = int(key)
            except (TypeError, ValueError) as exc:
                raise ConfigError(
                    "extract.sub_lang_by_track keys must be integers"
                ) from exc
            if not isinstance(value, str):
                raise ConfigError(
                    "extract.sub_lang_by_track values must be strings"
                )
            parsed_sub_lang_by_track[index] = value
    return ExtractConfig(
        origin_video_glob=origin_video_glob,
        sub_lang_by_track=parsed_sub_lang_by_track,
        target_video_glob=target_video_glob,
        origin_video_ep_pattern=origin_video_ep_pattern,
        target_video_ep_pattern=target_video_ep_pattern,
    )


def _parse_fonts_config(table: Mapping[str, Any], extract: ExtractConfig) -> FontsConfig:
    video_glob = _expect_str(
        table.get("video_glob", extract.origin_video_glob), "fonts.video_glob"
    )
    output_dir = _expect_str(table.get("output_dir", "fonts"), "fonts.output_dir")
    return FontsConfig(video_glob=video_glob, output_dir=output_dir)


def _compile_pattern(pattern: str, field_name: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ConfigError(f"Invalid regex for {field_name}: {exc}") from exc


def _expect_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string")
    return value


def _expect_str_mapping(value: Any, field_name: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field_name} must be a table")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ConfigError(f"{field_name} must map strings to strings")
        result[key] = item
    return result


def _get_table(data: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a table")
    return value
