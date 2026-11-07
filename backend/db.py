import os
from datetime import datetime
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

load_dotenv()

_client = MongoClient(os.getenv("MONGO_URI"))
_collection = _client["health_rag"]["documents"]


def upsert_chunks(url: str, title: str, source: str, chunks: list[str], embeddings: list[list[float]]):
    ops = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        doc = {
            "url": url,
            "chunk": chunk,
            "chunk_index": i,
            "embedding": embedding,
            "metadata": {
                "source": source,
                "title": title,
                "ingested_at": datetime.utcnow().isoformat(),
            },
        }
        ops.append(
            UpdateOne(
                {"url": url, "chunk_index": i},
                {"$set": doc},
                upsert=True,
            )
        )
    if ops:
        _collection.bulk_write(ops)
    return len(ops)
