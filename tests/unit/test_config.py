import pathlib
import pytest

from sub_utils.config import ConfigError, load_config


def test_load_config_parses_toml(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "sub-utils.toml"
    config_path.write_text(
        """
[rename]
video_glob = "*.mkv"
video_ep_pattern = '\\s(\\d{2})\\s'
subtitle_ep_pattern = '\\s(\\d{2})\\s'

[rename.subtitle_tag_by_glob]
"*.ass" = "ja"

[extract]
origin_video_glob = "*.mkv"

[extract.sub_lang_by_track]
0 = "eng"

[fonts]
video_glob = "*.mkv"
output_dir = "fonts"
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.rename.video_glob == "*.mkv"
    assert config.extract.origin_video_glob == "*.mkv"
    assert config.extract.sub_lang_by_track == {0: "eng"}
    assert config.fonts.output_dir == "fonts"


def test_invalid_regex_raises(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "sub-utils.toml"
    config_path.write_text(
        """
[rename]
video_glob = "*.mkv"
video_ep_pattern = "("
subtitle_ep_pattern = "("

[rename.subtitle_tag_by_glob]
"*.ass" = "ja"

[extract]
origin_video_glob = "*.mkv"

[fonts]
video_glob = "*.mkv"
output_dir = "fonts"
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(config_path)
