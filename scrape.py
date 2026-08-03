"""CLI over the package.

    python scrape.py urls.txt
    python scrape.py urls.txt --threads 24
    python scrape.py urls.txt --fast          # head only: no email/phone
    python scrape.py urls.txt --out pages.json
    python scrape.py urls.txt --jsonl         # line-delimited instead

Default output is a pretty-printed JSON array, so `json.load(f)` gives you a
list of dicts directly. Use --jsonl for the streamable one-object-per-line
form, which matters only for very large runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from facebook_page_info_scraper import scrape_pages, summarise


def load(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"no such file: {path}")
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", type=Path)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument(
        "--fast",
        action="store_true",
        help="read only the document head (Open Graph fields, no contact info)",
    )
    ap.add_argument(
        "--jsonl",
        action="store_true",
        help="write one object per line instead of a JSON array",
    )
    args = ap.parse_args()
    out = args.out or Path("pages.jsonl" if args.jsonl else "pages.json")

    urls = load(args.urls)
    print(f"scraping {len(urls)} urls with {args.threads} threads...\n")

    records = scrape_pages(
        urls, threads=args.threads, want_about=not args.fast
    )

    # ensure_ascii=False keeps Nordic characters readable (Harjedalsbrod,
    # Godsvagen) instead of \uXXXX escapes. No BOM - some editors add one on
    # save, which breaks a plain utf-8 json.load().
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        if args.jsonl:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        else:
            json.dump(records, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    for record in records:
        if not record.get("ok"):
            print(f"  FAIL  {record['source_url']}")
            print(f"        {record.get('error')}")
            continue
        mark = "*" if record.get("email") or record.get("phone_number") else " "
        print(f"{mark} {record.get('_seconds', 0):>5.2f}s  {record.get('page_name')}")
        for field in ("email", "phone_number", "page_website", "page_category",
                      "address"):
            value = record.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(value[:3])
                print(f"        {field:<14}: {value}")

    stats = summarise(records)
    print("\n" + "=" * 60)
    for key, value in stats.items():
        print(f"  {key:<14}: {value}")
    print(f"  written       : {out}")


if __name__ == "__main__":
    main()
