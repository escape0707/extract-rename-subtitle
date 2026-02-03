from sub_utils.extract import infer_sub_lang_by_track


def test_infer_sub_lang_by_track() -> None:
    info = {
        "streams": [
            {"tags": {"language": "eng", "title": "Full"}},
            {"tags": {"language": "jpn"}},
        ]
    }
    mapping = infer_sub_lang_by_track(info)
    assert mapping == {0: "eng-Full", 1: "jpn"}
