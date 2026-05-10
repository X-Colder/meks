import uuid

from fastapi import UploadFile
from minio import Minio

from meks.config import settings

_client: Minio | None = None


def init_minio():
    global _client
    _client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    if not _client.bucket_exists(settings.minio_bucket):
        _client.make_bucket(settings.minio_bucket)


def get_minio_client() -> Minio:
    if _client is None:
        init_minio()
    return _client


async def upload_file(file: UploadFile, kb_id: str) -> str:
    client = get_minio_client()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "bin"
    object_name = f"{kb_id}/{uuid.uuid4().hex}.{ext}"

    content = await file.read()
    from io import BytesIO

    client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(content),
        length=len(content),
        content_type=file.content_type or "application/octet-stream",
    )
    await file.seek(0)
    return object_name


def download_file(storage_path: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, storage_path)
    data = response.read()
    response.close()
    response.release_conn()
    return data
