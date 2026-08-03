"""Public API - fetch Facebook page info without a browser.

    from facebook_page_info_scraper import scrape_page, scrape_pages

    scrape_page("https://www.facebook.com/nike")
    scrape_pages(open("urls.txt").read().split(), threads=16)

Concurrency here is thread-bound rather than browser-bound, so the practical
ceiling is the network and Facebook's tolerance - not RAM. The browser tier
in `spider.py` remains available for pages that do not ship a prefetched
About payload.
"""

from __future__ import annotations

import concurrent.futures as cf
import threading
import time
from typing import Iterable, Optional

from . import extract, parsers as P
from .fetch import Response, fetch, new_session

DEFAULT_THREADS = 16

_local = threading.local()


def _session():
    """One requests.Session per worker thread, so connections get reused."""
    session = getattr(_local, "session", None)
    if session is None:
        session = _local.session = new_session()
    return session


def _failure(url: str, requested: Optional[str], reason: str, resp=None) -> dict:
    record = {
        "source_url": url,
        "requested": requested,
        "ok": False,
        "error": reason,
        "_tiers": {},
    }
    if resp is not None:
        record.update(
            {
                "_status": resp.status,
                "_kb": round(resp.bytes_read / 1024),
                "_seconds": resp.seconds,
                "final_url": resp.final_url,
            }
        )
    return record


def scrape_page(url: str, *, want_about: bool = True, timeout: int = 25) -> dict:
    """Scrape one page. Always returns a dict; check `ok`.

    want_about=False reads only the document head - faster, but yields just
    the Open Graph fields (no email/phone).
    """
    target = P.clean_link(url)
    if not target:
        return _failure(url, None, "could not derive a page slug from this URL")

    started = time.perf_counter()
    response: Response = fetch(
        target, _session(), want_about=want_about, timeout=timeout
    )

    if response.error:
        return _failure(url, target, response.error, response)
    if response.walled:
        return _failure(url, target, "redirected to a login wall", response)
    if not response.ok:
        return _failure(url, target, f"http {response.status}", response)

    record = extract.build_record(
        response.html, source_url=url, requested=target
    )
    record["ok"] = bool(record.get("page_name"))
    if not record["ok"]:
        record["error"] = "page loaded but no og:title - private, or markup changed"
    record.update(
        {
            "final_url": response.final_url,
            "_status": response.status,
            "_kb": round(response.bytes_read / 1024),
            "_truncated": response.truncated,
            "_seconds": round(time.perf_counter() - started, 3),
        }
    )
    return record


def scrape_pages(
    urls: Iterable[str],
    *,
    threads: int = DEFAULT_THREADS,
    want_about: bool = True,
    timeout: int = 25,
) -> list[dict]:
    """Scrape many pages concurrently. Order matches the input."""
    urls = [u.strip() for u in urls if u and u.strip()]
    if not urls:
        return []

    def work(url: str) -> dict:
        try:
            return scrape_page(url, want_about=want_about, timeout=timeout)
        except Exception as exc:  # a worker must never kill the batch
            return _failure(url, None, repr(exc)[:200])

    with cf.ThreadPoolExecutor(max_workers=threads) as pool:
        return list(pool.map(work, urls))


def summarise(records: list[dict]) -> dict:
    """Aggregate counts - the numbers worth alarming on."""
    ok = [r for r in records if r.get("ok")]
    return {
        "total": len(records),
        "ok": len(ok),
        "failed": len(records) - len(ok),
        "with_about": sum(1 for r in ok if r.get("_has_about")),
        "with_email": sum(1 for r in ok if r.get("email")),
        "with_phone": sum(1 for r in ok if r.get("phone_number")),
        "with_website": sum(1 for r in ok if r.get("page_website")),
        # Anything other than en_US means ?locale= was ignored on that page
        # and its About fields were parsed against the wrong language.
        "wrong_locale": sum(
            1 for r in ok if r.get("locale") and r["locale"] != "en_US"
        ),
        "avg_seconds": (
            round(sum(r.get("_seconds", 0) for r in ok) / len(ok), 2) if ok else 0
        ),
        "avg_kb": (
            round(sum(r.get("_kb", 0) for r in ok) / len(ok)) if ok else 0
        ),
    }
