"""
- Find contact details on a company's own website
- Fetching happens in two tiers. Plain `requests` handles the large majority;
sites that answer with a bot challenge instead are retried with a browser
TLS fingerprint via `curl_cffi`, which installs with the package
"""

from __future__ import annotations

import functools
import html as html_mod
import re
import socket
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Iterable, Optional

import requests

from . import classify
from .fetch import BASE_HEADERS

CONTACT_PATHS = (
    "/contact", "/contact-us", "/contacts",
    "/kontakt", "/kontakta-oss",       # sv / da / no / de
    "/contacto", "/contactez-nous",    # es / fr
    "/about", "/about-us",
    "/impressum",                      # legally mandated in DE/AT
)

READ_LIMIT = 512 * 1024
DEFAULT_TIMEOUT = 12


IMPERSONATE = "chrome"


CHALLENGE_MARKERS = (
    "just a moment",
    "enable javascript and cookies",
    "checking your browser",
    "attention required",
    "ddos protection by",
    "cf_chl_opt",
    "__cf_chl",
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_MAILTO_RE = re.compile(r'mailto:([^"\'>\s?]+)', re.I)
_TEL_RE = re.compile(r'tel:([+0-9()\s.-]{7,25})', re.I)


FREEMAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com", "aol.com",
    "protonmail.com", "proton.me", "gmx.de", "gmx.net", "web.de",
}


_NOT_CONTACT = re.compile(
    r"\.(?:png|jpe?g|gif|webp|svg|css|js|woff2?)$"     # asset filenames
    r"|^[0-9a-f]{16,}@"                                # sentry-style keys
    r"|@sentry\.io\b"
    r"|^(?:no-?reply|do-?not-?reply|postmaster|abuse|webmaster)@",
    re.I,
)


# --------------------------------------------------------------------------
# text handling
# --------------------------------------------------------------------------

def unescape(text: str) -> str:
    """Undo HTML and JSON escaping before pattern matching.

    Emails frequently live inside inline JSON where '>' is \\u003e and quotes
    are backslash-escaped. Matching the raw bytes produced junk like
    'u003einfo@example.com' and 'info@example.com\\\\\\'.
    """
    text = html_mod.unescape(text)
    text = re.sub(r"\\u00([0-9a-fA-F]{2})",
                  lambda m: chr(int(m.group(1), 16)), text)
    return text.replace("\\/", "/").replace('\\"', '"')


def clean_email(raw: str) -> Optional[str]:
    value = unescape(raw or "").strip().lower()
    value = value.strip("\\\"'<>(),;").rstrip(".")
    value = re.sub(r"^(?:u00[0-9a-f]{2}|x[0-9a-f]{2})", "", value)
    if value.count("@") != 1 or len(value) > 100:
        return None
    if _NOT_CONTACT.search(value):
        return None
    local, _, domain = value.partition("@")
    if not local or "." not in domain:
        return None
    return value


def host_of(url: str) -> str:
    parsed = urllib.parse.urlsplit(url if "//" in url else "//" + url)
    return (parsed.hostname or "").lower().removeprefix("www.")


def registrable(host: str) -> str:
    """Crude eTLD+1. Good enough to compare a site to an email domain."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def brand_of(host: str) -> str:
    """'kostaboda.com' and 'kostaboda.se' share a brand; treat them as related."""
    reg = registrable(host)
    return reg.split(".")[0]


@functools.lru_cache(maxsize=8192)
def domain_resolves(domain: str) -> Optional[bool]:
    """Does the mail domain exist in DNS at all?

    This is an A/AAAA lookup, not an MX query - a real MX check needs
    dnspython, and this catches the case that matters (a domain nobody
    registered) without the dependency. Returns None when DNS itself
    failed, so a flaky resolver never costs a candidate points.
    """
    try:
        socket.getaddrinfo(domain, None)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return None


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

@dataclass
class Candidate:
    email: str
    source: str                       # mailto | text
    page: str                         # url it was found on
    score: int = 0
    confidence: str = "low"
    kind: str = "unknown"             # role | personal | unknown
    kind_source: str = "none"         # <provider> | shape | none
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "email": self.email,
            "type": self.kind,
            "type_source": self.kind_source,
            "confidence": self.confidence,
            "score": self.score,
            "source": self.source,
            "found_on": self.page,
            "reasons": self.reasons,
        }


def score_candidate(
    cand: Candidate, site_host: str, kinds: Optional[dict] = None
) -> Candidate:
    """Signals, not word lists. See module docstring for why nothing is
    filtered outright.

    `kinds` maps local part -> {"type", "source"} from classify.py. Every
    other signal here is structural and needs no data at all, so scoring
    still works when it is empty.
    """
    local, _, domain = cand.email.partition("@")
    reasons: list[str] = []
    score = 0

    if cand.source == "mailto":
        score += 3
        reasons.append("mailto link")
    else:
        reasons.append("found in page text")

    site_reg, mail_reg = registrable(site_host), registrable(domain)
    if site_reg == mail_reg:
        score += 4
        reasons.append("domain matches site")
    elif brand_of(site_host) and brand_of(site_host) == brand_of(domain):
        # kostaboda.com -> info@kostaboda.se
        score += 3
        reasons.append("same brand, different TLD")
    elif domain in FREEMAIL:
        score += 1
        reasons.append("freemail address")
    else:
        # Weighted to outrank a mailto+role combination on its own. Company
        # sites link partner and parent-company addresses (allabolag.se
        # exposes hej@uc.se and content@proff.se as mailto links), and those
        # would otherwise score medium purely for being well-formed.
        score -= 3
        reasons.append("domain unrelated to site")

    verdict = (kinds or {}).get(local) or {"type": "unknown", "source": "none"}
    cand.kind = verdict["type"]
    cand.kind_source = verdict["source"]
    if verdict["type"] == "role":
        score += 2
        reasons.append(f"role address (via {verdict['source']})")
    elif verdict["type"] == "personal":
        reasons.append(f"looks personal (via {verdict['source']})")
    else:
        reasons.append("role or personal not determined")

    if domain not in FREEMAIL and domain_resolves(domain) is False:
        score -= 4
        reasons.append("domain does not resolve")

    cand.score = score
    cand.confidence = "high" if score >= 6 else "medium" if score >= 3 else "low"
    cand.reasons = reasons
    return cand


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

@dataclass
class Fetched:
    """Outcome of one request, with the reason kept rather than discarded.

    An earlier version returned Optional[str], which made a Cloudflare
    challenge, a DNS failure, a timeout and a 404 all indistinguishable -
    every one surfaced as "unreachable" and none could be retried usefully.
    """
    body: Optional[str] = None
    status: Optional[int] = None
    outcome: str = "error"        # ok|challenged|forbidden|not_found|
                                  # timeout|dns|error|http_NNN
    tier: str = "requests"        # requests | curl_cffi
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.outcome == "ok" and bool(self.body)


def read_outcome(status: Optional[int], body: str, headers: dict) -> str:
    """Name what came back. Mirrors the Phase 0 probe's classifier."""
    lowered = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    if lowered.get("cf-mitigated") == "challenge":
        return "challenged"
    head = (body or "")[:4000].lower()
    if any(marker in head for marker in CHALLENGE_MARKERS):
        return "challenged"
    server = lowered.get("server", "").lower()
    if status in (403, 503) and "cloudflare" in server:
        return "challenged"
    if status in (401, 403):
        return "forbidden"
    if status == 404:
        return "not_found"
    if status and 200 <= status < 300:
        return "ok"
    return f"http_{status}" if status else "error"


def fingerprint_available() -> bool:
    """Is the optional browser-fingerprint tier installed?"""
    import importlib.util

    return importlib.util.find_spec("curl_cffi") is not None


def _get_requests(
    session: requests.Session, url: str, timeout: int
) -> Fetched:
    """Tier 1 - plain HTTP. Handles the large majority of sites."""
    try:
        with session.get(
            url, timeout=timeout, stream=True, allow_redirects=True
        ) as response:
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                chunks.append(chunk)
                size += len(chunk)
                if size >= READ_LIMIT:
                    break
            body = b"".join(chunks).decode("utf-8", errors="replace")
            return Fetched(
                body=body,
                status=response.status_code,
                outcome=read_outcome(
                    response.status_code, body, dict(response.headers)
                ),
            )
    except requests.Timeout:
        return Fetched(outcome="timeout", error="timeout")
    except requests.ConnectionError as exc:
        text = str(exc)
        dns = "NameResolutionError" in text or "getaddrinfo failed" in text
        return Fetched(
            outcome="dns" if dns else "error", error=type(exc).__name__
        )
    except Exception as exc:
        return Fetched(outcome="error", error=type(exc).__name__)


def _get_fingerprint(url: str, timeout: int) -> Fetched:
    """Tier 2 - a real browser's TLS fingerprint, for challenged sites.

    Only reached when tier 1 was challenged, so the cost of not streaming
    the body applies to a small minority of requests.
    """
    try:
        from curl_cffi import requests as cffi
    except ImportError:
        return Fetched(
            outcome="challenged", tier="curl_cffi",
            error="curl_cffi not installed",
        )
    try:
        response = cffi.get(
            url, impersonate=IMPERSONATE, timeout=timeout,
            allow_redirects=True,
        )
        body = response.text[:READ_LIMIT]
        return Fetched(
            body=body,
            status=response.status_code,
            outcome=read_outcome(
                response.status_code, body, dict(response.headers)
            ),
            tier="curl_cffi",
        )
    except Exception as exc:
        return Fetched(
            outcome="error", tier="curl_cffi", error=type(exc).__name__
        )


def _get(
    session: requests.Session,
    url: str,
    timeout: int,
    *,
    use_fingerprint: bool = True,
) -> Fetched:
    """Fetch one page, escalating to the fingerprint tier on a challenge."""
    result = _get_requests(session, url, timeout)
    if result.outcome == "challenged" and use_fingerprint:
        retried = _get_fingerprint(url, timeout)
        # Keep the retry only if it actually got us further.
        if retried.ok or retried.outcome != "error":
            return retried
    return result


def harvest(body: str, page_url: str) -> tuple[list[Candidate], list[str]]:
    text = unescape(body)
    seen: set[str] = set()
    found: list[Candidate] = []

    for raw in _MAILTO_RE.findall(body):
        email = clean_email(raw)
        if email and email not in seen:
            seen.add(email)
            found.append(Candidate(email, "mailto", page_url))

    for raw in _EMAIL_RE.findall(text):
        email = clean_email(raw)
        if email and email not in seen:
            seen.add(email)
            found.append(Candidate(email, "text", page_url))

    phones = []
    for raw in _TEL_RE.findall(body):
        cleaned = re.sub(r"[^\d+]", "", raw)
        if 7 <= sum(c.isdigit() for c in cleaned) <= 15 and cleaned not in phones:
            phones.append(cleaned)

    return found, phones


def _collect(
    website: str,
    session: Optional[requests.Session],
    timeout: int,
    follow_contact_pages: bool,
    use_fingerprint: bool = True,
) -> tuple[dict, list[Candidate], str]:
    """Fetch a site and harvest candidates. No classification, no scoring.

    Split out so a batch can do every fetch first and then classify all the
    local parts in one call, instead of one call per site.
    """
    started = time.perf_counter()
    url = website.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    session = session or requests.Session()
    session.headers.update(BASE_HEADERS)
    site_host = host_of(url)

    result = {
        "website": url,
        "emails": [],
        "phones": [],
        "pages_fetched": 0,
        "status": "ok",
        "tier": "requests",
        "fetch_outcome": "ok",
    }

    page = _get(session, url, timeout, use_fingerprint=use_fingerprint)
    result["pages_fetched"] += 1
    result["tier"] = page.tier
    result["fetch_outcome"] = page.outcome
    if page.error:
        result["error"] = page.error

    if not page.ok:
        result["status"] = (
            "challenged" if page.outcome == "challenged" else "unreachable"
        )
        result["seconds"] = round(time.perf_counter() - started, 2)
        return result, [], site_host

    candidates, phones = harvest(page.body, url)

    if follow_contact_pages and not candidates:
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        for path in CONTACT_PATHS:
            sub = _get(session, base + path, timeout,
                       use_fingerprint=use_fingerprint)
            result["pages_fetched"] += 1
            if not sub.ok:
                continue
            candidates, more = harvest(sub.body, base + path)
            phones.extend(p for p in more if p not in phones)
            if candidates:
                result["found_on_path"] = path
                break

    result["phones"] = phones[:3]
    result["seconds"] = round(time.perf_counter() - started, 2)
    return result, candidates, site_host


def _score_into(
    result: dict, candidates: list[Candidate], site_host: str, kinds: dict
) -> dict:
    """Score harvested candidates into a collected result."""
    if result["status"] in ("unreachable", "challenged"):
        return result
    scored = [score_candidate(c, site_host, kinds) for c in candidates]
    scored.sort(key=lambda c: -c.score)
    result["emails"] = [c.as_dict() for c in scored]
    if not scored:
        result["status"] = "no_contact_found"
    return result


def enrich_site(
    website: str,
    *,
    session: Optional[requests.Session] = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_contact_pages: bool = True,
    use_fingerprint: bool = True,
    use_llm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """Fetch one website and return whatever contact details it exposes."""
    result, candidates, site_host = _collect(
        website, session, timeout, follow_contact_pages, use_fingerprint
    )
    kinds = classify.classify_parts(
        [c.email.partition("@")[0] for c in candidates],
        use_llm=use_llm, provider=provider, model=model,
    )
    return _score_into(result, candidates, site_host, kinds)


# --------------------------------------------------------------------------
# record-level API
# --------------------------------------------------------------------------

def websites_of(record: dict) -> list[str]:
    value = record.get("page_website")
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def enrich_records(
    records: Iterable[dict],
    *,
    threads: int = 8,
    timeout: int = DEFAULT_TIMEOUT,
    only_missing_email: bool = True,
    follow_contact_pages: bool = True,
    use_fingerprint: bool = True,
    use_llm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict]:
    """Add website-sourced contacts to records that lack an email.

    Sites are fetched once even when several records share one - the probe
    found 15% of requests were duplicates.
    """
    records = list(records)

    targets: dict[str, list[dict]] = {}
    for record in records:
        if only_missing_email and record.get("email"):
            continue
        if not record.get("ok", True):
            continue
        sites = websites_of(record)
        if sites:
            targets.setdefault(sites[0].strip(), []).append(record)

    if not targets:
        return records

    def work(site: str):
        session = requests.Session()
        session.headers.update(BASE_HEADERS)
        return site, _collect(
            site, session, timeout, follow_contact_pages, use_fingerprint
        )

    with ThreadPoolExecutor(max_workers=threads) as pool:
        collected = dict(pool.map(work, targets))


    found = [c for _, cands, _ in collected.values() for c in cands]
    if found:
        with ThreadPoolExecutor(max_workers=threads) as pool:
            pool.map(
                domain_resolves,
                {c.email.partition("@")[2] for c in found},
            )
    kinds = classify.classify_parts(
        [c.email.partition("@")[0] for c in found],
        use_llm=use_llm, provider=provider, model=model,
    )

    results = {
        site: _score_into(result, cands, host, kinds)
        for site, (result, cands, host) in collected.items()
    }

    for site, holders in targets.items():
        outcome = results.get(site, {})
        for record in holders:
            record["enrichment"] = outcome
            best = (outcome.get("emails") or [None])[0]
            if best:
                record["enriched_email"] = best["email"]
                record["enriched_email_type"] = best["type"]
                record["enriched_confidence"] = best["confidence"]
                record["_enrich_email_source"] = best["source"]
            record["_enrich_status"] = outcome.get("status", "skipped")
            record["_enrich_tier"] = outcome.get("tier", "requests")

    return records


def summarise_enrichment(records: Iterable[dict]) -> dict:
    records = list(records)
    touched = [r for r in records if "enrichment" in r]
    got = [r for r in touched if r.get("enriched_email")]

    by_conf: dict[str, int] = {}
    for record in got:
        key = record.get("enriched_confidence", "?")
        by_conf[key] = by_conf.get(key, 0) + 1

    by_tier: dict[str, int] = {}
    for record in touched:
        key = record.get("_enrich_tier", "requests")
        by_tier[key] = by_tier.get(key, 0) + 1

    challenged = sum(
        1 for r in touched if r.get("_enrich_status") == "challenged"
    )
    return {
        "records": len(records),
        "attempted": len(touched),
        "found_email": len(got),
        "by_confidence": by_conf,
        "by_tier": by_tier,
        "unreachable": sum(
            1 for r in touched if r.get("_enrich_status") == "unreachable"
        ),
        "no_contact": sum(
            1 for r in touched if r.get("_enrich_status") == "no_contact_found"
        ),
        "challenged": challenged,

        "hint": (
            f"{challenged} site(s) were challenged and curl_cffi is not "
            "importable - reinstall facebook-page-info-scraper to retry "
            "them with a browser fingerprint"
            if challenged and not fingerprint_available() else None
        ),
    }
