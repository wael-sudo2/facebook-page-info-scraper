"""Decide whether an email local part is a role address or a person.

    info@shop.se       -> role      (a company inbox)
    niklas@shop.se     -> personal  (an individual)
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterable, Optional


PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "env": ("DEEPSEEK_API_KEY",),
        "package": "openai",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "strict_schema": False,
    },
    "openai": {
        "env": ("OPENAI_API_KEY",),
        "package": "openai",
        "model": "gpt-4o-mini",
        "base_url": None,
        "strict_schema": True,
    },
}


PROVIDER_ORDER = ("deepseek", "openai")

BATCH = 150

_PERSONAL_SHAPE = re.compile(r"^[^\W\d_]{2,}[._-][^\W\d_]{2,}$", re.UNICODE)

_SCHEMA = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "local_part": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["role", "personal", "unknown"],
                    },
                },
                "required": ["local_part", "type"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["classifications"],
    "additionalProperties": False,
}

_PROMPT = """\
Classify each email local part (the text before the @) as one of:

  role      a shared company address - a function, department or greeting.
            Examples in any language: info, contact, kontakt, ventas,
            asiakaspalvelu, klantenservice, butik, bonjour, sav, 事務局
  personal  an individual person's address - a given name, surname, or both
  unknown   genuinely impossible to tell

Judge the word in whatever language it is written. A first name in Finnish
is still personal; a word meaning "shop" in Swedish is still role. Treat a
common abbreviation as what it abbreviates.

Return one entry per input, preserving the exact input string.

Local parts:
{parts}"""


_JSON_TAIL = """

Reply with json in exactly this form and nothing else:
{"classifications": [{"local_part": "info", "type": "role"}]}"""


def shape_guess(local: str) -> Optional[str]:
    """Vocabulary-free fallback. Returns 'personal' or None."""
    return "personal" if _PERSONAL_SHAPE.match(local or "") else None


# --------------------------------------------------------------------------
# provider selection
# --------------------------------------------------------------------------

def _has_key(name: str) -> bool:
    return any(os.environ.get(var) for var in PROVIDERS[name]["env"])


def _has_package(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(PROVIDERS[name]["package"]) is not None


def providers_available() -> list[str]:
    """Which providers are usable right now - key present and SDK installed."""
    return [
        name for name in PROVIDER_ORDER
        if name in PROVIDERS and _has_key(name) and _has_package(name)
    ]


def resolve(
    provider: Optional[str] = None, model: Optional[str] = None
) -> Optional[tuple[str, str]]:
    """Pick a (provider, model) pair, or None if nothing is usable.

    Explicit argument wins, then FBPS_LLM_PROVIDER, then PROVIDER_ORDER.
    """
    choice = provider or os.environ.get("FBPS_LLM_PROVIDER") or None
    if choice:
        choice = choice.strip().lower()
        if choice not in PROVIDERS:
            raise ValueError(
                f"unknown provider {choice!r}; "
                f"expected one of {', '.join(PROVIDERS)}"
            )
        if not (_has_key(choice) and _has_package(choice)):
            return None
        return choice, model or PROVIDERS[choice]["model"]

    usable = providers_available()
    if not usable:
        return None
    return usable[0], model or PROVIDERS[usable[0]]["model"]


def available(provider: Optional[str] = None) -> bool:
    """Can we actually call a model?"""
    try:
        return resolve(provider) is not None
    except ValueError:
        return False


# --------------------------------------------------------------------------
# the call
# --------------------------------------------------------------------------

def _parse(text: str) -> dict:
    """Pull {local_part: type} out of a model reply, tolerantly.

    A provider without schema enforcement occasionally wraps the object in
    prose or a fenced block, so fall back to the outermost braces.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        match = re.search(r"\{.*\}", text or "", re.S)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
        except ValueError:
            return {}

    answers: dict[str, str] = {}
    for row in (data or {}).get("classifications", []):
        local = (row.get("local_part") or "").strip().lower()
        kind = row.get("type")
        if local and kind in ("role", "personal", "unknown"):
            answers[local] = kind
    return answers


def _ask_chunk(chunk: list[str], provider: str, model: str) -> dict:
    """One request. Both providers speak the OpenAI protocol; they differ
    only in whether the server enforces the schema.
    """
    import openai

    config = PROVIDERS[provider]
    api_key = next(
        (os.environ[var] for var in config["env"] if os.environ.get(var)), None
    )
    client = openai.OpenAI(api_key=api_key, base_url=config["base_url"])

    prompt = _PROMPT.format(parts="\n".join(chunk))
    if config["strict_schema"]:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "classifications",
                "strict": True,
                "schema": _SCHEMA,
            },
        }
    else:
        response_format = {"type": "json_object"}
        prompt += _JSON_TAIL

    kwargs = {
        "model": model,
        "response_format": response_format,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        response = client.chat.completions.create(max_tokens=8000, **kwargs)
    except TypeError:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        if "max_completion_tokens" not in str(exc):
            raise
        response = client.chat.completions.create(
            max_completion_tokens=8000, **kwargs
        )

    return _parse(response.choices[0].message.content or "")


def _ask_model(parts: list[str], provider: str, model: str) -> dict:
    answers: dict[str, str] = {}
    for start in range(0, len(parts), BATCH):
        answers.update(
            _ask_chunk(parts[start : start + BATCH], provider, model)
        )
    return answers


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def classify_parts(
    parts: Iterable[str],
    *,
    use_llm: bool = True,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, dict]:
    """Classify local parts. Nothing is read from or written to disk.

    Returns {local_part: {"type": ..., "source": <provider>|shape|none}}.
    The source names the provider that answered, so a run stays auditable.

    Duplicates collapse here: the input is deduplicated before any request,
    so a batch of addresses costs one call per BATCH distinct local parts.
    """
    wanted = sorted({(p or "").strip().lower() for p in parts if p})
    if not wanted:
        return {}

    out: dict[str, dict] = {}

    if use_llm:
        try:
            chosen = resolve(provider, model)
        except ValueError:
            chosen = None
        if chosen:
            name, model_id = chosen
            try:
                answers = _ask_model(wanted, name, model_id)
            except Exception:
                answers = {}  # API trouble must not break enrichment
            for local in wanted:
                if local in answers:
                    out[local] = {"type": answers[local], "source": name}

    for local in wanted:
        if local in out:
            continue
        guess = shape_guess(local)
        out[local] = (
            {"type": guess, "source": "shape"} if guess
            else {"type": "unknown", "source": "none"}
        )

    return out


def classify_one(
    local: str,
    *,
    use_llm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    return classify_parts(
        [local], use_llm=use_llm, provider=provider, model=model
    ).get(
        (local or "").strip().lower(), {"type": "unknown", "source": "none"}
    )
