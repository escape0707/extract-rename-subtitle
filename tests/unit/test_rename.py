import pathlib
import re

from sub_utils.rename import build_video_by_episode, plan_rename


def test_plan_rename_matches_episodes(tmp_path: pathlib.Path) -> None:
    video1 = tmp_path / "Show 01.mkv"
    video2 = tmp_path / "Show 02.mkv"
    subtitle1 = tmp_path / "Subs 01.ass"
    subtitle2 = tmp_path / "Subs 03.ass"

    video1.write_text("v")
    video2.write_text("v")
    subtitle1.write_text("s")
    subtitle2.write_text("s")

    pattern = re.compile(r"\s(\d{2})")
    mapping, issues = build_video_by_episode([video1, video2], pattern)
    assert not issues

    plan = plan_rename(
        workdir=tmp_path,
        subtitle_glob="*.ass",
        subtitle_pattern=pattern,
        video_by_episode=mapping,
        tag="ja",
        overwrite=False,
    )

    assert len(plan.operations) == 1
    assert plan.operations[0].destination.name == "Show 01.ja.ass"
    assert any("No video match" in item for item in plan.skipped)
