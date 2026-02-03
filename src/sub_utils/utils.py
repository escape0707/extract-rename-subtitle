from __future__ import annotations

import pathlib
from typing import Iterable


def prompt_yes_no(text: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    reply = input(f"{text} {suffix} ").strip().lower()
    if not reply:
        return default_yes
    return reply in {"y", "yes"}


def sorted_paths(paths: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    return sorted(paths, key=lambda path: path.name.lower())
