"""Turn a fetched Facebook page into a record.

Two independent sources, deliberately ordered by how stable they are:

  T1  Open Graph <meta> tags
      An open standard the whole web's link previews depend on. Facebook
      cannot change it without breaking every share button on the internet,
      so it is the most durable signal available.

  T2  The prefetched `about_app_sections` Relay payload
      Facebook's own GraphQL field names, embedded in the HTML before any
      JS runs. Rotates far more slowly than CSS class hashes, which are
      build artifacts with no external consumers.

Each field records which tier produced it, so a caller can tell a
deterministic hit from a fallback guess.
"""

from __future__ import annotations

import html as html_mod
import json
import re
from typing import Any, Iterable, Iterator, Optional

from . import parsers as P

_META_RE = re.compile(
    r'<meta[^>]+(?:property|name)="(og:[^"]+|description)"[^>]+content="([^"]*)"',
    re.I,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_PAGE_ID_RE = re.compile(r"fb://profile/(\d+)")
_BLOB_RE = re.compile(
    r'<script type="application/json"[^>]*>(.*?)</script>', re.DOTALL
)

_LIKES_RE = re.compile(r"(\d[\d.,\s]*)\s+likes", re.I)
_TALKING_RE = re.compile(r"(\d[\d.,\s]*)\s+talking about this", re.I)
_WERE_HERE_RE = re.compile(r"(\d[\d.,\s]*)\s+were here", re.I)
_FOLLOWERS_RE = re.compile(r"(\d[\d.,\s]*)\s+followers", re.I)

FIELDS = (
    "page_name", "page_id", "canonical", "bio", "page_likes", "page_followers",
    "talking_about", "were_here", "email", "phone_number", "page_website",
    "social_media_links", "page_category", "address", "price_range",
    "page_rate", "page_review_number",
)


# --------------------------------------------------------------------------
# tier 1 - Open Graph metadata
# --------------------------------------------------------------------------

def from_meta(html: str) -> dict:
    meta = {
        key.lower(): html_mod.unescape(value)
        for key, value in _META_RE.findall(html)
    }
    bio = meta.get("og:description") or meta.get("description") or ""

    def count(pattern) -> Optional[str]:
        match = pattern.search(bio)
        return match.group(1).strip() if match else None

    title = _TITLE_RE.search(html)
    page_id = _PAGE_ID_RE.search(html)

    return {
        "page_name": meta.get("og:title")
        or P.page_name_from_title(title.group(1) if title else ""),
        "page_id": page_id.group(1) if page_id else None,
        "canonical": meta.get("og:url"),
        "image": meta.get("og:image"),
        "locale": meta.get("og:locale"),
        "bio": bio or None,
        "page_likes": count(_LIKES_RE),
        "page_followers": count(_FOLLOWERS_RE),
        "talking_about": count(_TALKING_RE),
        "were_here": count(_WERE_HERE_RE),
    }


# --------------------------------------------------------------------------
# tier 2 - prefetched About payload
# --------------------------------------------------------------------------

def _walk(node: Any) -> Iterator[Any]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)
    else:
        yield node


def _find_key(node: Any, key: str) -> Iterator[Any]:
    if isinstance(node, dict):
        for found_key, value in node.items():
            if found_key == key:
                yield value
            yield from _find_key(value, key)
    elif isinstance(node, list):
        for value in node:
            yield from _find_key(value, key)


def _json_docs(candidates: Iterable[str]) -> Iterator[Any]:
    """Parse each candidate, tolerating newline-delimited JSON.

    Facebook streams multi-part GraphQL responses as several JSON objects
    separated by newlines, so a captured XHR body is not always a single
    document.
    """
    for raw in candidates:
        raw = (raw or "").strip()
        if not raw or P.ABOUT_KEY not in raw:
            continue
        try:
            yield json.loads(raw)
            continue
        except (ValueError, TypeError):
            pass
        for line in raw.splitlines():
            line = line.strip()
            if not line or P.ABOUT_KEY not in line:
                continue
            try:
                yield json.loads(line)
            except (ValueError, TypeError):
                continue


def about_subtree(
    html: str, extra_payloads: Iterable[str] = ()
) -> Optional[Any]:
    """The richest `about_app_sections` payload available.

    `extra_payloads` carries raw JSON bodies captured from the network - the
    browser tier sniffs /api/graphql/ responses, because on pages where the
    payload was not prefetched into the HTML it only ever exists on the wire.
    Same search either way; only the source differs.
    """
    best = None
    best_size = 0
    for doc in _json_docs(list(_BLOB_RE.findall(html)) + list(extra_payloads)):
        for value in _find_key(doc, P.ABOUT_KEY):
            size = len(json.dumps(value))
            if size > best_size:
                best, best_size = value, size
    return best


def from_about(subtree: Any) -> dict:
    """Classify the strings inside the About subtree.

    Scoping to this subtree is what makes naive matching safe - the same
    patterns run against the whole 16 MB document match Facebook's internal
    config (URL blocklists, page-load IDs) instead of the page's own data.
    """
    emails: list[str] = []
    phones: list[str] = []
    websites: list[str] = []
    ordered: list[str] = []
    seen: set[str] = set()

    for value in _walk(subtree):
        if not isinstance(value, str):
            continue
        item = value.strip()
        if not item or len(item) > 300:
            continue

        if P.EMAIL_EXACT.match(item):
            emails.append(item)
        elif P.is_website(item):
            websites.append(item)
        elif P.PHONE_EXACT.match(item) and sum(c.isdigit() for c in item) >= 7:
            phones.append(item)
        if item not in seen:
            seen.add(item)
            ordered.append(item)

    def uniq(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    record = {
        "email": uniq(emails),
        "phone_number": uniq(phones),
        "page_website": uniq(websites),
    }
    record.update(P.classify_about_text(ordered))
    return record


# --------------------------------------------------------------------------
# combined
# --------------------------------------------------------------------------

def _first(value):
    """Collapse single-element lists so the common case reads naturally."""
    if isinstance(value, list):
        if not value:
            return None
        return value[0] if len(value) == 1 else value
    return value


def build_record(
    html: str,
    *,
    source_url: str,
    requested: str,
    extra_payloads: Iterable[str] = (),
) -> dict:
    """Merge both tiers into one record, tracking which tier supplied what.

    `extra_payloads` are raw JSON bodies captured from the network (browser
    tier only). They are searched alongside the HTML's embedded blobs.
    """
    record: dict = {"source_url": source_url, "requested": requested}
    provenance: dict = {}

    for key, value in from_meta(html).items():
        record[key] = value
        if value not in (None, "", []):
            provenance[key] = 1

    subtree = about_subtree(html, extra_payloads)
    if subtree is not None:
        for key, value in from_about(subtree).items():
            collapsed = _first(value)
            if collapsed in (None, "", []):
                continue

            record[key] = collapsed
            provenance[key] = 2


    if not record.get("page_website") and record.get("bio"):
        site = P.fetch_website(record["bio"])
        if site:
            record["page_website"] = site
            provenance["page_website"] = 1

    record.setdefault("about_other", [])
    record["_tiers"] = provenance
    record["_has_about"] = subtree is not None
    return record
