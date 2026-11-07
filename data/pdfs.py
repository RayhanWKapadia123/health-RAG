"""
Finds PDFs linked from already-scraped IDOH pages, downloads them, and extracts their text.

Run:  pip install beautifulsoup4 lxml requests pymupdf
      python pdfs.py                 # uses idoh_output/ from scrape.py
      python pdfs.py --links-only    # just build the PDF inventory, no downloads

Output (in idoh_output/):
  pdf_links.jsonl      every unique PDF + which pages link to it
  other_files.jsonl    .docx/.xlsx/etc. links, recorded for later
  pdfs/                downloaded PDFs
  pdf_clean/           one .md per PDF + pdf_clean.jsonl
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

OUT_DIR = Path("idoh_output")
HTML_DIR = OUT_DIR / "html"
PDF_DIR = OUT_DIR / "pdfs"
CLEAN_DIR = OUT_DIR / "pdf_clean"

OTHER_DOC_EXT = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv")
DELAY = 1  # seconds between downloads; be polite to a state site
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; idoh-research-scraper)"}


def load_page_urls():
    """Maps saved HTML filename -> original page URL, using scrape.py's pages.jsonl."""
    mapping = {}
    jsonl = OUT_DIR / "pages.jsonl"
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("html_file"):
                    mapping[Path(row["html_file"]).name] = row["url"]
    return mapping


def guess_page_url(fname):
    """Fallback when pages.jsonl is missing: health__idepd__x.html -> https://www.in.gov/health/idepd/x"""
    return "https://www.in.gov/" + Path(fname).stem.replace("__", "/")


def is_in_gov(url):
    """Any in.gov host. PDFs often live at in.gov/dA/..., outside /health/, so no path filter."""
    host = urlparse(url).netloc.lower()
    return host == "in.gov" or host.endswith(".in.gov")


def collect_links():
    """Scans saved HTML for document links in page content; returns {pdf_url: info}, {other_url: info}."""
    page_urls = load_page_urls()
    pdfs, others = {}, {}

    files = sorted(HTML_DIR.glob("*.html"))
    for f in files:
        page_url = page_urls.get(f.name) or guess_page_url(f.name)
        soup = BeautifulSoup(f.read_bytes(), "lxml")
        root = soup.select_one("main article") or soup.select_one("main") or soup.body  # skip footer docs
        if root is None:
            continue

        for a in root.select("a[href]"):
            url, _ = urldefrag(urljoin(page_url, a["href"].strip()))
            url = url.replace("http://", "https://", 1)
            if not is_in_gov(url):
                continue
            path = urlparse(url).path.lower()  # path, not URL: "x.pdf?language_id=1" is still a PDF
            if path.endswith(".pdf"):
                bucket = pdfs
            elif path.endswith(OTHER_DOC_EXT):
                bucket = others
            else:
                continue

            info = bucket.setdefault(url, {"url": url, "link_texts": [], "source_pages": []})
            text = a.get_text(" ", strip=True)
            if text and text not in info["link_texts"]:
                info["link_texts"].append(text)
            if page_url not in info["source_pages"]:
                info["source_pages"].append(page_url)  # provenance for RAG citations

    print(f"Scanned {len(files)} pages: {len(pdfs)} unique PDFs, {len(others)} other docs")
    return pdfs, others


def pdf_filename(url):
    """Readable, unique filename: last path segment + short hash of the full URL."""
    stem = Path(unquote(urlparse(url).path)).stem  # %20 -> space before sanitizing
    stem = re.sub(r"[^\w\-]+", "_", stem)[:80] or "file"  # Windows-safe
    return f"{stem}_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"


def download(url, dest):
    """Downloads one PDF; skips if already on disk so reruns resume where they left off."""
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):  # catches HTML error pages served with a .pdf URL
        raise ValueError(f"not a PDF (content-type: {r.headers.get('content-type')})")
    dest.write_bytes(r.content)
    time.sleep(DELAY)
    return "downloaded"


def extract_text(path):
    """Extracts text page by page with PyMuPDF; returns (text, page_count)."""
    import pymupdf

    with pymupdf.open(path) as doc:
        pages = [p.get_text("text").strip() for p in doc]
    text = "\n\n".join(f"<!-- page {i} -->\n{t}" for i, t in enumerate(pages, 1) if t)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), len(pages)


def main():
    """Builds the link inventory, then downloads and extracts every PDF."""
    if not HTML_DIR.exists():
        sys.exit(f"{HTML_DIR} not found; run scrape.py first (or run this from the folder containing idoh_output/)")

    pdfs, others = collect_links()

    with open(OUT_DIR / "pdf_links.jsonl", "w", encoding="utf-8") as f:
        for info in pdfs.values():
            f.write(json.dumps(info, ensure_ascii=False) + "\n")
    with open(OUT_DIR / "other_files.jsonl", "w", encoding="utf-8") as f:
        for info in others.values():
            f.write(json.dumps(info, ensure_ascii=False) + "\n")

    if "--links-only" in sys.argv:
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"ok": 0, "empty": 0, "failed": 0}

    with open(CLEAN_DIR / "pdf_clean.jsonl", "w", encoding="utf-8") as jf:
        for i, (url, info) in enumerate(pdfs.items(), 1):
            fname = pdf_filename(url)
            dest = PDF_DIR / fname
            try:
                status = download(url, dest)
                text, n_pages = extract_text(dest)
            except Exception as e:  # one bad PDF shouldn't stop the run
                stats["failed"] += 1
                print(f"[{i}/{len(pdfs)}] FAILED {url}: {e}")
                continue

            empty = not text  # usually a scanned PDF with no text layer; needs OCR
            stats["empty" if empty else "ok"] += 1
            title = info["link_texts"][0] if info["link_texts"] else Path(urlparse(url).path).stem
            print(f"[{i}/{len(pdfs)}] {status}{' (NO TEXT)' if empty else ''}: {title}")

            row = {**info, "title": title, "pdf_file": f"pdfs/{fname}", "pages": n_pages, "empty": empty, "text": text}
            jf.write(json.dumps(row, ensure_ascii=False) + "\n")

            md = f"# {title}\n\n*Source: {url}*\n\n*Linked from: {', '.join(info['source_pages'])}*\n\n{text}\n"
            (CLEAN_DIR / f"{Path(fname).stem}.md").write_text(md, encoding="utf-8")

    print(f"Done. {stats['ok']} extracted, {stats['empty']} empty (likely scanned), {stats['failed']} failed")


if __name__ == "__main__":
    main()