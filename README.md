# Sub-Utils

Utilities to extract and rename subtitle files so they match your video filenames. Designed for anime and other episodic collections with softsubs.

## Features

- Extract subtitle streams with ffmpeg.
- Rename subtitle files to match video names.
- Extract embedded fonts from video attachments.
- TOML config with regex-based episode matching.

## Requirements

`ffmpeg` and `ffprobe` on PATH

## Install (local dev)

```bash
uv venv
uv sync
```

## Quickstart

```bash
sub-utils init
sub-utils rename --dry-run
sub-utils rename
sub-utils extract --dry-run
sub-utils extract
sub-utils fonts
```

## Config

Default config file is `sub-utils.toml` in your working directory.

```toml
[rename]
video_glob = "*.mkv"
video_ep_pattern = '\s(\d{2})\s'
subtitle_ep_pattern = '\s(\d{2})\s'

[rename.subtitle_tag_by_glob]
"*.ass" = "ja"
"*.srt" = "en"

[extract]
origin_video_glob = "*.mkv"
# target_video_glob = "*.mp4"
# origin_video_ep_pattern = '\s(\d{2})\s'
# target_video_ep_pattern = '\s(\d{2})\s'

[extract.sub_lang_by_track]
0 = "eng"
1 = "jpn"

[fonts]
video_glob = "*.mkv"
output_dir = "fonts"
```

## Commands

- `sub-utils init` creates a template `sub-utils.toml`.
- `sub-utils probe` shows subtitle stream indexes and language tags.
- `sub-utils extract` extracts subtitle tracks based on config.
- `sub-utils rename` renames subtitle files to match videos.
- `sub-utils fonts` extracts font attachments to a folder.
- Use `--config` to point to a different TOML file and `--dir` to set the working directory.

## Safety

- Default behavior shows a plan and asks before applying changes.
- Use `--dry-run` to plan only.
- Use `--yes` to skip confirmation.
- Use `--overwrite` to overwrite existing files.

## Notes

- Regex patterns capture the episode number in group 1.
- If you have multiple subtitle groups, define multiple globs in `rename.subtitle_tag_by_glob`. For example you have a group of English subtitles named "XXXX-en.srt" and a group of Japanese subtitles named "XXXX.japanese.srt" and you want to rename them to "EPXX.en.srt" and "EPXX.ja.srt" respectively, then you can use:

  ```toml
  [rename.subtitle_tag_by_glob]
  "*-en.srt" = "en"
  "*.japanese.srt" = "ja"
  ```

- If `extract.sub_lang_by_track` is omitted, sub-utils will try to infer language tags from ffprobe.

## Copyright

Copyright (C) 2026 Escape0707

## License

AGPL-3.0-or-later
