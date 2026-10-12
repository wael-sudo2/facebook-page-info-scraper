"""Fetch a page through a proxy, for sites that refuse a direct request.

Some sites cannot be reached from your own address no matter how the request
is shaped: a bot challenge that survives a browser fingerprint, an IP-based
geo-block, a host that answers 402 to datacentre ranges. Coming from a
different address is the only thing that helps, and that is all this does.

Two shapes of "proxy" exist and they are not alike:

  kind="proxy"   a real HTTP proxy. You keep your own request and pass
                 credentials:  http://user:pass@host:port
  kind="api"     a scraping API. You call *their* endpoint with your target
                 URL as a parameter; they fetch it and hand back the body.

`kind` is the switch, so adding a vendor is one dict entry rather than a
rewrite. Nothing here is required - the package ships with no proxy and no
extra dependency, and every tier below this one works without it.

Note on HTTPS_PROXY: `requests` already honours it on every call, so a proxy
set that way is in effect from tier 1 and needs nothing here.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from . import envfile

PROVIDERS: dict[str, dict] = {
    # Your own proxy first: you are already paying for it.
    "custom": {
        "kind": "proxy",
        "env": ("FBPS_PROXY_URL",),
        "label": "custom",
    },
    "scrapingant": {
        "kind": "api",
        "env": ("SCRAPINGANT_API_KEY", "ANT_API_KEY"),
        "endpoint": "https://api.scrapingant.com/v2/general",
        "key_param": "x-api-key",
        "url_param": "url",
        # browser=false returns the HTML without rendering, which is all the
        # extractor needs and the cheaper call of the two.
        "params": {"browser": "false", "proxy_type": "residential"},
        # Their 423 means the target detected *them* - a block, not a bug.
        "blocked_status": (423,),
        "label": "scrapingant",
    },
}

PROVIDER_ORDER = ("custom", "scrapingant")

# Outcomes worth a second attempt from another address.
RETRYABLE = ("challenged", "forbidden", "error", "timeout")

# Never worth retrying: no proxy revives a domain nobody registered, and a
# 404 is a 404 from every address on earth.
NEVER_RETRY = ("ok", "dns", "not_found", "redirect")


def should_retry(outcome: str) -> bool:
    """Is this failure one a different IP might fix?

    Measured on a live run rather than guessed: the two sites a proxy
    actually rescued returned `http_402` and an SSL `error` - neither was a
    bot challenge. Any 4xx/5xx therefore qualifies, which a fixed list of
    named outcomes would have missed.
    """
    if not outcome or outcome in NEVER_RETRY:
        return False
    if outcome in RETRYABLE:
        return True
    if outcome.startswith("http_"):
        code = outcome[5:]
        return code.isdigit() and 400 <= int(code) < 600
    return False

READ_LIMIT = 512 * 1024


def _has_key(name: str) -> bool:
    return any(os.environ.get(var) for var in PROVIDERS[name]["env"])


def _value(name: str) -> Optional[str]:
    return next(
        (os.environ[var] for var in PROVIDERS[name]["env"] if os.environ.get(var)),
        None,
    )


def providers_available() -> list[str]:
    """Which proxies are configured right now."""
    envfile.load()
    return [n for n in PROVIDER_ORDER if n in PROVIDERS and _has_key(n)]


def resolve(provider: Optional[str] = None) -> Optional[str]:
    """Pick a provider name, or None if nothing is configured.

    Explicit argument wins, then FBPS_PROXY_PROVIDER, then PROVIDER_ORDER.
    """
    envfile.load()
    choice = provider or os.environ.get("FBPS_PROXY_PROVIDER") or None
    if choice:
        choice = choice.strip().lower()
        if choice not in PROVIDERS:
            raise ValueError(
                f"unknown proxy provider {choice!r}; "
                f"expected one of {', '.join(PROVIDERS)}"
            )
        return choice if _has_key(choice) else None

    usable = providers_available()
    return usable[0] if usable else None


def available(provider: Optional[str] = None) -> bool:
    """Is a proxy configured and usable?"""
    try:
        return resolve(provider) is not None
    except ValueError:
        return False


def describe() -> dict:
    """What is configured, without revealing any secret."""
    envfile.load()
    return {
        name: {
            "kind": PROVIDERS[name]["kind"],
            "configured": _has_key(name),
            "via": next(
                (v for v in PROVIDERS[name]["env"] if os.environ.get(v)), None
            ),
        }
        for name in PROVIDER_ORDER
    }


def proxies_for(provider: Optional[str] = None) -> Optional[dict]:
    """A requests-style proxies mapping, for callers that build their own
    request and only want a different exit address.

    Deliberately refuses an API scraper. Measured against Facebook: a
    request the API builds comes back without the prefetched About payload,
    dropping a page from six extracted fields to three. Silently halving a
    caller's data would be worse than failing.
    """
    if provider is None:
        # Auto-resolution only considers real proxies, and returns None when
        # there is none - the same quiet no-op the rest of the library uses
        # for an unconfigured optional feature.
        envfile.load()
        name = next(
            (n for n in PROVIDER_ORDER
             if PROVIDERS[n]["kind"] == "proxy" and _has_key(n)), None
        )
        if name is None:
            return None
    else:
        name = resolve(provider)
        if name is None:
            return None

    config = PROVIDERS[name]
    if config["kind"] != "proxy":
        # Only reachable when the caller named it, so say why plainly.
        raise ValueError(
            f"{name} is a scraping API, not a proxy. Facebook does not return "
            "its About payload through one (measured: 6 extracted fields "
            "drop to 3), so it cannot be used here. Set FBPS_PROXY_URL to a "
            "standard http://user:pass@host:port proxy instead."
        )
    url = _value(name)
    return {"http": url, "https": url}


def _read(response: requests.Response, limit: int) -> str:
    chunks, size = [], 0
    for chunk in response.iter_content(65536):
        chunks.append(chunk)
        size += len(chunk)
        if size >= limit:
            break
    return b"".join(chunks).decode("utf-8", errors="replace")


def fetch(
    url: str,
    *,
    timeout: int = 30,
    provider: Optional[str] = None,
    read_limit: int = READ_LIMIT,
) -> dict:
    """Fetch `url` through the configured proxy.

    Returns {provider, status, headers, body, error} - never raises, so a
    proxy problem degrades to the tier below instead of failing a batch.
    """
    try:
        name = resolve(provider)
    except ValueError as exc:
        return {"provider": None, "status": None, "headers": {},
                "body": None, "error": str(exc)}
    if name is None:
        return {"provider": None, "status": None, "headers": {},
                "body": None, "error": "no proxy configured"}

    config = PROVIDERS[name]
    result = {"provider": name, "status": None, "headers": {},
              "body": None, "error": None}

    try:
        if config["kind"] == "proxy":
            proxy_url = _value(name)
            with requests.get(
                url, timeout=timeout, stream=True, allow_redirects=True,
                proxies={"http": proxy_url, "https": proxy_url},
            ) as response:
                result["status"] = response.status_code
                result["headers"] = dict(response.headers)
                result["body"] = _read(response, read_limit)
            return result

        # kind == "api": their endpoint, our target URL as a parameter.
        params = {
            config["url_param"]: url,
            config["key_param"]: _value(name),
            **config.get("params", {}),
            "timeout": min(timeout, 60),
        }
        with requests.get(
            config["endpoint"], params=params, timeout=timeout + 10, stream=True
        ) as response:
            body = _read(response, read_limit)
            if response.status_code in config.get("blocked_status", ()):
                # Their own block code: report it as the target refusing us,
                # not as a transport failure.
                result["status"] = 403
                result["body"] = ""
                result["error"] = f"{name}: target detected the proxy"
                return result
            if response.status_code >= 400:
                result["status"] = response.status_code
                result["error"] = f"{name}: {body[:160]}"
                return result
            # A 200 from the API means it reached the target; the body is
            # the target's page, so let the caller classify it as usual.
            result["status"] = 200
            result["headers"] = dict(response.headers)
            result["body"] = body
        return result

    except requests.Timeout:
        result["error"] = f"{name}: timeout"
        return result
    except Exception as exc:
        result["error"] = f"{name}: {type(exc).__name__}"
        return result
