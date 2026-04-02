"""E2E テスト実行スクリプト。"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# worker モジュールのパスを追加
sys.path.insert(0, str(Path("worker/src").resolve()))

# .env を読み込む
dotenv_path = Path("worker/.env").resolve()
load_dotenv(dotenv_path)

from pipeline.flow import sst_pipeline

TARGET_DIR = Path("work_area/Victory Heat Rally- OST").resolve()
if not TARGET_DIR.exists():
    print(f"Error: Directory not found: {TARGET_DIR}")
    sys.exit(1)

files = [str(f) for f in sorted(TARGET_DIR.glob("*.mp3"))]

print(f"Loaded {len(files)} files.")
print("Running SST Pipeline...")

# app_id = 3183570 is Victory Heat Rally OST on Steam (approximate).
# We'll use 1515220 (base game) to see how it resolves.
result = sst_pipeline(
    app_id=1515220,
    files=files,
    config_path="worker/config.yaml",
    dry_run=True  # 実際のタグ書き込みはスキップ（S3保存・識別は行われる）
)

import json
print("\n[Pipeline Result]")
print(json.dumps(result, indent=2, ensure_ascii=False))
