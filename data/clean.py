"""
Cleans saved IDOH HTML pages into markdown: keeps page content, drops nav/footer/social/translate.

Run:  pip install beautifulsoup4 lxml
      python clean.py                          # idoh_output/html -> idoh_output/clean
      python clean.py path/to/html path/to/out
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString

BASE_URL = "https://www.in.gov"
DROP_TAGS = ["script", "style", "noscript", "svg", "form", "button", "iframe"]


def clean_page(html):
    """Extracts title, breadcrumbs, and content (as markdown) from one IDOH page."""
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("h1.info-heading")
    title = title_el.get_text(strip=True) if title_el else (soup.title.get_text(strip=True) if soup.title else "")

    # breadcrumbs = useful hierarchy metadata (e.g. Health > CSHCR > Acute and Continuing Care)
    crumbs = [c.get_text(" ", strip=True) for c in soup.select("#breadcrumbs li")]
    crumbs = [c for c in crumbs if c]

    # <main> also wraps the footer, so scope to <article>; fall back to main if missing
    root = soup.select_one("main article") or soup.select_one("main") or soup.body
    if root is None:
        return {"title": title, "breadcrumbs": crumbs, "content": ""}

    for el in root.select(", ".join(DROP_TAGS)):
        el.decompose()
    for el in root.select(".info-internal-banner, .breadcrumbs, .prefooter"):
        el.decompose()  # title/breadcrumbs already captured above

    content = to_markdown(root)
    content = re.sub(r"[ \t]+\n", "\n", content)          # strip trailing spaces
    content = re.sub(r"\n{3,}", "\n\n", content).strip()  # collapse blank-line runs
    return {"title": title, "breadcrumbs": crumbs, "content": content}


def to_markdown(node):
    """Recursively converts HTML to markdown, keeping headings, lists, tables, and links."""
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))

    name = node.name
    inner = "".join(to_markdown(c) for c in node.children)

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        text = re.sub(r"[*\s]+", " ", inner).strip()  # headings are often wrapped in <strong>
        return f"\n\n{'#' * int(name[1])} {text}\n\n" if text else ""
    if name == "p":
        return f"\n\n{inner.strip()}\n\n" if inner.strip() else ""
    if name == "br":
        return "\n"
    if name in ("strong", "b"):
        return f"**{inner.strip()}**" if inner.strip() else ""
    if name in ("em", "i"):
        return f"*{inner.strip()}*" if inner.strip() else ""
    if name == "a":
        return link(node, inner)
    if name in ("ul", "ol"):
        items = []
        for i, li in enumerate(node.find_all("li", recursive=False), 1):
            bullet = f"{i}." if name == "ol" else "-"
            items.append(f"{bullet} {to_markdown(li).strip()}")
        return "\n\n" + "\n".join(items) + "\n\n"
    if name == "table":
        return "\n\n" + table(node) + "\n\n"
    if name == "img":
        alt = node.get("alt", "").strip()
        return f"[image: {alt}]" if alt else ""
    return inner


def link(a, inner):
    """Keeps link targets (forms, docs, phone/email) so contact info survives."""
    text = inner.strip()
    href = (a.get("href") or "").strip()
    if not text:
        return ""
    if not href or href.startswith(("#", "javascript:")):
        return text
    if href.startswith("tel:") or href.startswith("mailto:"):
        target = href.split(":", 1)[1]
        return text if target in text else f"{text} ({target})"
    return f"[{text}]({urljoin(BASE_URL, href)})"


def table(t):
    """Converts a table to markdown rows (first row treated as header)."""
    rows = []
    for tr in t.find_all("tr"):
        cells = [to_markdown(c).strip().replace("\n", " ").replace("|", "\\|") for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    ncols = rows[0].count("|") - 1
    rows.insert(1, "|" + " --- |" * ncols)
    return "\n".join(rows)


def load_page_urls(jsonl):
    """Maps saved HTML filename -> original page URL, using scrape.py's pages.jsonl."""
    mapping = {}
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("html_file"):
                    mapping[Path(row["html_file"]).name] = row["url"]
    return mapping


def guess_page_url(fname):
    """Fallback if pages.jsonl is missing: health__idepd__x.html -> https://www.in.gov/health/idepd/x"""
    return f"{BASE_URL}/" + Path(fname).stem.replace("__", "/")


def main():
    """Cleans every .html in the input dir; writes one .md per page plus a combined JSONL."""
    in_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("idoh_output/html")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("idoh_output/new_clean")
    out_dir.mkdir(parents=True, exist_ok=True)

    page_urls = load_page_urls(in_dir.parent / "pages.jsonl")
    files = sorted(in_dir.glob("*.html"))
    with open(out_dir / "clean.jsonl", "w", encoding="utf-8") as jf:
        for f in files:
            page = {"url": page_urls.get(f.name) or guess_page_url(f.name), **clean_page(f.read_bytes())}
            page["source_file"] = f.name

            md = f"Source: {page['url']}\n\n# {page['title']}\n\n"
            if page["breadcrumbs"]:
                md += f"*{' > '.join(page['breadcrumbs'])}*\n\n"
            md += page["content"] + "\n"
            (out_dir / f"{f.stem}.md").write_text(md, encoding="utf-8")
            jf.write(json.dumps(page, ensure_ascii=False) + "\n")

    print(f"Cleaned {len(files)} pages -> {out_dir}")


if __name__ == "__main__":
    main()