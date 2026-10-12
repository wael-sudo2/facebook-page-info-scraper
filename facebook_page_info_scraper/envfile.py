"""Read keys from a .env file, so callers do not have to export them.

A library reaching for a dotfile deserves a justification. This one is small
and strict:

  * real environment variables always win - a .env never overwrites them
  * nothing is written, only read
  * failure is silent: no .env is the normal case, not an error

Only `python-dotenv`'s simplest behaviour is reproduced. Taking a dependency
for `KEY=value` would cost more than it saves.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

FILENAME = ".env"

# How far up from the working directory to look. A scraper is often run from
# a subdirectory of the project that holds the .env.
MAX_PARENTS = 3

_loaded: set[str] = set()


def find(start: Optional[Path] = None) -> Optional[Path]:
    """Nearest .env at or above `start`, or None."""
    here = (start or Path.cwd()).resolve()
    for directory in [here, *list(here.parents)[:MAX_PARENTS]]:
        candidate = directory / FILENAME
        if candidate.is_file():
            return candidate
    return None


def parse(text: str) -> dict[str, str]:
    """KEY=value lines. Blank lines, comments and `export` prefixes ignored."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        # Strip one matching pair of quotes, not every quote - a password
        # may legitimately contain them.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and value:
            out[key] = value
    return out


def load(path: Optional[Path] = None, *, force: bool = False) -> dict[str, str]:
    """Load a .env into os.environ without clobbering anything already set.

    Returns the keys this call actually applied. Repeat calls for the same
    file are no-ops unless `force`.
    """
    target = path or find()
    if target is None:
        return {}

    marker = str(target)
    if marker in _loaded and not force:
        return {}
    _loaded.add(marker)

    try:
        values = parse(target.read_text(encoding="utf-8-sig"))
    except OSError:
        return {}

    applied: dict[str, str] = {}
    for key, value in values.items():
        if os.environ.get(key):
            continue          # a real environment variable outranks the file
        os.environ[key] = value
        applied[key] = value
    return applied
