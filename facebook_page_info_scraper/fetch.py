"""HTTP fetching for Facebook pages - no browser required.

Two non-obvious requirements are encoded here; both were found the hard way
and both fail *silently* if you get them wrong:

1. Facebook returns HTTP 400 unless the request carries the `Sec-Fetch-*`
   and `sec-ch-ua` client-hint headers. A plain User-Agent is not enough.

2. Do NOT advertise `br` in Accept-Encoding. `requests` cannot decode brotli
   unless the optional `brotli` package is installed, and an undecoded body
   arrives as a 200 with a plausible byte count that parses to nothing -
   which looks exactly like an empty page.
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

import requests

DEFAULT_LOCALE = "en_US"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


HEAD_MARKER = b"</head>"
ABOUT_MARKER = b"about_app_sections"

HEAD_CAP = 128 * 1024
FULL_CAP = 12 * 1024 * 1024


@dataclass
class Response:
    """What a fetch produced, plus how it went."""

    url: str
    html: str = ""
    status: Optional[int] = None
    final_url: Optional[str] = None
    bytes_read: int = 0
    seconds: float = 0.0
    truncated: bool = False
    error: Optional[str] = None
    headers: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == 200 and bool(self.html)

    @property
    def walled(self) -> bool:
        target = self.final_url or ""
        return any(m in target for m in ("/login", "/checkpoint", "/recover"))


def new_session(user_agent: Optional[str] = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session


def with_locale(url: str, locale: Optional[str] = DEFAULT_LOCALE) -> str:
    """Add ?locale=<locale> to a URL, preserving any existing query.

    Applied here rather than in parsers.clean_link(), which strips query
    strings - anything added there would be deleted. Keeping it in the fetch
    layer also leaves `requested` in the output free of transport concerns.
    """
    if not locale:
        return url
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query["locale"] = locale
    return urllib.parse.urlunsplit(
        parts._replace(query=urllib.parse.urlencode(query))
    )


def fetch(
    url: str,
    session: Optional[requests.Session] = None,
    *,
    want_about: bool = True,
    timeout: int = 25,
    cap: Optional[int] = None,
) -> Response:
    """GET `url`, reading only as far as needed.

    want_about=False stops after </head> (fast; og: metadata only).
    want_about=True continues until the About payload's script tag closes.
    The page language is forced to DEFAULT_LOCALE and is not an option -
    extraction matches Facebook's English About labels, so any other
    language returns empty fields.
    """
    session = session or new_session()
    marker = ABOUT_MARKER if want_about else HEAD_MARKER
    limit = cap or (FULL_CAP if want_about else HEAD_CAP)
    target = with_locale(url, DEFAULT_LOCALE)

    started = time.perf_counter()
    result = Response(url=url)
    buf = bytearray()
    found = -1

    try:
        with session.get(
            target, timeout=timeout, stream=True, allow_redirects=True
        ) as response:
            result.status = response.status_code
            result.final_url = response.url
            result.headers = dict(response.headers)

            for chunk in response.iter_content(65536):
                buf += chunk
                if want_about:
                    if found < 0:
                        found = buf.find(marker)
                    elif buf.find(b"</script>", found) != -1:
                        break
                elif marker in buf:
                    break
                if len(buf) >= limit:
                    result.truncated = True
                    break

        result.html = buf.decode("utf-8", errors="replace")
        result.bytes_read = len(buf)

        if result.bytes_read and "<" not in result.html[:4096]:
            enc = result.headers.get("content-encoding", "?")
            result.error = (
                f"body did not decode as HTML (content-encoding={enc}); "
                "check Accept-Encoding"
            )
            result.html = ""
    except Exception as exc:
        result.error = repr(exc)[:200]

    result.seconds = round(time.perf_counter() - started, 3)
    return result
