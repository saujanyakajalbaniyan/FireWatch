"""
Cloud storage abstraction for fire events and model artifacts.
Supports local fallback, AWS S3, and Google Cloud Storage.
"""

import json
import os
from datetime import datetime, UTC

try:
    import boto3
except Exception:
    boto3 = None

try:
    from google.cloud import storage as gcs_storage
except Exception:
    gcs_storage = None


class CloudStorageService:
    def __init__(self):
        self.provider = os.getenv("CLOUD_PROVIDER", "local").lower()
        self.bucket = os.getenv("CLOUD_BUCKET", "firewatch-events")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.local_path = os.path.join(os.path.dirname(__file__), "uploads", "cloud_events")
        os.makedirs(self.local_path, exist_ok=True)

        self.s3_client = None
        self.gcs_client = None

        if self.provider == "aws" and boto3:
            self.s3_client = boto3.client("s3", region_name=self.region)
        elif self.provider == "gcp" and gcs_storage:
            self.gcs_client = gcs_storage.Client()

    def status(self):
        return {
            "provider": self.provider,
            "bucket": self.bucket,
            "ready": self._is_ready(),
        }

    def store_event(self, event_type, payload):
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        key = f"events/{event_type}/{ts}.json"
        serialized = json.dumps(payload, ensure_ascii=True, default=str)

        if self.provider == "aws" and self.s3_client:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=serialized.encode("utf-8"),
                ContentType="application/json",
            )
            return {"provider": "aws", "key": key}

        if self.provider == "gcp" and self.gcs_client:
            bucket = self.gcs_client.bucket(self.bucket)
            blob = bucket.blob(key)
            blob.upload_from_string(serialized, content_type="application/json")
            return {"provider": "gcp", "key": key}

        local_file = os.path.join(self.local_path, key.replace("/", "_"))
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(serialized)
        return {"provider": "local", "path": local_file}

    def _is_ready(self):
        if self.provider == "aws":
            return self.s3_client is not None and bool(self.bucket)
        if self.provider == "gcp":
            return self.gcs_client is not None and bool(self.bucket)
        return True
