"""
Run once after `docker-compose up -d mongodb` to create the database,
collection, and vector search index.

Usage:
    docker-compose run --rm setup
"""

import os
import time

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo.operations import SearchIndexModel

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/?authSource=admin")
DB_NAME = "health_rag"
COLLECTION_NAME = "documents"
EMBEDDING_DIMENSIONS = 1536


def wait_for_search_service(collection, retries: int = 12, delay: int = 5):
    for attempt in range(1, retries + 1):
        try:
            list(collection.list_search_indexes())
            return
        except OperationFailure as e:
            if "SearchIndexManagementHostUnreachable" in str(e):
                print(f"Search service not ready, retrying ({attempt}/{retries})...")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Search Index Management service never became ready.")


client = MongoClient(MONGO_URI)
db = client[DB_NAME]

if COLLECTION_NAME not in db.list_collection_names():
    db.create_collection(COLLECTION_NAME)
    print(f"Created collection: {COLLECTION_NAME}")
else:
    print(f"Collection already exists: {COLLECTION_NAME}")

collection = db[COLLECTION_NAME]

existing_indexes = [idx["name"] for idx in collection.list_indexes()]
if "url_1" in existing_indexes:
    collection.drop_index("url_1")

collection.create_index("url")
collection.create_index("metadata.source")
collection.create_index("metadata.ingested_at")
print("Created standard indexes")

print("Waiting for Search Index Management service...")
wait_for_search_service(collection)

existing = [idx["name"] for idx in collection.list_search_indexes()]
if "vector_index" not in existing:
    vector_index = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": EMBEDDING_DIMENSIONS,
                    "similarity": "cosine",
                }
            ]
        },
        name="vector_index",
        type="vectorSearch",
    )
    collection.create_search_index(vector_index)
    print("Created vector search index")
else:
    print("Vector search index already exists")

print("Setup complete.")
client.close()
