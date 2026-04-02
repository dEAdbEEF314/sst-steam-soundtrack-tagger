"""write_tags のテスト。"""
from pathlib import Path

from mutagen.id3 import ID3

from tagging.id3 import write_tags


def test_write_tags_sets_track_number_for_mp3(tmp_path: Path):
    # 空の mp3 ファイルを作成して ID3 ヘッダ書き込みをテスト
    target = tmp_path / "sample.mp3"
    target.write_bytes(b"")

    write_tags(
        file_path=str(target),
        metadata={
            "album": "Album",
            "title": "Title",
            "artist": "Artist",
            "track_number": 2,
            "total_tracks": 10,
        },
    )

    tags = ID3(str(target))
    assert tags.get("TRCK") is not None
    assert str(tags.get("TRCK").text[0]) == "2/10"
