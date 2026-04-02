import json
import os
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from models import StorageConfig


def build_s3_client(storage: StorageConfig):
    return boto3.client(
        "s3",
        endpoint_url=storage.endpoint_url,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
        use_ssl=os.getenv("S3_USE_SSL", "false").lower() == "true",
        config=Config(s3={'addressing_style': 'path'}),
    )


def put_json(
    client,
    storage: StorageConfig,
    prefix: str,
    key_name: str,
    payload: dict[str, Any],
) -> str:
    object_key = f"{prefix.rstrip('/')}/{key_name}.json"
    client.put_object(
        Bucket=storage.bucket,
        Key=object_key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    return object_key


def put_json_for_prefix_name(
    client,
    storage: StorageConfig,
    prefix_name: str,
    key_name: str,
    payload: dict[str, Any],
) -> str:
    prefix_map = {
        "ingest": storage.ingest_prefix,
        "archive": storage.archive_prefix,
        "review": storage.review_prefix,
        "workspace": storage.workspace_prefix,
    }
    if prefix_name not in prefix_map:
        raise ValueError(f"Unknown prefix name: {prefix_name}")
    return put_json(client, storage, prefix_map[prefix_name], key_name, payload)


def check_storage_health(client, storage: StorageConfig) -> None:
    try:
        client.head_bucket(Bucket=storage.bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "403", "400"):
            try:
                client.create_bucket(Bucket=storage.bucket)
            except Exception:
                pass # SeaweedFS often auto-creates buckets anyway or doesn't support CreateBucket fully.
        else:
            raise
