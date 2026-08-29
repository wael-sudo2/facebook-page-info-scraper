# __init__.py
from .version import __version__
from .client import scrape_page, scrape_pages, summarise
from .enrich import (
    enrich_records,
    enrich_site,
    fingerprint_available,
    summarise_enrichment,
)

__all__ = [
    "scrape_page",
    "scrape_pages",
    "summarise",
    "enrich_records",
    "enrich_site",
    "summarise_enrichment",
    "fingerprint_available",
    "FacebookPageInfoScraper",
    "FacebookPageSpider",
    "__version__",
]


def __getattr__(name):
    """Lazy imports (PEP 562) for the optional browser tiers.

    Keeps `from facebook_page_info_scraper import FacebookPageInfoScraper`
    working for existing users, without pulling selenium / googletrans /
    geopy (or scrapy / playwright) into processes that only need the HTTP
    path - and without firing the import-time side effect in the Selenium
    module's retry decorator.
    """
    if name == "FacebookPageInfoScraper":
        from .facebook_page_info_scraper import FacebookPageInfoScraper

        return FacebookPageInfoScraper
    if name == "FacebookPageSpider":
        from .spider import FacebookPageSpider

        return FacebookPageSpider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
