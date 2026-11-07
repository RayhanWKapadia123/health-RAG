import hashlib
import string
from pathlib import Path
from urllib.parse import urlparse, urldefrag

import scrapy

OUT_DIR = Path("idoh_output")  # relative to where you run the command
HTML_DIR = OUT_DIR / "html"

SKIP_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".jpg", ".png")


"""True if the URL is under in.gov/health/."""
# allowed_domains can't filter by path, so check /health/ manually
def in_health(url):
    p = urlparse(url)
    return p.netloc in ("www.in.gov", "in.gov") and p.path.startswith("/health/")


"""Turns a page URL into a safe filename for its saved HTML."""
# URL path -> flat filename: /health/idepd/measles -> health__idepd__measles.html
def html_filename(url):
    path = urlparse(url).path.strip("/").replace("/", "__") or "index"
    if len(path) > 150:  # Windows path limit; hash keeps long names unique
        path = path[:120] + "_" + hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{path}.html"


"""Crawls IDOH topic pages from the A-Z index, then follows in-body links."""
class IdohHealthSpider(scrapy.Spider):
    name = "idoh_health"
    start_urls = ["https://www.in.gov/health/"]
    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "DEPTH_LIMIT": 4,  # 1 = A-Z topic pages, 2+ = links found inside them
        "FEEDS": {str(OUT_DIR / "pages.jsonl"): {"format": "jsonlines", "overwrite": True}},
    }

    """Entry point: reads the A-Z index and queues every topic link."""
    # #tab_..._X fragments are client-side only; all 26 tabs are in this one HTML response
    def parse(self, response):
        for letter in string.ascii_uppercase:
            for a in response.css(f"#tab_a75ad341f5_{letter} a"):
                yield from self.follow_link(response, a, source="a-z", letter=letter)

    """Saves a page's HTML, yields its metadata/text, and queues its in-body links."""
    def parse_topic(self, response, source, letter=None):
        if not in_health(response.url):  # a /health/ link can redirect elsewhere
            return

        HTML_DIR.mkdir(parents=True, exist_ok=True)
        fname = html_filename(response.url)
        (HTML_DIR / fname).write_bytes(response.body)  # raw bytes, original encoding kept

        main = response.css("main, #main")  # body content only, skips nav/footer
        yield {
            "url": response.url,
            "html_file": f"html/{fname}",
            "found_via": source,  # "a-z" or the page that linked here
            "letter": letter,     # inherited from the A-Z entry that started this branch
            "title": response.css("title::text").get(default="").strip(),
            "text": " ".join(t.strip() for t in main.css("*:not(script):not(style)::text").getall() if t.strip()),
        }

        # recurse into in-body links; Scrapy's dupe filter prevents revisits/loops
        for a in main.css("a[href]"):
            yield from self.follow_link(response, a, source=response.url, letter=letter)

    """Turns an <a> tag into a request if it's a crawlable /health/ page."""
    def follow_link(self, response, a, source, letter=None):
        href = a.attrib.get("href", "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return
        url, _ = urldefrag(response.urljoin(href))  # resolve relative hrefs; drop #anchors so page#x == page
        if not in_health(url) or url.lower().endswith(SKIP_EXT):
            return
        yield scrapy.Request(url, callback=self.parse_topic,
                             cb_kwargs={"source": source, "letter": letter})

