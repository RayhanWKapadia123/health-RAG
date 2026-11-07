import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

load_dotenv()

_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_collection = MongoClient(os.getenv("MONGO_URI"))["health_rag"]["documents"]

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5


def embed_query(query: str) -> list[float]:
    response = _openai.embeddings.create(input=[query], model=EMBED_MODEL)
    return response.data[0].embedding


def search(query_vector: list[float], k: int = TOP_K) -> list[dict]:
    return list(_collection.aggregate([
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": k * 10,
                "limit": k,
            }
        },
        {
            "$project": {
                "chunk": 1,
                "url": 1,
                "metadata.title": 1,
                "_id": 0,
            }
        },
    ]))


def answer(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"Source: {c['url']}\n{c['chunk']}" for c in chunks
    )
    response = _openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer the user's question "
                    "using only the context provided. If the answer is not in "
                    "the context, say so."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ],
    )
    return response.choices[0].message.content


def ask(query: str):
    print(f"\nQuestion: {query}\n")
    print("Searching database...")
    query_vector = embed_query(query)
    chunks = search(query_vector)

    if not chunks:
        print("No relevant chunks found in the database.")
        return

    print(f"Found {len(chunks)} relevant chunks:\n")
    for i, c in enumerate(chunks, 1):
        print(f"  [{i}] {c.get('metadata', {}).get('title', 'Unknown')} — {c['url']}")

    print("\nGenerating answer...\n")
    print(answer(query, chunks))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py \"your question here\"")
        sys.exit(1)
    ask(" ".join(sys.argv[1:]))
