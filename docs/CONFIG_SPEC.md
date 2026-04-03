# CONFIG_SPEC — SST 設定ファイル仕様

本ドキュメントは `config.yaml` で指定可能なすべてのキーを定義します。
環境変数が `ENV` と記されている項目は、環境変数からの上書きが可能です。

設定はコンポーネントごとに **共通 (core)** / **worker 固有** / **scout 固有** に分類されます。

---

## 共通設定 (core)

### llm

```yaml
llm:
  provider: ollama            # ollama, google-genai, openai
  model: qwen2.5-coder:14b
  api_key: ENV                # ENV: LLM_API_KEY（ローカル LLM では省略可）
  base_url: http://localhost:11434  # ENV: OLLAMA_BASE_URL
  temperature: 0.1
```

### storage

```yaml
storage:
  provider: s3_compatible
  endpoint_url: http://localhost:9000  # ENV: S3_ENDPOINT_URL
  bucket: sst                                  # ENV: S3_BUCKET
  prefixes:
    ingest: ingest/
    archive: archive/
    review: review/
    workspace: workspace/
```

### mode

```yaml
mode:
  dry_run: false
```

---

## Worker 固有設定

### steam

```yaml
steam:
  api_url: https://store.steampowered.com/api/appdetails
```

Notes:
- テスト時にモックサーバーの URL へ差し替え可能

### musicbrainz

```yaml
musicbrainz:
  app_name: sst
  app_version: "0.1"
  contact_url: https://example.invalid
```

Notes:
- MusicBrainz API 利用規約で User-Agent の設定が必須
- `contact_url` はプロジェクトの実際の連絡先 URL に変更することを推奨

### acoustid

```yaml
acoustid:
  api_url: https://api.acoustid.org/v2/lookup
  api_key: ENV                                  # ENV: ACOUSTID_API_KEY（必須）
  score_threshold: 0.9
  score_gap: 0.05
  partial_verify_tracks: 3
  partial_match_threshold: 0.8
  full_fallback_min_match_ratio: 0.4
```

### search

```yaml
search:
  languages:
    - ja
    - en
    - original
  strategy: merge
```

### album_match

```yaml
album_match:
  track_count_tolerance: 1
  date_tolerance_days: 30
```

### retry

```yaml
retry:
  max_attempts: 3
  base_delay_sec: 5
  backoff_strategy: exponential
  base_backoff_factor: 2
  acoustid_max_attempts: 3
  musicbrainz_max_attempts: 2
```

### format

```yaml
format:
  lossless_target: aiff
  max_sample_rate: 48000
  max_bit_depth: 24
```

Notes:
- max_sample_rate / max_bit_depth は変換時の上限値として使用
- ソースがこれ以下の場合はそのまま維持、超過時のみダウンサンプル/ビット深度削減

---

## Scout 固有設定

### vgmdb

```yaml
vgmdb:
  cddb_url: http://vgmdb.net:80/cddb/ja.utf8
  user_cookie: ENV             # 保護されたアクセス用（省略可）
```

### paths

```yaml
paths:
  input: /mnt/work_area
```

### scan

```yaml
scan:
  audio_extensions:
    - .flac
    - .mp3
    - .ogg
    - .wav
    - .m4a
    - .aiff
  soundtrack_keywords:
    - "OST"
    - "Soundtrack"
    - "Sound Track"
    - "Original Sound"
    - "Music Pack"
    - "Digital Soundtrack"
    - "Original Score"
  min_audio_files: 1
```

Notes:
- `audio_extensions`: スキャン対象とする音源ファイルの拡張子リスト
- `soundtrack_keywords`: ACF の `name` フィールドに含まれていればサウンドトラックと判定するキーワード
- `min_audio_files`: サウンドトラックとして認識するための最小ファイル数
- これらの値はコード内のデフォルト定数より **config.yaml の値が優先** される（下記「設定優先順位」参照）

---

## 設定優先順位

各設定値は以下の優先順位で解決されます（上が最優先）。

### 全般

```
CLI 引数 > 環境変数 (.env) > config.yaml > コード内デフォルト値
```

### scan セクション固有

```
config.yaml > コード内デフォルト定数
```

`library_scanner.py` 内の `AUDIO_EXTENSIONS` / `SOUNDTRACK_KEYWORDS` はフォールバック用のデフォルト値として維持されますが、
`config.yaml` の `scan` セクションで値が指定されている場合は **設定ファイルの値を優先** します。

### bucket 設定

`S3_BUCKET` 環境変数が空または未設定の場合、自動的に `sst` をデフォルト値として使用します。

```
環境変数 S3_BUCKET > config.yaml の bucket > デフォルト値 "sst"
```

---

## Scout CLI オプション

```
python main.py [OPTIONS]
```

| オプション | 型 | 説明 |
|-----------|------|------|
| `--steam-library PATH` | str | Steam ライブラリのルートパス（`STEAM_LIBRARY_PATH` 環境変数より優先） |
| `--app-id ID` | int | 指定した AppID のみ処理する |
| `--dry-run` | flag | S3 操作を行わず、何がアップロードされるかをログ出力のみ行う |
| `--no-audio` | flag | ACF マニフェストのみアップロードし、音源ファイルはスキップ |
| `--force` | flag | 未処理チェックをスキップし、既に処理済みの AppID も再処理する |
| `--limit N` | int | 処理する新規サウンドトラックの最大件数（テスト・デバッグ用） |
| `--log-level LEVEL` | str | ログレベル指定（`DEBUG`, `INFO`, `WARNING`, `ERROR`） |
| `--config FILE` | str | config.yaml のパス（デフォルト: `/app/config.yaml`） |
| `--output-json FILE` | str | 実行サマリー JSON を指定ファイルに書き出す |

### --limit の動作仕様

- スキャン（ライブラリ検出）自体には制限をかけず、**アップロード処理の件数のみ** を制限する
- 未処理フィルタリング適用後の対象リストから、先頭 N 件を切り出して処理する
- `--force` と併用した場合は、全検出アプリから先頭 N 件を処理する
- 省略時は全件処理（制限なし）

### --force の動作仕様

- SeaweedFS 上の `ingest/{AppID}/scout_result.json` の存在による未処理チェックをスキップする
- 既にアップロード済みのファイルは上書きされる

---

## ログレベル仕様

ログレベルの優先順位: `CLI (--log-level)` > `環境変数 (LOG_LEVEL)` > デフォルト (`INFO`)

| レベル | 出力内容 |
|--------|---------|
| `DEBUG` | 全スキャン対象の ACF ファイル一覧、スキップ理由詳細、S3 キー生成ログ、各ファイルのサイズ、拡張子分類結果 |
| `INFO` | 検出サウンドトラック一覧、処理開始/完了、アップロード進捗、スキップ件数、最終サマリー |
| `WARNING` | ACF パース失敗、インストールパス未発見、設定値の不整合 |
| `ERROR` | S3 接続失敗、アップロードエラー、致命的な設定不備 |

---

## SeaweedFS ストレージ仕様

### 使用する API

Scout は **S3 互換 API** 経由で SeaweedFS にアクセスします。
S3 API は「ディレクトリ」のオブジェクト概念を持たないため、`put_object` でキーを指定すれば
中間パス（ディレクトリに見えるプレフィックス）は自動的に認識されます。
**明示的なディレクトリ作成は不要** です。

> SeaweedFS の Filer API を使用する場合は空ディレクトリの明示的作成が必要になるケースがありますが、
> 今回は S3 API 経由のため対象外とします。Filer API 対応は将来の検討事項です。

### Ingest ディレクトリ構造

```text
{S3_BUCKET}/
  ingest/
    {AppID}/
      manifest.acf                    ← ACF マニフェストファイル
      scout_result.json               ← スキャン結果メタデータ
      Disc 1/                         ← ディスク階層（無い場合は補完）
        flac/                         ← 拡張子別ディレクトリ
          01 - Track One.flac
          subdir/02 - Track Two.flac  ← サブディレクトリ構造は維持
        mp3/
          01 - Track One.mp3
      Disc 2/
        flac/
          01 - Bonus Track.flac
```

- **基本構造**: `ingest/{AppID}/{Disk No.}/{拡張子}/{ファイル名}`
- **ディスク階層の補完**: 音源ファイルが特定のディスク用ディレクトリに入っていない場合、デフォルトで `Disc 1` が補完されます（メタデータの一貫性のため）。
- **サブディレクトリの維持**: `Disc 1/subdir/flac/file.flac` のように、ディスク階層内の更なるサブディレクトリ構造も保持されます。
- **拡張子ディレクトリの配置**: 拡張子ディレクトリ（`flac/`, `mp3/` 等）は、常にファイル名の直前の親ディレクトリとして配置されます。
- **パス正規化**: 元のフォルダ名が現在の拡張子名と完全に一致する場合（例: `FLAC/01.flac`）、冗長な階層（`FLAC/`）は除去されます。

### 未処理判定

`ingest/{AppID}/scout_result.json` の存在で処理済みかどうかを判定します。
`--force` フラグで上書き再処理が可能です。

### 全フォーマット収集

複数のフォーマットサブディレクトリ（例: `flac/` と `mp3/`）が存在する場合、
**全フォーマットのファイルを全てコピー** します（最優先フォーマットのみの選出は行わない）。