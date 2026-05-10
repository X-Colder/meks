from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    utility,
)

EMBEDDING_DIM = 1024


def get_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="knowledge_base_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
    ]
    return CollectionSchema(fields=fields, description="Medical paper chunks")


def create_collection(collection_name: str) -> Collection:
    schema = get_schema()
    collection = Collection(name=collection_name, schema=schema)
    collection.create_index(
        field_name="embedding",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024},
        },
    )
    return collection


def drop_collection(collection_name: str):
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
