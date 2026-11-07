import tiktoken

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_enc = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str) -> list[str]:
    tokens = _enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + CHUNK_SIZE
        chunk_tokens = tokens[start:end]
        chunks.append(_enc.decode(chunk_tokens))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]
