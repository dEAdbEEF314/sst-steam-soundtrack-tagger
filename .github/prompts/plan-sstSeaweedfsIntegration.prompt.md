## Plan: SST Worker MVP + SeaweedFS Integration

最初の到達目標は「単一アルバムを手動 AppID 入力で E2E 自動タグ付け」までです。インフラ前提は MinIO ではなく、稼働済み SeaweedFS の S3 互換エンドポイント（http://swfs-s3.outergods.lan）を利用します。実装は Worker 中心で進め、並行して S3 設定を確定し、最後に Prefect 連携を最小構成で検証します。

**Steps**
1. Phase 0: Storage 前提確定（設計のみ、実装準備）
2. SeaweedFS を SST の公式ストレージとして定義し、既存 MinIO 記述を運用上「S3 互換ストレージ」に読み替える方針を確定する。
3. バケット/プレフィックス命名を確定する。最新スクリーンショットに合わせ、バケットは buckets、プレフィックスは ingest/, archive/, review/, workspace/ を正式採用する。
4. 認証情報を確定する。`accessKey` が S3 Access Key に該当するかを確認し、Secret Key とセットで Worker/Core の実行環境へ注入する方法を定義する（.env またはホスト環境変数）。
5. 受け入れ条件を定義する。`put/get/list` が Worker 実行ユーザーで成功し、`review/` 出力が確認できること。
6. Phase 1: Worker コア実装（MVP本体）
7. 音声指紋生成（fpcalc ラッパー）を実装する。
8. MusicBrainz 検索クライアントを実装する。戦略は「全言語検索して統合（ja/en/original）」、MBID で重複排除する。
9. 候補フィルタリングとスコアリングを実装する（フォーマット、曲数、発売日、タイトル類似度）。
10. AcoustID 検証を実装する。最初の3曲で部分検証し、失敗時は自動で全曲フォールバックする。
11. タグ書き込みを実装する（ID3v2.3、メタデータ正規化、既存タグ上書き方針を明示）。
12. Pipeline エントリポイントを実装する（入力: AppID + ローカルディレクトリ、出力: 処理結果 JSON）。
13. Phase 2: SeaweedFS I/O 統合（Phase 1 と一部並行可）
14. S3 クライアント（boto3）設定層を実装し、endpoint URL を `http://swfs-s3.outergods.lan` に切替可能にする。
15. 成果物アップロードを実装する。成功時は archive/ と結果 JSON、要レビュー時は review/ に配置する。入力原本は ingest/、作業中一時データは workspace/ を利用する。
16. キャッシュ読み書きの最小実装を入れる（少なくとも同一入力の再処理抑止キーを設計）。
17. Phase 3: オーケストレーション最小統合
18. Prefect Flow に Worker 実行タスクを最小接続する（単一アルバム処理）。
19. リトライと状態遷移を仕様準拠で実装する（外部 API エラー時の backoff、最終 review 振り分け）。
20. Phase 4: テストと受け入れ
21. pytest 基盤を作成し、MusicBrainz クライアント、Scoring、AcoustID 判定、Tagging のユニットテストを実装する。
22. 31ファイルの実データで E2E テストを実行し、成功率・処理時間・フォールバック率を記録する。
23. SeaweedFS への成果物配置（ingest/archive/review/workspace）を検証し、MVP 完了判定を行う。

**Relevant files**
- `e:/AI_Base/WorkSpace/SST_Project/worker/src/` — Worker 各モジュールの新規実装（acoustid, fingerprint, musicbrainz, scoring, tagging, pipeline, models）
- `e:/AI_Base/WorkSpace/SST_Project/worker/requirements.txt` — 依存の追加/整理（pytest、必要クライアント）
- `e:/AI_Base/WorkSpace/SST_Project/worker/.env` — MinIO 名義の変数を S3 互換向けに整理（命名統一）
- `e:/AI_Base/WorkSpace/SST_Project/worker/config.yaml` — SeaweedFS endpoint と buckets + ingest/archive/review/workspace を設定
- `e:/AI_Base/WorkSpace/SST_Project/core/docker-compose.yml` — Prefect 側の接続情報確認
- `e:/AI_Base/WorkSpace/SST_Project/docs/CONFIG_SPEC.md` — ストレージ設定を S3 互換前提へ更新
- `e:/AI_Base/WorkSpace/SST_Project/docs/ARCHITECTURE.md` — MinIO 固有記述を SeaweedFS/S3 互換へ更新
- `e:/AI_Base/WorkSpace/SST_Project/docs/DATA_FLOW.md` — 保存先説明を SeaweedFS に更新
- `e:/AI_Base/WorkSpace/SST_Project/docs/TASKS.md` — Phase 0 タスクを MinIO 構築から SeaweedFS 接続確定へ更新

**Verification**
1. SeaweedFS 接続確認: Worker 実行環境から S3 `ListBuckets`, `PutObject`, `GetObject` を実行し成功すること。
2. Unit test: `pytest` で各モジュールの正常系・異常系を実行し、主要分岐を通すこと。
3. E2E test: 31トラックの1アルバムで AppID 手動入力実行し、タグ更新と結果 JSON 出力を確認すること。
4. Fallback test: 部分検証を意図的に失敗させ、全曲 AcoustID へ自動遷移すること。
5. Storage path test: ingest/, archive/, review/, workspace/ に期待どおりオブジェクトが保存されること。

**Decisions**
- MinIO は採用しない。SeaweedFS の S3 互換 API を使用する。
- 最初のマイルストーンは Scout を含めない（手動 AppID 入力）。
- MusicBrainz は全言語検索統合、部分検証失敗時は全曲フォールバック。
- テストフレームワークは pytest。

**Further Considerations**
1. buckets をバケット名として固定し、ingest/archive/review/workspace をプレフィックスとして運用する。
2. S3 認証情報の命名を `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_ENDPOINT_URL` に統一し、将来のベンダ切替を容易にする。
3. SeaweedFS 側でバージョニングやライフサイクルを使う場合は、MVP後の運用フェーズで有効化する。
