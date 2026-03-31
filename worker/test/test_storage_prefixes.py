from models import StorageConfig
from pipeline.storage import put_json_for_prefix_name


class DummyS3Client:
    def __init__(self):
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)


def test_put_json_for_prefix_name_uses_workspace_prefix():
    client = DummyS3Client()
    storage = StorageConfig(
        endpoint_url="http://example.local",
        bucket="buckets",
        ingest_prefix="ingest/",
        archive_prefix="archive/",
        review_prefix="review/",
        workspace_prefix="workspace/",
    )

    key = put_json_for_prefix_name(client, storage, "workspace", "run_1", {"ok": True})

    assert key == "workspace/run_1.json"
    assert client.calls[0]["Bucket"] == "buckets"
    assert client.calls[0]["Key"] == "workspace/run_1.json"
