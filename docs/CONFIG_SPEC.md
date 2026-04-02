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