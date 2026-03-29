### **🛠️ 採用システム・ツール一覧**

| カテゴリ | 採用ツール | 役割・選定理由 |
| :---- | :---- | :---- |
| **オーケストレーション** | **Prefect** | 非同期ジョブの実行管理、ステート監視、リトライ制御. |
| **ストレージ抽象化** | **MinIO** | S3互換APIによる提供。バージョニング機能による「人間の誤操作」からの保護. |
| **Web諜報エージェント** | **browser-use** | AI（LLM）による動的なウェブブラウジングとメタデータ抽出. |
| **メディア処理** | **FFmpeg** | 音声フォーマットの変換（AIFF化）およびリサンプリング. |
| **メタデータ操作** | **Mutagen等** | 各種タグフィールド（COMM, TPE2, TIT1等）への厳格な書き込み. |
| **インフラ基盤** | **Docker** | 実行環境の隔離と、他環境（1台構成等）での再現性確保. |

SST-Scout-VM: Ubuntu Desktop \+ Docker

SST-Core-VM: Ubuntu server \+ Docker \+ USB-HDD-8TB( not mount )

SST-Worker-CT: Ubuntu server \+ Docker \+ USB-SSD-1TB( /mnt/work\_area )

M2 MacBookAir: Ollama \+ mlv