# IO Specification

---

## Scout Output (`scout_result.json`)

Scout が SeaweedFS の `ingest/{AppID}/scout_result.json` に書き込むメタデータです。
このファイルの存在は「処理済み」の判定基準としても使用されます。

```json
{
  "app_id": 123456,
  "name": "Example Game Soundtrack",
  "install_dir": "Example Game Soundtrack",
  "storage_location": "music",
  "track_count": 15,
  "files_by_ext": {
    "flac": {
      "count": 15,
      "keys": [
        "ingest/123456/Disc 1/flac/01 - Track One.flac",
        "ingest/123456/Disc 1/flac/02 - Track Two.flac"
      ]
    },
    "mp3": {
      "count": 15,
      "keys": [
        "ingest/123456/Disc 1/mp3/01 - Track One.mp3",
        "ingest/123456/mp3/02 - Track Two.mp3"
      ]
    }
  },
  "acf_key": "ingest/123456/manifest.acf",
  "uploaded_at": "2026-04-03T00:00:00+00:00",
  "dry_run": false
}
```

### S3 キーの構成ルール

Scout は音源ファイルを以下の規則に従って配置します。

1. **基本構造**: `ingest/{AppID}/{Disk No.}/{拡張子}/{ファイル名}`
   - `{Disk No.}` は `Disc 1`, `Disc 2` 等。
   - 音源ファイルが特定のディスク用ディレクトリに入っていない（平坦な構造の）場合、デフォルトで `Disc 1` が補完されます。
   - 元のディレクトリ構造が `Disc`, `CD`, `Volume` 等で始まっている場合は、その構造が維持されます。
   - これにより、多枚組サウンドトラックなどで同名のディレクトリが拡張子ごとに重複することを防ぎます。
2. **パスの正規化**:
   - `install_path` からの相対パスに含まれるディレクトリ名が、現在の拡張子の名前（例: `flac`, `mp3`）と一致する場合（大文字小文字無視）、そのディレクトリは冗長とみなして除去します。
   - 例: `install_path/track.flac` → `ingest/123/Disc 1/flac/track.flac` (Disc 1 補完)
   - 例: `install_path/FLAC/track.flac` → `ingest/123/Disc 1/flac/track.flac` (正規化 + Disc 1 補完)
   - 例: `install_path/Disc 1/FLAC/track.flac` → `ingest/123/Disc 1/flac/track.flac` (正規化 + 構造維持)

フィールド説明:

| フィールド | 型 | 説明 |
|-----------|------|------|
| `app_id` | int | Steam AppID |
| `name` | str | ACF から取得したアプリ名 |
| `install_dir` | str | ACF の `installdir` 値 |
| `storage_location` | str | `"music"` または `"common"` |
| `track_count` | int | 全拡張子の合計トラック数 |
| `files_by_ext` | dict | 拡張子別のファイル数と S3 キー一覧 |
| `acf_key` | str | ACF ファイルの S3 キー |
| `uploaded_at` | str | アップロード日時 (ISO 8601) |
| `dry_run` | bool | dry-run モードで実行されたかどうか |

---

## Worker Input

Worker は SeaweedFS の `ingest/{AppID}/` 以下のファイルを処理対象として受け取ります。

```json
{
  "app_id": 123456,
  "files": [
    "ingest/123456/flac/01 - Track One.flac"
  ]
}
```

---

## Worker Output

```json
{
  "app_id": 123456,
  "file_refs": ["ingest/123456/flac/01 - Track One.flac"],
  "status": "success",
  "resolved": {
    "resolved": true,
    "album": "Example Album",
    "artist": "Example Artist",
    "mbid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "resolution": "partial",
    "partial_ratio": 0.85
  },
  "tag_result": {
    "updated": 1,
    "dry_run": false
  },
  "candidate_count": 5,
  "storage": {
    "bucket": "sst",
    "key": "archive/app_123456_20260101T000000Z.json"
  }
}
```

status values: "success" | "review"

---

## Internal

```json
{
  "state": "PROCESSING",
  "node": "worker"
}
```

---

# END

