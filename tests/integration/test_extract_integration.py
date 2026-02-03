import pathlib
import re
import shutil
import subprocess

import pytest

from sub_utils.extract import apply_extract, plan_extract


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.integration
def test_extract_integration(tmp_path: pathlib.Path) -> None:
    if not _ffmpeg_available():
        pytest.skip("ffmpeg/ffprobe not available")

    subtitle_path = tmp_path / "subtitle.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:00,500\nHello\n", encoding="utf-8"
    )

    video_path = tmp_path / "Show 01.mkv"
    cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=black:s=160x120:d=1",
        "-f",
        "srt",
        "-i",
        str(subtitle_path),
        "-c:v",
        "libx264",
        "-c:s",
        "srt",
        "-y",
        str(video_path),
    ]
    subprocess.run(cmd, check=True)

    plan = plan_extract(
        origin_videos=[video_path],
        sub_lang_by_track={0: "eng"},
        target_video_by_episode=None,
        origin_episode_pattern=re.compile(r"\s(\d{2})\s"),
        overwrite=True,
    )
    apply_extract(plan)

    extracted = tmp_path / "Show 01.eng.srt"
    assert extracted.exists()
