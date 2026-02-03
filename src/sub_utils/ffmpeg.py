from __future__ import annotations

import json
import pathlib
import shlex
import shutil
import subprocess
from typing import Any


class FfmpegError(RuntimeError):
    pass


def ensure_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FfmpegError(
            f"Required executable '{name}' not found in PATH. Install ffmpeg."
        )
    return path


def run_ffprobe(video: pathlib.Path) -> dict[str, Any]:
    ensure_executable("ffprobe")
    cmd = (
        "ffprobe",
        "-loglevel",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        "s",
        str(video),
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FfmpegError(
            f"ffprobe failed for {video}: {result.stderr.strip() or 'unknown error'}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FfmpegError(f"Failed to parse ffprobe output for {video}") from exc


def run_ffmpeg(cmd: tuple[str, ...], cwd: pathlib.Path | None = None) -> None:
    ensure_executable("ffmpeg")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise FfmpegError(f"ffmpeg failed: {shlex.join(cmd)}")


def format_cmd(cmd: tuple[str, ...]) -> str:
    return shlex.join(cmd)
