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


def rewrite_query(question: str, history: list[dict]) -> str:
    """Rewrite a follow-up question into a standalone question using chat history."""
    if not history:
        return question

    messages = [
        {
            "role": "system",
            "content": (
                "Given the conversation history and a follow-up question, rewrite the "
                "follow-up question as a single standalone question that includes all "
                "necessary context. Return only the rewritten question, nothing else."
            ),
        }
    ]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({
        "role": "user",
        "content": f"Follow-up question: {question}",
    })

    response = _openai.chat.completions.create(
        model="gpt-5.6-terra",
        messages=messages,
        max_completion_tokens=128,
    )
    return response.choices[0].message.content.strip()


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


def answer(question: str, chunks: list[dict], history: list[dict]) -> str:
    context = "\n\n".join(
        f"Source: {c['url']}\n{c['chunk']}" for c in chunks
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a healthcare assistant. Answer the user's question given the context provided to you. Only talk about information relevant to health in the state of Indiana. \n\n"
                f"Context:\n{context}"
            ),
        }
    ]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    response = _openai.chat.completions.create(
        model="gpt-5.6-terra",
        messages=messages,
    )
    return response.choices[0].message.content


def generate_followups(question: str, answer_text: str) -> list[str]:
    response = _openai.chat.completions.create(
        model="gpt-5.6-terra",
        max_completion_tokens=256,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate follow-up questions for a healthcare data chatbot about Indiana counties. "
                    "Given a question and answer, return exactly 3-4 short follow-up questions the user might ask next. "
                    "If the answer mentions specific counties, organizations, or health programs, include questions about "
                    "contact information, phone numbers, or names of relevant people or agencies when appropriate. "
                    "Return only the questions, one per line, no numbering, no bullets, no extra text."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer_text}"},
        ],
    )
    raw = response.choices[0].message.content.strip()
    return [q.strip() for q in raw.splitlines() if q.strip()][:4]


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
    print(answer(query, chunks, history=[]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py \"your question here\"")
        sys.exit(1)
    ask(" ".join(sys.argv[1:]))
