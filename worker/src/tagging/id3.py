"""ID3 タグ書き込み。"""
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK


def write_tags(file_path: str, metadata: dict) -> None:
    """ID3v2.3 タグを書き込む。

    Args:
        file_path: 対象ファイルパス
        metadata: タグ情報。キー:
            - album: str
            - title: str
            - artist: str
            - track_number: int | None
            - total_tracks: int | None
    """
    path = Path(file_path)
    if path.suffix.lower() != ".mp3":
        return

    album = str(metadata.get("album", "Unknown Album"))
    title = str(metadata.get("title", path.stem))
    artist = str(metadata.get("artist", "Unknown Artist"))
    track_number = metadata.get("track_number")
    total_tracks = metadata.get("total_tracks")

    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()
    tags.delall("TALB")
    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("TRCK")
    tags.add(TALB(encoding=3, text=album))
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if track_number is not None:
        trck = f"{track_number}/{total_tracks}" if total_tracks else str(track_number)
        tags.add(TRCK(encoding=3, text=trck))
    tags.save(file_path, v2_version=3)
