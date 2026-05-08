from __future__ import annotations

import asyncio
import os
import tempfile
import time
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from src.app.settings import Settings


class S3Storage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )
        self._bucket_checked = False

    def _ensure_bucket_sync(self) -> None:
        if self._bucket_checked:
            return
        bucket = self.settings.s3_bucket
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError:
            # Create if missing. For S3-compatible endpoints, CreateBucket usually works without LocationConstraint.
            try:
                self._client.create_bucket(Bucket=bucket)
            except ClientError as e:
                code = (e.response or {}).get("Error", {}).get("Code", "")
                # Concurrent creators (multi workers) may race; treat "already exists/owned" as success.
                if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise

            # Some S3 implementations may need a short propagation window; wait until head succeeds.
            for _ in range(100):
                try:
                    self._client.head_bucket(Bucket=bucket)
                    break
                except ClientError:
                    time.sleep(0.1)
        self._bucket_checked = True

    async def write_upload_to_temp(self, upload_file, hasher) -> str:
        fd, path = tempfile.mkstemp(prefix="audit-upload-", suffix=".bin")
        os.close(fd)

        def _copy() -> None:
            with open(path, "wb") as out:
                while True:
                    chunk = upload_file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    out.write(chunk)

        await asyncio.to_thread(_copy)
        return path

    async def remove_temp(self, path: str) -> None:
        await asyncio.to_thread(lambda: os.remove(path))

    async def put_file(self, *, key: str, fileobj: BinaryIO, content_type: str) -> None:
        def _upload() -> None:
            self._ensure_bucket_sync()
            self._client.upload_fileobj(
                Fileobj=fileobj,
                Bucket=self.settings.s3_bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type or "application/octet-stream"},
            )

        await asyncio.to_thread(_upload)

    async def put_path(self, *, key: str, path: str, content_type: str) -> None:
        def _upload() -> None:
            self._ensure_bucket_sync()
            with open(path, "rb") as f:
                self._client.upload_fileobj(
                    Fileobj=f,
                    Bucket=self.settings.s3_bucket,
                    Key=key,
                    ExtraArgs={
                        "ContentType": content_type or "application/octet-stream"
                    },
                )

        await asyncio.to_thread(_upload)

    async def download_to_path(self, *, bucket: str, key: str, dest_path: str) -> None:
        """Download object from bucket/key to local dest_path (blocking in thread)."""

        def _download() -> None:
            self._ensure_bucket_sync()
            # download_file will create/overwrite dest_path
            self._client.download_file(Bucket=bucket, Key=key, Filename=dest_path)

        await asyncio.to_thread(_download)

    async def download_fileobj(self, *, bucket: str, key: str):
        """Return a file-like object (BytesIO) with the object content."""
        import io

        buf = io.BytesIO()

        def _download() -> None:
            self._ensure_bucket_sync()
            self._client.download_fileobj(Bucket=bucket, Key=key, Fileobj=buf)

        await asyncio.to_thread(_download)
        buf.seek(0)
        return buf
