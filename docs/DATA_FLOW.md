# DATA FLOW

## Overview

SST processes Steam-purchased soundtrack files through a multi-phase identification pipeline.

---

## Pipeline

### 0. SCOUT INGEST（パイプライン起点）

Scout はシステムの起点として、ローカルの Steam ライブラリを走査し、音源ファイルとメタデータを SeaweedFS に効率的に取り込みます。

- **Source**: Steam ライブラリ（`STEAM_LIBRARY_PATH`）
- **Process**:
  1. `steamapps/appmanifest_*.acf` を走査
  2. ACF の `name` フィールドにサウンドトラックキーワードが含まれるか判定
  3. `steamapps/music/` → `steamapps/common/` の順でインストールディレクトリを探索
  4. 既処理チェック: SeaweedFS 上の `ingest/{AppID}/scout_result.json` の存在を確認（`--force` でスキップ可能）
  5. 音源収集: 対象拡張子（`.flac`, `.mp3`, `.wav` 等）に一致する全ファイルを収集・分類
  6. 正規化・修正: 冗長なフォルダ（`FLAC/` 等）の除去と、Missing な `Disc 1` 階層の自動補完
  7. アップロード: 音源、ACF、および統計メタデータ（`scout_result.json`）をコピー

- **SeaweedFS 上のアセット配置**:
  ```text
  ingest/{AppID}/manifest.acf
  ingest/{AppID}/scout_result.json
  ingest/{AppID}/{Disk No.}/{ext}/{filename}
  ```
  - **構造化ルール**: `Disc 1` 等のディスク階層（{Disk No.}）を優先し、その配下に拡張子ディレクトリを配置します。内部階層がない場合は `Disc 1` がデフォルトで補完されます。
  - **パス正規化**: 元のフォルダ名が現在の拡張子名と完全に一致する場合、重複を避けるためにその階層を除去します。

- **Output**:
  - `scout_result.json`: AppID、トラック数、拡張子別 S3 キー一覧、アップロード日時等の詳細メタデータ

---

### 1. INPUT

- Source: SeaweedFS `ingest/{AppID}/` 以下の音源ファイル
- Metadata: Steam AppID（`scout_result.json` から取得）


2. STEAM METADATA FETCH

- Input: AppID
- Output:
  - title (localized)
    - release_date

---

3. MUSICBRAINZ SEARCH (MULTI-LANGUAGE MERGE)

- Input:
  - title (ja → en → original)
- Process:
  - Perform multiple queries
  - Merge results
  - Deduplicate by MBID

- Output:
  - candidate albums

---

4. CANDIDATE FILTERING

Conditions:
- format = Digital Media
- track_count ≈ local file count (±1)
- release_date ≈ Steam release date (±30 days)

---

5. SCORING

Each candidate receives a score:

score =
  title_similarity +
  track_count_match +
  release_date_match +
  format_match

---

6. DECISION

- If score ≥ threshold:
  → proceed to partial verification
- Else:
  → fallback to full AcoustID

---

7. PARTIAL ACOUSTID VERIFICATION

- Input: first 3 tracks
- Process:
  - fingerprint
  - match via AcoustID

- If match_ratio ≥ 0.8:
  → ACCEPT album
- Else:
  → fallback to full AcoustID

---

8. FULL ACOUSTID (FALLBACK)

- Process all tracks
- Aggregate matches
- Determine album

---

9. TAGGING

- Write ID3v2.3 tags
- Normalize metadata

---

10. STORAGE

- Save archived output files
- Store metadata JSON
- Upload review cases to SeaweedFS

---

## Notes

- Album-level and track-level logic MUST be separated
- All decisions must be deterministic and reproducible
