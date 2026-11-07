"""
Small test crawl of in.gov/health/ A-Z topics + in-body links.

Run:  pip install scrapy
      python test_idoh.py            # defaults: letters A,B ; depth 1 ; max 25 pages
      python test_idoh.py ABC 2 50   # letters, depth limit, max pages

Output: test_output.jsonl
"""
import string
import sys
from urllib.parse import urlparse, urldefrag

import scrapy
from scrapy.crawler import CrawlerProcess

TAB_ID = "tab_a75ad341f5"
SKIP_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".jpg", ".jpeg", ".png", ".gif")


def in_health(url):
    p = urlparse(url)
    return p.netloc in ("www.in.gov", "in.gov") and p.path.startswith("/health/")


class IdohTestSpider(scrapy.Spider):
    name = "idoh_test"
    start_urls = ["https://www.in.gov/health/"]

    def __init__(self, letters="AB", **kwargs):
        super().__init__(**kwargs)
        self.letters = [l for l in letters.upper() if l in string.ascii_uppercase]

    def parse(self, response):
        # --- selector sanity check ---
        total = 0
        for letter in string.ascii_uppercase:
            n = len(response.css(f"#{TAB_ID}_{letter} a"))
            total += n
            self.logger.info(f"[check] tab {letter}: {n} links")
        if total == 0:
            self.logger.error(
                f"[check] No links found under #{TAB_ID}_X. Inspect the page in devtools "
                "and fix TAB_ID / the selector before scaling up."
            )
            return

        for letter in self.letters:
            for a in response.css(f"#{TAB_ID}_{letter} a"):
                yield from self.follow_link(response, a, source="a-z", letter=letter)

    def parse_topic(self, response, source, letter=None):
        if not in_health(response.url):  # redirected off /health/
            self.logger.info(f"[skip] redirected off /health/: {response.url}")
            return

        main = response.css("main, #main")
        if not main:
            self.logger.warning(f"[check] no <main>/#main on {response.url}")

        body_links = main.css("a[href]")
        text = " ".join(
            t.strip() for t in main.css("*:not(script):not(style)::text").getall() if t.strip()
        )
        yield {
            "url": response.url,
            "found_via": source,
            "letter": letter,
            "depth": response.meta.get("depth", 0),
            "title": response.css("title::text").get(default="").strip(),
            "body_link_count": len(body_links),
            "text_preview": text[:300],
            "text_len": len(text),
        }

        for a in body_links:
            yield from self.follow_link(response, a, source=response.url, letter=letter)

    def follow_link(self, response, a, source, letter=None):
        href = a.attrib.get("href", "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return
        url, _ = urldefrag(response.urljoin(href))
        if not in_health(url) or url.lower().endswith(SKIP_EXT):
            return
        yield scrapy.Request(url, callback=self.parse_topic, cb_kwargs={"source": source, "letter": letter})


if __name__ == "__main__":
    letters = sys.argv[1] if len(sys.argv) > 1 else "AB"
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    process = CrawlerProcess(settings={
        "FEEDS": {"test_output.jsonl": {"format": "jsonlines", "overwrite": True}},
        "DOWNLOAD_DELAY": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "DEPTH_LIMIT": depth,                  # 0 = A-Z page, 1 = topic pages, 2 = links from topic pages
        "CLOSESPIDER_PAGECOUNT": max_pages,    # hard stop for testing
        "LOG_LEVEL": "INFO",
    })
    process.crawl(IdohTestSpider, letters=letters)
    process.start()