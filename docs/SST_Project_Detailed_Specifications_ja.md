# SST（Steam Soundtrack Tagger）詳細仕様書（日本語版）

---

# 1. 概要

SSTは、**Steamで購入したサウンドトラック専用**のメタデータ補完・正規化パイプラインである。

以下の複合戦略により、音源を高精度に識別・タグ付けする：

* Steamメタデータ
* MusicBrainz検索（多言語マージ戦略）
* AcoustID（部分検証＋フォールバック）

---

# 2. 対象範囲

## 対象

* Steamで購入したサウンドトラック
* メタデータが不完全または不正確な音源

## 非対象

* ストリーミング音源
* 非Steam由来の音源
* ライブ録音・ユーザー編集音源

---

# 3. 全体パイプライン

```text
音源入力
 ↓
 Steamメタデータ取得
  ↓
  MusicBrainzでアルバム候補検索
   ↓
   候補フィルタリング＆スコアリング
    ↓
    アルバム確定
     ↓
     AcoustID部分検証（3曲）
      ↓
      （必要時）フルAcoustID
       ↓
       メタデータ補完
        ↓
        タグ書き込み
         ↓
         MinIO保存
          ↓
          レビュー（必要時）
          ```

          ---

# 4. 入力要件

## 必須

* Steam AppID
* 同一アルバムの音源ファイル群

## 派生情報

* トラック数
* 再生時間
* フィンガープリント

---

# 5. Steamメタデータ取得

## 取得項目

* タイトル（ローカライズ済）
* リリース日

## 注意

* 年のみの場合あり
* MusicBrainzと表記揺れあり

---

# 6. MusicBrainz検索戦略

## 基本方針

複数言語で検索し、結果を統合する

---

## 設定

```yaml
search:
  languages:
      - ja
          - en
              - original
                strategy: merge
                ```

                ---

## クエリ構築

```
(
  release:"日本語タイトル"^3 OR
    release:"英語タイトル"^2 OR
      release:"原語タイトル"
      )
AND format:digital
AND date:[YYYY-01-01 TO YYYY-12-31]
```

---

## 処理

* 全結果をマージ
* MBIDで重複除去
* 上位N件に制限

---

# 7. アルバム候補フィルタ

```yaml
album_match:
  track_count_tolerance: 1
    date_tolerance_days: 30
    ```

    ---

## 条件

* フォーマット：Digital Media
* トラック数一致（±許容）
* リリース日一致（±許容）

---

# 8. スコアリング

```
score =
  タイトル類似度
    + トラック数一致
      + 日付一致
        + フォーマット一致
        ```

        ---

## 判定閾値

```yaml
search:
  accept_threshold: 2.5
  ```

  ---

# 9. アルバム確定

* 最高スコアを採用
* 閾値以上 → 確定
* 未満 → AcoustIDへ

---

# 10. AcoustID部分検証

## 設定

```yaml
acoustid:
  partial_verify_tracks: 3
    partial_match_threshold: 0.8
    ```

    ---

## 処理

* 先頭3曲で検証
* 一致率判定

---

## 判定

* 80%以上一致 → 採用
* 未満 → フル検証

---

# 11. フルAcoustID（フォールバック）

* 全曲フィンガープリント
* 個別マッチング
* アルバム再構築

---

# 12. メタデータ補完

## ソース

* MusicBrainz
* Cover Art Archive

---

## 項目

* アルバム名
* 曲名
* アーティスト
* トラック番号
* 発売日
* ジャケット

---

# 13. タグ書き込み

## 仕様

* ID3v2.3（厳格）

---

# 14. ストレージ

MinIO（S3互換）

```
bucket/
 ├─ processed/
  ├─ review/
   └─ logs/
   ```

   ---

# 15. レビュー

## 条件

* 低信頼度
* 結果衝突

---

# 16. キャッシュ戦略

* 成功結果保存
* confidence ≥ 0.95のみ再利用
* manual_verified最優先

---

# 17. 状態管理

```
INGESTED
FINGERPRINTED
IDENTIFIED
ENRICHED
TAGGED
STORED
FAILED
```

---

# 18. ログ

* job_id
* track_id
* step
* result
* error

---

# 19. 設計思想

* 誤認識を最小化
* 再現性重視
* 人間補正前提
* キャッシュで進化

---

# 20. 本質

SSTは単なるタグツールではない。

👉 **音楽メタデータを解決するためのインフラである**

---

# END

