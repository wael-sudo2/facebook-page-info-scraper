"""Pure extraction functions - no browser, no network, no I/O.

Everything here takes plain strings and returns data, so the whole module is
unit-testable without a driver or a live page.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional, Union

# Legacy Comet CSS markers, kept for the Playwright fallback tier. These are
# build artifacts and rotate often - never rely on them as a primary source.
NEW_LAYOUT = "x1yztbdb"
OLD_LAYOUT = "x9orja2"

JSON_MARKER = 'type="application/json"'
ABOUT_KEY = "about_app_sections"

# --------------------------------------------------------------------------
# regexes
# --------------------------------------------------------------------------

_PHONE_RE = re.compile(
    r"([+]?[+(][0-9]{1,4}[)]?[-\s]?[0-9]{2,7}[-\s]?[0-9]{2,7}[-\s]?[0-9]{4,10})"
    r"|([\d]{2,4}-[\d]{2,4}-[\d]{2,4})"
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+\.\S+\b")
# Facebook has used several rating formats. Current pages show a
# recommendation percentage; older ones show a star rating. Both may carry a
# review count, and unrated pages say so explicitly.
#
#   "74% recommend (9 Reviews)"        -> recommend_percent=74, reviews=9
#   "Rating - 4.5 (128 Reviews)"       -> page_rate=4.5,        reviews=128
#   "Not yet rated (0 Reviews)"        -> reviews=0
_RECOMMEND_RE = re.compile(r"(\d[\d.,]*)\s*%\s*recommend", re.I)
_REVIEWS_RE = re.compile(r"\(\s*(\d[\d.,]*)\s+Reviews?\s*\)", re.I)
_STARS_RE = re.compile(
    r"(?:rating|rated)\D{0,4}(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:stars?|/\s*5)",
    re.I,
)
_NOT_RATED_RE = re.compile(r"not yet rated|no reviews", re.I)

# "Closed now", "Always open", "Opens at 09:00" - opening status, not an
# address and not a category.
_OPEN_STATUS_RE = re.compile(
    r"^(?:closed now|open now|always open|temporarily closed|"
    r"permanently closed|opens?\s+at\b.*|closes?\s+at\b.*|open\s+24\s+hours)$",
    re.I,
)
_COORDS_RE = re.compile(r"center=([-+]?\d+\.\d+)%2C([-+]?\d+\.\d+)")

# Strict, anchored variants for scanning values inside the About subtree,
# where we already know the scope is small and relevant.
EMAIL_EXACT = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_EXACT = re.compile(r"^[+(]?[\d][\d\s().+-]{6,24}$")
URL_EXACT = re.compile(r"^(?:https?://|www\.)", re.I)

# Facebook's own hosts, plus the Bing static-map link Facebook injects for
# page addresses - none of these are the page's website.
_NOT_A_WEBSITE = re.compile(
    r"facebook\.com|fbcdn|fbsbx|messenger\.com|meta\.com|"
    r"bing\.com/maps|/maps/default\.aspx",
    re.I,
)

_SOCIAL_RES = [
    re.compile(rf"(https?%3A%2F%2F(?:www\.)?{host}%2F[\w.-]+)")
    for host in (
        r"instagram\.com",
        r"linkedin\.com",
        r"youtube\.com",
        r"twitter\.com",
        r"pinterest\.com",
    )
]

# Boilerplate section headings Facebook renders in every About panel.
_ABOUT_BOILERPLATE = {
    "contact and basic info",
    "page transparency",
    "contact info",
    "websites and social links",
    "basic info",
    "more info",
    "additional info",
    "privacy policy",
    "see all",
}


# --------------------------------------------------------------------------
# url normalisation
# --------------------------------------------------------------------------

# Any Facebook host: bare, www, m, mbasic, web, pages, or a locale
# subdomain such as sv-se.facebook.com.
_FB_HOST = re.compile(r"^https?://(?:[\w-]+\.)*facebook\.com", re.I)

_RESERVED_SLUGS = {
    "", "about", "pages", "groups", "profile.php", "login", "help",
    "policies", "privacy", "terms", "watch", "marketplace", "events",
    "gaming", "business", "ads", "settings",
}


def _redirect_to_about(link: Optional[str]) -> Optional[str]:
    if not link:
        return None
    return link + "about" if link.endswith("/") else link + "/about"


def clean_link(link: str) -> Optional[str]:
    """Normalise any Facebook URL shape to `https://www.facebook.com/<slug>/about`.

    Returns None when no usable page slug can be derived - a bare
    facebook.com, a reserved path, or a non-Facebook URL.
    """
    if not link or not link.strip():
        return None
    link = link.strip()

    # Normalise every Facebook host variant to www. Without this, a no-www
    # URL falls through the slug regex below and never gets '/about'.
    if not _FB_HOST.match(link):
        return None
    link = _FB_HOST.sub("https://www.facebook.com", link)

    # Numeric profile forms
    for pattern in (r"(?<=profile\.php\?id=)(\d+)", r"(?<=[?&]id=)(\d+)"):
        match = re.search(pattern, link)
        if match:
            return _redirect_to_about(
                f"https://www.facebook.com/{match.group(1)}"
            )

    if "comment_id=" in link:
        match = re.search(r"(?<=www\.facebook\.com/)([^/?]*)", link)
        if match:
            link = f"https://www.facebook.com/{match.group(1)}"

    # Strip content sub-paths
    link = re.sub(r"/pages/", "/", link)
    link = re.sub(r"facebook\.com/category/(.*?)/", "facebook.com/", link)
    link = re.sub(r"/posts/.*", "", link)
    link = re.sub(r"/photos/.*", "", link)
    link = re.sub(r"/videos/.*", "", link)
    link = re.sub(r"/public/", "/", link)
    link = re.sub(r"\?.*", "", link)

    # Group and people URLs keep their sub-path
    if "/people/" in link or "/groups/" in link:
        return _redirect_to_about(link.rstrip("/") + "/")

    match = re.search(r"(?<=www\.facebook\.com/)([^/?#]*)", link)
    if not match:
        return None

    slug = urllib.parse.unquote(match.group(1)).strip()
    if slug.lower() in _RESERVED_SLUGS:
        return None

    return _redirect_to_about(f"https://www.facebook.com/{match.group(1)}")


# --------------------------------------------------------------------------
# field extraction from free text
# --------------------------------------------------------------------------

def page_name_from_title(title: str) -> Optional[str]:
    if not title:
        return None
    return title.replace(" | Facebook", "").strip() or None


def fetch_phone(text: str) -> Optional[str]:
    try:
        phone = _PHONE_RE.findall(text)[0][0]
    except IndexError:
        return None
    return phone or None


def fetch_email(text: str) -> Union[list, str, None]:
    emails = _EMAIL_RE.findall(text or "")
    if len(emails) == 1:
        return emails[0]
    return emails or None


def fetch_website(text: str) -> Union[list, str, None]:
    urls = [u for u in _URL_RE.findall(text or "") if not _NOT_A_WEBSITE.search(u)]
    if len(urls) == 1:
        return urls[0]
    return urls or None


def rating_info(text: str) -> Optional[dict]:
    """Parse any of Facebook's rating formats, or return None.

    Returns a dict with whichever of `page_rate`, `recommend_percent` and
    `page_review_number` were present. Returning None means the string is
    not rating-related at all, which is what lets the classifier keep
    rating strings out of `page_category`.
    """
    if not text:
        return None

    out: dict = {}
    unrated = bool(_NOT_RATED_RE.search(text))

    reviews = _REVIEWS_RE.search(text)
    if reviews:
        out["page_review_number"] = reviews.group(1)

    recommend = _RECOMMEND_RE.search(text)
    if recommend:
        out["recommend_percent"] = recommend.group(1)

    # Skip star parsing when the page says it is unrated: _STARS_RE keys on
    # "rating|rated", and "Not yet rated (0 Reviews)" would otherwise yield
    # a page_rate of "0" - a real score of zero, not an absence.
    if not unrated:
        stars = _STARS_RE.search(text)
        if stars:
            out["page_rate"] = stars.group(1) or stars.group(2)

    if unrated:
        out.setdefault("page_review_number", "0")

    return out or None


def fetch_rate_and_reviews(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (rating, review_count). Kept for backwards compatibility.

    The original returned [rate, reviews] but unpacked it as
    `review_number, rate = ...[0], ...[1]`, silently swapping the two in the
    output. Fixed here - the order matches the names.
    """
    info = rating_info(text) or {}
    return info.get("page_rate"), info.get("page_review_number")


def fetch_social_media_links(hrefs: list[str]) -> Union[list, str, None]:
    """Pull social profile URLs out of Facebook's percent-encoded redirects."""
    links: list[str] = []
    for href in hrefs:
        if not href:
            continue
        for pattern in _SOCIAL_RES:
            found = pattern.findall(href)
            if found:
                links.append(urllib.parse.unquote(found[0]))
    if len(links) == 1:
        return links[0]
    return links or None


def coords_from_style(style: str) -> Optional[tuple[str, str]]:
    """Extract (lat, lon) from a static-map background-image style attribute."""
    if not style or "background-image:" not in style:
        return None
    found = _COORDS_RE.findall(style)
    return (found[0][0], found[0][1]) if found else None


def is_website(value: str) -> bool:
    return bool(URL_EXACT.match(value)) and not _NOT_A_WEBSITE.search(value)


# --------------------------------------------------------------------------
# About-panel text classification
# --------------------------------------------------------------------------

_ADDRESS_SEP = re.compile(r"[,\n]")
_LETTERS = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
_PRICE_HINT = re.compile(r"price range", re.I)
_DETAILS_HINT = re.compile(r"^details about\b", re.I)


_TYPE_LABELS = {
    "address": "address",
    "addresses": "address",
    "category": "page_category",
    "categories": "page_category",
    "email": "email",
    "e-mail": "email",
    "website": "page_website",
    "websites": "page_website",
    "phone": "phone_number",
    "phone number": "phone_number",
    "mobile": "phone_number",
    "price range": "price_range",
    "hours": "hours",
    "founded": "founded",
    "impressum": "impressum",
    "rating": "page_rate",
}

_LABEL_ONLY_FIELDS = {"address", "page_category", "price_range", "hours",
                      "founded", "impressum"}


def _is_noise(value: str) -> bool:
    low = value.lower()
    return (
        not value
        or low in _ABOUT_BOILERPLATE
        or low in _TYPE_LABELS
        or bool(_DETAILS_HINT.match(value))
    )


def _is_rating(value: str) -> bool:
    return rating_info(value) is not None


def _is_open_status(value: str) -> bool:
    return bool(_OPEN_STATUS_RE.match(value.strip()))


def _looks_like_address(value: str) -> bool:
    """Ingredient test, not an ordering test - see _ADDRESS_SEP above."""
    if len(value) > 140 or not _ADDRESS_SEP.search(value):
        return False
    if not _LETTERS.search(value):
        return False
    if _is_rating(value) or _is_open_status(value):
        return False
    if EMAIL_EXACT.match(value) or URL_EXACT.match(value):
        return False
    if _PRICE_HINT.search(value):
        return False

    return any(c.isdigit() for c in value) or value.count(",") >= 1


def _valid_for(field: str, value: str) -> bool:
    """Is `value` a plausible payload for `field`?

    A label tells us which field a neighbour belongs to, but not which
    neighbour. Facebook puts the label before the value in some rows
    ("Categories" / "Bakery") and after it in others (street lines, then
    "Address"), so both sides must be tested and the implausible one
    rejected. Without this, the "Address" label claims whatever follows it -
    which on a page with no reviews is "Not yet rated (0 Reviews)".
    """
    if _is_noise(value):
        return False

    typed_elsewhere = (
        _is_rating(value)
        or bool(EMAIL_EXACT.match(value))
        or bool(URL_EXACT.match(value))
    )

    if field == "address":
        return (
            not typed_elsewhere
            and not _is_open_status(value)
            and not _PRICE_HINT.search(value)
            and (any(c.isdigit() for c in value) or "," in value)
        )
    if field == "page_category":
        return (
            not typed_elsewhere
            and not _is_open_status(value)
            and not _PRICE_HINT.search(value)
            and "\n" not in value
            and len(value) <= 60
        )
    if field == "price_range":
        return bool(_PRICE_HINT.search(value)) or any(
            sym in value for sym in "$€£kr"
        )
    return not typed_elsewhere


def classify_about_text(lines: list[str]) -> dict:
    """Sort the About panel's strings into typed fields.

    Two passes, strongest signal first:

      1. Label-driven. Facebook emits an English type label adjacent to each
         value ("Categories" / "Bakery", "Address" after the street lines).
         Binding to that label is language-independent and immune to
         formatting differences.

      2. Shape-driven fallback, for rows whose label is missing or renamed.

    `lines` must preserve document order, and must include single-word
    entries - the labels and many categories ("Bakery") are single words.
    """
    out: dict = {
        "page_category": None,
        "address": None,
        "price_range": None,
        "page_rate": None,
        "recommend_percent": None,
        "page_review_number": None,
        "open_status": None,
        "hours": None,
        "founded": None,
        "impressum": None,
        "about_other": [],
    }
    items = [(raw or "").strip() for raw in (lines or [])]
    claimed: set[int] = set()

    # ---- pass 1: labels -------------------------------------------------
    for index, value in enumerate(items):
        field = _TYPE_LABELS.get(value.lower())
        if field is None or field not in _LABEL_ONLY_FIELDS:
            continue
        if out.get(field):
            continue

        for neighbour in (index + 1, index - 1):
            if not 0 <= neighbour < len(items) or neighbour in claimed:
                continue
            candidate = items[neighbour]
            if not _valid_for(field, candidate):
                continue
            out[field] = candidate
            claimed.add(neighbour)
            break

    # ---- pass 2: shape --------------------------------------------------
    for index, value in enumerate(items):
        if index in claimed or _is_noise(value):
            continue

        if (
            EMAIL_EXACT.match(value)
            or URL_EXACT.match(value)
            or (
                PHONE_EXACT.match(value)
                and sum(c.isdigit() for c in value) >= 7
            )
        ):
            continue

        info = rating_info(value)
        if info:
            for key, found in info.items():
                if out.get(key) is None:
                    out[key] = found
            continue

        if _is_open_status(value):
            out["open_status"] = out["open_status"] or value
            continue

        if _PRICE_HINT.search(value):
            out["price_range"] = out["price_range"] or value
            continue

        if out["address"] is None and _looks_like_address(value):
            out["address"] = value
            continue


        if (
            out["page_category"] is None
            and len(value) <= 60
            and "\n" not in value
        ):
            out["page_category"] = value
            continue

        out["about_other"].append(value)

    return out


def detect_layout(html: str) -> Optional[str]:
    """Which legacy Comet layout marker the rendered page uses, if any."""
    if NEW_LAYOUT in html:
        return NEW_LAYOUT
    if OLD_LAYOUT in html:
        return OLD_LAYOUT
    return None
