from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from query import embed_query, rewrite_query, search, answer, generate_followups

app = FastAPI(title="Health RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    question: str
    history: list[Message] = []
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
    history = [m.model_dump() for m in request.history]

    standalone = rewrite_query(request.question, history)

    query_vector = embed_query(standalone)
    chunks = search(query_vector, k=request.top_k)

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant chunks found in the database.")

    return QueryResponse(
        question=request.question,
        answer=answer(request.question, chunks, history),
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


class FollowupRequest(BaseModel):
    question: str
    answer: str


class FollowupResponse(BaseModel):
    followups: list[str]


@app.post("/followups", response_model=FollowupResponse)
def followups(request: FollowupRequest):
    return FollowupResponse(followups=generate_followups(request.question, request.answer))
