import os
import sys
from pathlib import Path

from chunker import chunk_text
from embedder import embed_chunks
from db import upsert_chunks

DATA_DIR = Path("/data/health_data_zip")


def ingest_file(path: Path):
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"  Skipping empty file: {path.name}")
        return 0

    lines = content.splitlines()
    url = ""
    if lines and lines[0].startswith("Source:"):
        url = lines[0].removeprefix("Source:").strip()
        text = "\n".join(lines[1:]).strip()
    else:
        text = content

    if not url:
        url = f"file://{path.name}"

    title = path.stem.replace("__", " > ").replace("_", " ")

    chunks = chunk_text(text)
    if not chunks:
        print(f"  Skipping (no text after chunking): {path.name}")
        return 0

    embeddings = embed_chunks(chunks)
    count = upsert_chunks(url, title, "health_data_zip", chunks, embeddings)
    return count


def main():
    md_files = sorted(DATA_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {DATA_DIR}")
        sys.exit(1)

    total = 0
    for i, path in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] {path.name}")
        count = ingest_file(path)
        print(f"  -> {count} chunks stored")
        total += count

    print(f"\nDone. {total} total chunks stored from {len(md_files)} files.")


if __name__ == "__main__":
    main()
