from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from query import embed_query, search, answer

app = FastAPI(title="Health RAG API")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class Source(BaseModel):
    url: str
    title: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]


@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    query_vector = embed_query(request.question)
    chunks = search(query_vector, k=request.top_k)

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant chunks found in the database.")

    return QueryResponse(
        question=request.question,
        answer=answer(request.question, chunks),
        sources=[
            Source(
                url=c["url"],
                title=c.get("metadata", {}).get("title", "Unknown"),
            )
            for c in chunks
        ],
    )


@app.get("/health")
def health():
    return {"status": "ok"}
