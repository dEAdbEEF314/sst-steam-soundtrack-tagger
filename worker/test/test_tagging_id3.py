from pathlib import Path

from mutagen.id3 import ID3

from tagging.id3 import write_basic_id3


def test_write_basic_id3_sets_track_number_for_mp3(tmp_path: Path):
    # Create an empty mp3-like file for ID3 header writing.
    target = tmp_path / "sample.mp3"
    target.write_bytes(b"")

    write_basic_id3(
        file_path=str(target),
        album="Album",
        title="Title",
        artist="Artist",
        track_number=2,
        total_tracks=10,
    )

    tags = ID3(str(target))
    assert tags.get("TRCK") is not None
    assert str(tags.get("TRCK").text[0]) == "2/10"
