<div align="center">

# facebook-page-info-scraper

**Public Facebook page info as a Python dict — fast, no login, no API key.**

[![PyPI](https://img.shields.io/pypi/v/facebook-page-info-scraper.svg)](https://pypi.python.org/pypi/facebook-page-info-scraper)
[![Python](https://img.shields.io/pypi/pyversions/facebook-page-info-scraper.svg)](https://pypi.python.org/pypi/facebook-page-info-scraper)
[![License](https://img.shields.io/pypi/l/facebook-page-info-scraper.svg)](https://github.com/wael-sudo2/facebook-page-info-scraper/blob/main/LICENSE.txt)
[![Downloads](https://static.pepy.tech/badge/facebook-page-info-scraper)](https://pepy.tech/project/facebook-page-info-scraper)
[![Monthly](https://static.pepy.tech/badge/facebook-page-info-scraper/month)](https://pepy.tech/project/facebook-page-info-scraper)
[![Weekly](https://static.pepy.tech/badge/facebook-page-info-scraper/week)](https://pepy.tech/project/facebook-page-info-scraper)

![Requests](https://img.shields.io/badge/Requests-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Scrapy](https://img.shields.io/badge/Scrapy-60A839?style=for-the-badge&logo=scrapy&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white)

</div>

---

## ⚡ Quick start

```bash
pip install facebook-page-info-scraper
```

```python
from facebook_page_info_scraper import scrape_page

scrape_page("https://www.facebook.com/examplepage")
```

That is everything — both engines install and are ready to use.

---

## 🚀 Two engines, one result

Pick whichever suits the job. **Both take the same URLs, return the same
fields, and run the same extraction.** They differ only in how the page is
requested.

<table>
<tr><th></th><th>🌐 HTTP</th><th>🎭 Browser</th></tr>
<tr><td><b>requests with</b></td><td><code>requests</code></td><td>Chromium via Playwright</td></tr>
<tr><td><b>speed</b></td><td>~1.4 s per page</td><td>~3 s per page</td></tr>
<tr><td><b>memory</b></td><td>negligible</td><td>~60–80 MB per page</td></tr>
<tr><td><b>runs JavaScript</b></td><td>—</td><td>✅</td></tr>
<tr><td><b>reads network traffic</b></td><td>—</td><td>✅ captures GraphQL responses</td></tr>
<tr><td><b>suits</b></td><td>large lists, minimal setup</td><td>pages whose data never reaches the raw HTML</td></tr>
</table>

```python
from facebook_page_info_scraper import scrape_pages       # 🌐 HTTP
from facebook_page_info_scraper.spider import run         # 🎭 Browser

scrape_pages(urls, threads=16)
run(urls, threads=8)
```

> The browser engine downloads Chromium (~150 MB) the first time it runs —
> pip cannot fetch browser binaries, so it happens on first use. One time
> only.

---

## 📖 What it does

Give it a Facebook page URL, get back the page's public details: name,
category, email, phone, website, address, likes, ratings, opening status.

## 🎯 What it solves

Facebook page data used to require driving a real browser — slow, heavy, and
it broke every time Facebook changed its CSS. Both engines here read
Facebook's own page payload instead, so neither depends on how the page
looks.

---

## 🌐 Usage — HTTP

```python
from facebook_page_info_scraper import scrape_page, scrape_pages

page  = scrape_page("https://www.facebook.com/examplepage")
pages = scrape_pages(urls, threads=16)

print(page["email"])        # hello@example.com
print(page["page_likes"])   # 12,480
```

```bash
python scrape.py urls.txt                  # -> pages.json
python scrape.py urls.txt --threads 24
python scrape.py urls.txt --out output.json
```

```python
scrape_page(url,   want_about=True, timeout=25)
scrape_pages(urls, threads=16, want_about=True, timeout=25)
```

`want_about=False` reads only the page header — faster, but no email or phone.

---

## 🎭 Usage — Browser

```python
from facebook_page_info_scraper.spider import run

run(urls, threads=8)                    # -> pages_browser.jsonl
run(urls, threads=8, headless=False)    # watch it work
```

```bash
python -m facebook_page_info_scraper.spider urls.txt --threads 8
python -m facebook_page_info_scraper.spider urls.txt --headed
python -m facebook_page_info_scraper.spider https://www.facebook.com/examplepage
```

```python
run(urls,
    threads=8,                  # pages rendered at once, no cap
    out="pages_browser.jsonl",
    settle_ms=2000,             # pause after load before reading
    headless=True)
```

This engine works in batches — pass a list of URLs rather than one at a time.

---

## 📥 Input

Any Facebook page URL. These all work with either engine:

```
https://www.facebook.com/examplepage
https://facebook.com/examplepage                        (no www)
https://www.facebook.com/examplepage/                   (trailing slash)
https://www.facebook.com/pages/Example-Page/100000000000000
https://www.facebook.com/profile.php?id=100000000000000
http://sv-se.facebook.com/pages/Example-Page/100000000000000   (locale subdomain)
```

## 📤 Output

Identical from either engine.

```python
{
  "page_name": "Example Store",
  "page_id": "100000000000000",
  "page_category": "Bakery",
  "email": "hello@example.com",
  "phone_number": "+33 1 23 45 67 89",
  "page_website": "https://example.com",
  "address": "1 Example Street\n12345 Sampletown",
  "page_likes": "12,480",
  "talking_about": "215",
  "were_here": "33",
  "recommend_percent": "94",
  "page_review_number": "18",
  "open_status": "Closed now",
  "price_range": "Price Range - $",
  "bio": "Example Store. 12,480 likes ...",
  "image": "https://scontent.xx.fbcdn.net/...",
  "canonical": "https://www.facebook.com/examplepage",
  "locale": "en_US",
  "ok": True
}
```

### Fields

| field | type | description |
|---|---|---|
| `page_name` | `str` | Page name |
| `page_id` | `str` | Numeric Facebook page ID |
| `page_category` | `str \| None` | e.g. `Bakery`, `Clothing Store` |
| `email` | `str \| list \| None` | Contact email(s) |
| `phone_number` | `str \| list \| None` | Contact phone(s) |
| `page_website` | `str \| list \| None` | External website(s) |
| `address` | `str \| None` | Full street address |
| `page_likes` | `str \| None` | Like count, e.g. `12,480` |
| `page_followers` | `str \| None` | Follower count |
| `talking_about` | `str \| None` | "talking about this" count |
| `were_here` | `str \| None` | Check-in count |
| `recommend_percent` | `str \| None` | e.g. `74` from "74% recommend" |
| `page_rate` | `str \| None` | Star rating, where shown |
| `page_review_number` | `str \| None` | Review count |
| `open_status` | `str \| None` | `Closed now`, `Always open`, … |
| `price_range` | `str \| None` | e.g. `Price Range · $` |
| `bio` | `str \| None` | Page description |
| `image` | `str \| None` | Profile picture URL |
| `canonical` | `str` | Canonical page URL |
| `locale` | `str` | Language Facebook served |
| `ok` | `bool` | Whether the scrape succeeded |
| `error` | `str` | Present only when `ok` is `False` |

Always check `ok`:

```python
page = scrape_page(url)
print(page.get("page_name")if page.get("ok") else page.get("error"))
```

> **One thing to know.** `email`, `phone_number` and `page_website` are a
> **string** when the page lists one, and a **list** when it lists several.
> ```python
> "email": "hello@example.com"                          # one
> "email": ["sales@example.com", "press@example.com"]   # several
> "email": None                                         # none
>
> def as_list(v):
>     return [] if v is None else (v if isinstance(v, list) else [v])
> ```

---

## 🩺 Check your run

One call tells you how a batch went. Works on records from either engine.

```python
from facebook_page_info_scraper import scrape_pages, summarise

records = scrape_pages(urls, threads=16)
summarise(records)
```

```python
{
  "total": 213,          # records in
  "ok": 211,             # scraped successfully
  "failed": 2,
  "with_about": 164,     # found the About panel
  "with_email": 150,
  "with_phone": 115,
  "with_website": 161,
  "wrong_locale": 0,     # pages Facebook served in another language
  "avg_seconds": 1.44,
  "avg_kb": 533          # bytes actually read, not page size
}
```

Field counts are measured against `ok`, not `total` — dead URLs never drag
your extraction numbers down. That makes the two problems easy to tell apart:

| what moved | what it means |
|---|---|
| `ok` dropped | **fetching** — blocks, rate limits, bad URLs |
| `ok` steady, `with_email` dropped | **extraction** — Facebook changed something |
| `wrong_locale` above `0` | those pages came back in another language |

Handy as a guard in scheduled jobs:

```python
stats = summarise(records)
if stats["with_email"] / stats["ok"] < 0.60:
    raise SystemExit("email extraction dropped — check for changes")
```

---

## 📊 Speed

Measured on the same 183-page list, same machine.

| | 🐌 old (Selenium) | 🌐 HTTP | 🎭 Browser |
|---|---|---|---|
| per page | 15–20 s | **~1.4 s** | ~3 s |
| pages in parallel | ❌ | ✅ 16+ | ✅ you choose |
| **200 pages** | ~50 min | **under 1 min** | ~2 min |
| memory | ~60 MB/page | negligible | ~60–80 MB/page |
| needs Chrome installed | ✅ | ❌ | downloads its own |

Both engines beat the old Selenium version by a wide margin — HTTP by roughly
**50×**, the browser engine by about **6×** while still running JavaScript.

---

## 🔮 Roadmap

An **AI extraction layer** is planned for the tail that deterministic rules
cannot reach — unlabelled free-text rows in languages whose formatting
conventions vary, plus self-healing selectors that repair themselves when
Facebook changes shape. It will sit *behind* the current parsers, not in
front of them: rules first, model only where rules come up empty.

---

## ⬆️ Upgrading from 1.x

The old Selenium class still works:

```bash
pip install facebook-page-info-scraper[selenium]
```

```python
from facebook_page_info_scraper import FacebookPageInfoScraper
FacebookPageInfoScraper(url).get_page_info()
```

Either new engine is a recommended replacement — same idea, much faster.

Two output differences:

- `page_rate` and `page_review_number` used to be swapped. They are correct now.
- `location` was a country name; the new `address` is the full street address.

---

## 🤝 Contributing

Contributions are welcome. If you find an issue or have a suggestion, please
open an issue or submit a pull request on GitHub.

## 📝 Notes

- Only public pages. Nothing behind a login.
- Be reasonable with `threads` — this hits Facebook from your IP.
- Scraping Facebook is against their Terms of Service. Use accordingly.

## License

MIT — see [LICENSE.txt](https://github.com/wael-sudo2/facebook-page-info-scraper/blob/main/LICENSE.txt).
