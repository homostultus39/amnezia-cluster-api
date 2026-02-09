from minio import Minio
from urllib.parse import urlparse

from src.management.settings import get_settings

settings = get_settings()

_minio_client: Minio | None = None
_minio_public_client: Minio | None = None


def get_minio_client() -> Minio:
    """Get MinIO client for internal operations (upload, delete, etc.)"""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.minio_internal_host,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _minio_client


def get_minio_public_client() -> Minio:
    """Get MinIO client with public host for generating presigned URLs"""
    global _minio_public_client
    if _minio_public_client is None:
        # Parse public host to extract host:port and scheme
        parsed = urlparse(settings.minio_public_host if '://' in settings.minio_public_host
                         else f'http://{settings.minio_public_host}')

        # Determine if secure based on scheme
        is_secure = parsed.scheme == 'https'

        # Get host:port
        public_endpoint = parsed.netloc

        _minio_public_client = Minio(
            public_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=is_secure,
        )
    return _minio_public_client
