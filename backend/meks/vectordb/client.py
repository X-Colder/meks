from pymilvus import connections, Collection

from meks.config import settings

_connected = False


def init_milvus():
    global _connected
    try:
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
        _connected = True
    except Exception:
        _connected = False


def get_milvus_client():
    if not _connected:
        init_milvus()
    return _connected
