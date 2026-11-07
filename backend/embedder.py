import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "text-embedding-3-small"


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    response = _client.embeddings.create(input=chunks, model=MODEL)
    return [item.embedding for item in response.data]
