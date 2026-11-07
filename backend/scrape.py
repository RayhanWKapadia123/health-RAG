import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from chunker import chunk_text
from embedder import embed_chunks
from db import upsert_chunks


def scrape(url: str) -> tuple[str, str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; health-RAG/1.0)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else url

    parts = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = tag.get_text(separator=" ", strip=True)
        if len(text) > 30:
            parts.append(text)

    return title, " ".join(parts)


def ingest(url: str):
    print(f"Scraping: {url}")
    title, text = scrape(url)

    if not text:
        print("No content found.")
        return

    print(f"Chunking text ({len(text)} chars)...")
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    print("Embedding chunks...")
    embeddings = embed_chunks(chunks)

    source = urlparse(url).netloc
    count = upsert_chunks(url, title, source, chunks, embeddings)
    print(f"Stored {count} chunks from: {url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape.py <url>")
        sys.exit(1)
    ingest(sys.argv[1])
