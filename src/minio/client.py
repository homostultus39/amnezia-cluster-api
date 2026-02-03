import asyncio
import io
from datetime import timedelta
from typing import Optional

from minio.error import S3Error

from src.management.settings import get_settings
from src.minio.connection import get_minio_client

settings = get_settings()


class MinioClient:
    def __init__(self) -> None:
        self._client = get_minio_client()
        self._bucket_ready = False
        self.bucket_name = settings.minio_bucket

    async def _run(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        exists = await self._run(self._client.bucket_exists, self.bucket_name)
        if not exists:
            await self._run(self._client.make_bucket, self.bucket_name)
        self._bucket_ready = True

    async def upload_text(
        self,
        object_name: str,
        content: str,
        content_type: str = "text/plain",
    ) -> None:
        await self._ensure_bucket()
        data = content.encode()
        await self._run(
            self._client.put_object,
            self.bucket_name,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def upload_bytes(
        self,
        object_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        await self._ensure_bucket()
        await self._run(
            self._client.put_object,
            self.bucket_name,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

    async def delete_object(self, object_name: str) -> None:
        await self._ensure_bucket()
        await self._run(self._client.remove_object, self.bucket_name, object_name)

    async def presigned_get_url(
        self,
        object_name: str,
        expires_seconds: Optional[int] = None,
    ) -> str:
        await self._ensure_bucket()
        expires = timedelta(
            seconds=expires_seconds or settings.minio_presigned_expires_seconds
        )
        return await self._run(
            self._client.presigned_get_object,
            self.bucket_name,
            object_name,
            expires=expires,
        )

    async def is_available(self) -> bool:
        try:
            await self._ensure_bucket()
        except S3Error:
            return False
        return True


