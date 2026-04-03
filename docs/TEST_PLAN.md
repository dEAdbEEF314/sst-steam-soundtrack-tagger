# TEST_PLAN

---

## 1. Worker Unit Tests

`worker/test/` で pytest を実行。各ファイルが以下を検証する。

### test_flow_resolution.py
- `select_best_candidate` が `final_score` の最大値を正しく選択する
- `select_best_candidate` が空リストで `None` を返す
- `_to_scored_candidates` が fallback_title に基づく類似ボーナスを正しく加算する
- `refine_candidates_with_fallback_title` が新候補を追加して再スコアする
- `refine_candidates_with_fallback_title` が検索エラー時に既存候補を保持する

### test_config_and_scoring.py
- `load_config` が config.yaml から retry / acoustid / storage 設定を正しく読み込む
- `score_candidates` がトラック数 & リリース日の近さで候補を優先順位付けする

### test_fallback_confidence.py
- `full_acoustid_fallback` がファイルなしで `no_files` 理由を返す
- `full_acoustid_fallback` が resolved=True のとき match_ratio を含む

### test_storage_prefixes.py
- `put_json_for_prefix_name` が workspace プレフィックスで正しいキーに PUT する

### test_tagging_convert.py
- FLAC → AIFF 変換で ffmpeg が呼ばれる
- WAV → AIFF 変換でビット深度 16 → `pcm_s16be` コーデックを選択する
- 96kHz/32bit ソースが max_sample_rate=48000/max_bit_depth=24 に変換される

### test_tagging_id3.py
- MP3 ファイルに track_number/total_tracks を含む TRCK タグが書き込まれる

---

## 2. Scout Unit Tests

`scout/test/` で pytest を実行。

### test_acf_parser.py
- ACF をパースして dict を返す
- `appid`, `name`, `StateFlags`, `installdir` を正しく取得する
- `is_installed` が StateFlags に基づき判定する

### test_library_scanner.py
- `_is_soundtrack_name` が OST/Soundtrack 等のキーワードを検出する
- `_find_audio_files` が音源ファイルのみ返し、非音源を除外する
- `_find_audio_files` がサブディレクトリを再帰的に取得する
- `_find_audio_files` がソートされたリストを返す
- 空ディレクトリで空リストを返す

### test_uploader.py
- dry-run 時に S3 操作が発生しない
- dry-run で `UploadResult` が返る
- ACF キーが `ingest/{app_id}/manifest.acf` 形式になる
- 音源ファイルキーが `ingest/{app_id}/Disc 1/{ext}/` 形式になる
- scout_result.json キーが `ingest/{app_id}/scout_result.json` になる

---

## 3. E2E / Integration Test Scenarios

以下の 3 シナリオで手動または自動検証を行う。

| シナリオ | 内容 |
|--------|------|
| known correct | トラック数・リリース日が MusicBrainz と一致する既知アルバム |
| ambiguous | 複数候補が接近スコアになるアルバム（fallback 動作の検証） |
| failure | AcoustID 一致率が低く review/ へ送られるケース |

---

## 4. E2E 受入基準

- 少なくとも 90% のトラックが正しく識別される（SUCCESS_CRITERIA.md 準拠）
- review/ への振り分けが失敗・低信頼ケースに対して正しく行われる
- structured log に job_id, track_id, step, result, error が含まれる
