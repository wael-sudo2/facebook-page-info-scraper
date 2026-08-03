"""Browser tier - Scrapy + Playwright.

The ONLY difference between this and the HTTP tier is how the bytes are
obtained: requests.get() there, a rendered browser page here. Everything
after that - URL normalisation, locale forcing, extraction, record shape -
is the exact same code path.

CSS selectors deliberately do not appear here. Class hashes like x1yztbdb
are build artifacts that Facebook rotates; they belong to the legacy Selenium
implementation in facebook_page_info_scraper.py and nowhere else.

    python -m facebook_page_info_scraper.spider https://www.facebook.com/nike
    python -m facebook_page_info_scraper.spider urls.txt --threads 16
    python -m facebook_page_info_scraper.spider urls.txt --headed --log-level INFO

    from facebook_page_info_scraper.spider import run
    run(urls, threads=16, out="browser.jsonl")

Requires:
    pip install scrapy scrapy-playwright
    playwright install chromium
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from scrapy import Spider, Request
from scrapy.crawler import CrawlerProcess

from . import extract, parsers as P
from .fetch import DEFAULT_LOCALE, with_locale

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

SETTLE_MS = 2_000

def ensure_chromium(auto_install: bool = True) -> None:
    """Make sure the Chromium binary Playwright needs is present.

    pip installs the playwright package but not its browsers - a wheel has no
    post-install hook, so `playwright install chromium` cannot run as part of
    `pip install`. Doing it here on first use keeps the package genuinely
    plug-and-play.

    The download is ~150 MB and happens once; afterwards this is a path
    check costing a fraction of a second.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - install-time only
        raise RuntimeError(
            "the browser engine needs scrapy-playwright:\n"
            "    pip install scrapy scrapy-playwright"
        ) from exc

    try:
        with sync_playwright() as playwright:
            executable = playwright.chromium.executable_path
        if executable and Path(executable).exists():
            return
    except Exception:

        pass

    if not auto_install:
        raise RuntimeError(
            "Chromium is not installed. Run:\n"
            "    playwright install chromium"
        )

    print("Downloading Chromium (one-time, ~150 MB)...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )


def should_abort(request):
    """Drop subresources we never parse - the biggest single speed win."""
    if request.resource_type in ("image", "media", "font", "stylesheet"):
        return True
    return any(m in request.url for m in ("/tr?", "/ajax/bz", "analytics"))


class FacebookPageSpider(Spider):
    name = "facebook_page"

    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_ABORT_REQUEST": should_abort,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30_000,
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "WARNING",
    }

    def __init__(
        self,
        urls: str = "",
        settle_ms: int = SETTLE_MS,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.start_urls = [u for u in urls.split(",") if u.strip()]
        self.settle_ms = int(settle_ms)
        self._sniffed: dict = defaultdict(list)

    async def on_response(self, response, **_):
        """Network sniffer, registered before navigation.

        On pages where Facebook did not prefetch the About payload into the
        HTML, it arrives here instead - as a /api/graphql/ XHR after
        hydration. Capturing it is the whole reason the browser tier can
        rescue a page the HTTP tier cannot: same extraction afterwards, the
        payload just came off the wire instead of out of the document.
        """
        url = getattr(response, "url", "") or ""
        if "/api/graphql" not in url and "/graphqlbatch" not in url:
            return
        try:
            body = await response.text()
        except Exception:
            return
        if P.ABOUT_KEY not in body:
            return
        try:
            page = response.frame.page
        except Exception:
            return
        self._sniffed[page].append(body)

    def start_requests(self):
        for raw in self.start_urls:
            target = P.clean_link(raw.strip())
            if not target:
                self.logger.warning("could not normalise %r - skipped", raw)
                continue
            # Locale is forced, not configurable. The extraction layer
            # matches Facebook's English About labels ("Categories",
            # "Address", "Closed now"), so any other language returns empty
            # fields. Exposing this as an option would only let callers
            # break their own results.
            target = with_locale(target, DEFAULT_LOCALE)
            yield Request(
                target,
                callback=self.parse,
                errback=self.errback,
                dont_filter=True,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                    "playwright_page_event_handlers": {"response": "on_response"},
                    "source_url": raw,
                    "requested": target,
                },
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        started = time.perf_counter()
        try:
            try:
                await page.wait_for_timeout(self.settle_ms)
            except Exception:
                pass

            html = await page.content()
            sniffed = self._sniffed.pop(page, [])
            record = extract.build_record(
                html,
                source_url=response.meta["source_url"],
                requested=response.meta["requested"],
                extra_payloads=sniffed,
            )
            record["ok"] = bool(record.get("page_name"))
            if not record["ok"]:
                record["error"] = (
                    "rendered but no og:title - private page or login wall"
                )
            record.update(
                {
                    "final_url": page.url,
                    "_tier": "browser",
                    "_status": response.status,
                    "_kb": round(len(html) / 1024),
                    "_sniffed": len(sniffed),
                    "_seconds": round(time.perf_counter() - started, 3),
                }
            )
            yield record
        finally:
            self._sniffed.pop(page, None)
            await page.close()

    async def errback(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error("%s failed: %r", failure.request.url, failure.value)


def run(
    urls: list[str],
    *,
    threads: int = 8,
    out: str = "pages_browser.jsonl",
    settle_ms: int = SETTLE_MS,
    headless: bool = True,
    timeout_ms: int = 30_000,
    log_level: str = "WARNING",
    auto_install_browser: bool = True,
) -> None:
    """Run the browser tier over `urls`.

    Args:
        urls:       list of Facebook page URLs.
        threads:    how many pages to render at once. Sets CONCURRENT_REQUESTS,
                    CONCURRENT_REQUESTS_PER_DOMAIN and PLAYWRIGHT_MAX_CONTEXTS
                    together - raising only the first does nothing, because
                    every URL here shares one domain.

                    No ceiling is imposed. A Chromium context costs roughly
                    60-80 MB on top of ~250 MB for the browser itself; pick a
                    number that suits your machine.
        out:        output file (JSON Lines). Named distinctly from the HTTP
                    tier's pages.json / pages.jsonl so runs cannot clobber
                    each other.
        settle_ms:  flat pause after load, before reading the page. The About
                    data arrives as several GraphQL responses, so reading at
                    the first one loses fields. This is the only wait - cost
                    per page is navigation + settle_ms, nothing stacked.
        headless:   False opens a visible browser - useful for debugging.
        timeout_ms: navigation timeout.
        log_level:  Scrapy log level; "INFO" to see per-request detail.
        auto_install_browser:
                    download Chromium on first use if it is missing. Set
                    False in locked-down environments to raise instead.
    """
    urls = [u.strip() for u in urls if u and u.strip()]
    if not urls:
        raise ValueError("no urls given")

    ensure_chromium(auto_install_browser)

    process = CrawlerProcess(
        settings={
            "CONCURRENT_REQUESTS": threads,
            "CONCURRENT_REQUESTS_PER_DOMAIN": threads,
            "PLAYWRIGHT_MAX_CONTEXTS": threads,
            "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": headless},
            "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": timeout_ms,
            "LOG_LEVEL": log_level,
            "FEEDS": {out: {"format": "jsonlines", "overwrite": True}},
        }
    )
    process.crawl(
        FacebookPageSpider,
        urls=",".join(urls),
        settle_ms=settle_ms,
    )
    process.start()


def _load_urls(args: list[str]) -> list[str]:
    """Accept either URLs directly or a path to a file of URLs."""
    if len(args) == 1 and Path(args[0]).is_file():
        return [
            line.strip()
            for line in Path(args[0]).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    return args


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Browser tier: render Facebook pages with Playwright."
    )
    parser.add_argument("urls", nargs="+", help="URLs, or one path to a file of URLs")
    parser.add_argument("--threads", type=int, default=8,
                        help="pages rendered concurrently (default 8, no cap)")
    parser.add_argument("--out", default="pages_browser.jsonl")
    parser.add_argument("--settle-ms", type=int, default=SETTLE_MS,
                        help="pause after load before reading (default 2000)")
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--headed", action="store_true",
                        help="show the browser window")
    parser.add_argument("--log-level", default="WARNING")
    ns = parser.parse_args()

    run(
        _load_urls(ns.urls),
        threads=ns.threads,
        out=ns.out,
        settle_ms=ns.settle_ms,
        timeout_ms=ns.timeout_ms,
        headless=not ns.headed,
        log_level=ns.log_level,
    )
