from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK


def write_basic_id3(
    file_path: str,
    album: str,
    title: str,
    artist: str,
    track_number: int | None = None,
    total_tracks: int | None = None,
) -> None:
    path = Path(file_path)
    if path.suffix.lower() != ".mp3":
        return

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
