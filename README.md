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

![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![DeepSeek](https://img.shields.io/badge/DeepSeek-4D6BFE?style=for-the-badge&logo=deepseek&logoColor=white)
![curl_cffi](https://img.shields.io/badge/curl__cffi-073551?style=for-the-badge&logo=curl&logoColor=white)

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

That is everything. One install, no extras to pick.

## 📦 What's in the box

| | | |
|---|---|---|
| 🌐 **HTTP engine** | public page data | ~1.4 s per page |
| 🎭 **Browser engine** | pages whose data needs JavaScript | ~3 s per page |
| 📧 **Contact enrichment** | recovers missing emails from company websites | 🤖 AI-labelled |

```python
from facebook_page_info_scraper import scrape_pages, enrich_records

records = scrape_pages(urls, threads=16)   # scrape
records = enrich_records(records)          # fill in the missing emails
```

<sub>Ships with `requests`, `scrapy-playwright`, `openai` (serves OpenAI **and**
DeepSeek) and `curl_cffi`. The AI step is opt-in and needs only an API key —
everything else works without one.</sub>

---

## 🎯 What it solves

**Getting the data.** Give it a Facebook page URL, get back the page's public
details — name, category, email, phone, website, address, likes, ratings,
opening status. This used to mean driving a real browser: slow, heavy, and it
broke every time Facebook changed its CSS. Both engines here read Facebook's
own page payload instead, so neither depends on how the page looks.

**The holes in it.** Facebook pages very often list a website but *no email* —
so a scraped list comes back empty in exactly the column you needed. Contact
enrichment visits the website Facebook *did* list, finds the address there,
and scores how much to trust it. In testing that turned about half of those
otherwise-dead records into usable contacts.

---

## 🚀 Two engines, one result

**Both take the same URLs, return the same fields, and run the same
extraction.** They differ only in how the page is requested.

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
# 🌐 HTTP — one page or many
from facebook_page_info_scraper import scrape_page, scrape_pages

page  = scrape_page("https://www.facebook.com/examplepage")
pages = scrape_pages(urls, threads=16)

print(page["email"])        # hello@example.com
print(page["page_likes"])   # 12,480

# 🎭 Browser — always a batch, never one at a time
from facebook_page_info_scraper.spider import run

run(urls, threads=8)                    # -> pages_browser.jsonl
run(urls, threads=8, headless=False)    # watch it work
```

From the command line:

```bash
python scrape.py urls.txt --threads 24 --out output.json
python -m facebook_page_info_scraper.spider urls.txt --threads 8 --headed
```

All options:

```python
scrape_page(url,   want_about=True, timeout=25)
scrape_pages(urls, threads=16, want_about=True, timeout=25)

run(urls, threads=8,                   # pages rendered at once, no cap
    out="pages_browser.jsonl",
    settle_ms=2000,                    # pause after load before reading
    headless=True)
```

`want_about=False` reads only the page header — faster, but no email or phone.

> The browser engine downloads Chromium (~150 MB) the first time it runs —
> pip cannot fetch browser binaries, so it happens on first use. One time
> only.

---

## 📧 Contact enrichment

Facebook pages very often list a **website but no email**. Enrichment visits
that website and recovers the missing contact.

```python
from facebook_page_info_scraper import scrape_pages, enrich_records

records = scrape_pages(urls, threads=16)
records = enrich_records(records, threads=8)

records[0]["enriched_email"]        # hello@example.com
records[0]["enriched_confidence"]   # high
```

It only touches records that need it — a page that already has an email is
skipped, and sites shared by several pages are fetched once.

### How it works

<p align="center">
<img src="https://raw.githubusercontent.com/wael-sudo2/facebook-page-info-scraper/main/docs/enrichment-flow.png"
     alt="Enrichment flow: fetch the homepage; retry bot-challenged sites with a browser TLS
          fingerprint; fall back to /contact-style pages; decide company inbox versus person;
          score every candidate into enriched_email with confidence and reasons."
     width="760">
</p>

Both marked steps ship with the package. The fingerprint retry happens on its
own; the role/person check is the only thing you switch on, and it needs just
an API key. Leave it off and every address is still found and scored — only
the `role` / `personal` label is left as `unknown`.

### Nothing is thrown away

Every address found comes back **with its score and the reasons behind it**,
so you pick your own threshold rather than trusting ours:

```python
{
  "email": "hello@example.se",
  "type": "role",              # role | personal | unknown
  "type_source": "deepseek",   # who decided that: provider | shape | none
  "confidence": "high",
  "score": 9,
  "source": "mailto",          # mailto | text
  "found_on": "https://example.se/kontakt",
  "reasons": [
    "mailto link",
    "same brand, different TLD",
    "role address (via deepseek)"
  ]
}
```

That matters because the obvious filters are wrong. Rejecting a different
TLD would discard `hello@example.se` found on `example.com` — which is the
same company.

| signal | score |
|---|---|
| email domain matches the site | **+4** |
| same brand, different TLD | **+3** |
| found in a `mailto:` link | **+3** |
| a company inbox rather than a person | **+2** |
| a freemail address (gmail, outlook …) | **+1** |
| domain unrelated to the site | **−3** |
| domain does not resolve in DNS | **−4** |

`high` ≥ 6 · `medium` ≥ 3 · `low` below that.

### Company inbox, or a person?

`info@example.com` is a company inbox. `anna@example.com` is a person.
Mailing the first is ordinary business; the second is personal data under
GDPR — so enrichment labels which is which, and never guesses when it cannot
tell.

There is no word list, in any language. A list can never cover them all — an
early version of this package missed `customerservice`, and would never have
contained the Finnish `asiakaspalvelu` or the Dutch `klantenservice`. A
language model answers the question directly instead.

**Nothing extra to install** — set an API key and switch it on:

```python
enrich_records(records, use_llm=True)                       # picks up your key
enrich_records(records, use_llm=True, provider="deepseek", model="deepseek-v4-flash")  # or choose
```

| provider | environment variable | default model |
|---|---|---|
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |

Whichever key is present is used. One request covers a whole batch, nothing
is written to disk, and if the call fails the run continues with the type
reported as `unknown`. With no key at all, enrichment still finds and scores
every address — only the `role` / `personal` label is left as `unknown`.

### What you get back
<details>
<summary><b>Sites that block you</b></summary>

A small share of sites answer with a bot challenge instead of their page.
Those get retried automatically with a real browser's TLS fingerprint — no
setup, it ships with the package. Anything still refusing after that is
reported as `challenged`: alive and blocking you, which is a very different
thing from a dead domain.

How often this is needed varies a lot. A probe of 100 sites measured 7%
challenged; re-testing the same sites later found only one still challenging.
Treat any single measurement as a snapshot.

</details>

<details>
<summary><b>Checking a run — <code>summarise_enrichment()</code></b></summary>

```python
from facebook_page_info_scraper import summarise_enrichment

summarise_enrichment(records)
```

```python
{
  "records": 40,
  "attempted": 40,
  "found_email": 22,
  "by_confidence": {"high": 13, "medium": 5, "low": 4},
  "by_tier": {"requests": 39, "curl_cffi": 1},
  "unreachable": 11,        # dead domain, expired cert, 404 …
  "no_contact": 7,          # site loaded, no email anywhere
  "challenged": 0,
  "hint": None              # set when something in the environment is missing
}
```

</details>

### Fields added to each record

Your original fields are never overwritten — enrichment only adds.

| field | type | description |
|---|---|---|
| `enriched_email` | `str` | Best candidate found. Absent when none was. |
| `enriched_email_type` | `str` | `role`, `personal` or `unknown` |
| `enriched_confidence` | `str` | `high`, `medium` or `low` |
| `enrichment` | `dict` | The full result — see below |
| `_enrich_status` | `str` | `ok`, `no_contact_found`, `challenged`, `unreachable` |
| `_enrich_tier` | `str` | `requests` or `curl_cffi` |
| `_enrich_email_source` | `str` | `mailto` or `text` — how the winner was found |

The `enrichment` dict holds everything, not just the winner:

| key | type | description |
|---|---|---|
| `website` | `str` | The URL that was visited |
| `emails` | `list` | **Every** candidate, best first, each with its score and reasons |
| `phones` | `list` | Up to 3 numbers from `tel:` links |
| `status` | `str` | Same as `_enrich_status` |
| `tier` | `str` | Which fetch tier succeeded |
| `fetch_outcome` | `str` | `ok`, `challenged`, `forbidden`, `not_found`, `timeout`, `dns`, `error`, `http_NNN` |
| `error` | `str` | Exception name, when one occurred |
| `pages_fetched` | `int` | Requests spent on this site |
| `found_on_path` | `str` | Which contact path paid off, if one did |
| `seconds` | `float` | Wall time for this site |

`fetch_outcome` is the one to read when a site fails — it separates a dead
domain (`dns`) from an expired certificate (`error`), a missing page
(`not_found`) and a site that is up and refusing you (`challenged`).

### Options

```python
enrich_records(records,
               threads=8,
               timeout=12,
               only_missing_email=True,
               follow_contact_pages=True,
               use_fingerprint=True,
               use_llm=False,
               provider=None,
               model=None)
```

| option | default | what it does |
|---|---|---|
| `threads` | `8` | Sites fetched in parallel. These are other people's servers, and each site is hit at most a few times — raise it for large lists, but stay civil. |
| `timeout` | `12` | Seconds per request. Lower it to move past slow or half-dead hosts faster. |
| `only_missing_email` | `True` | Skip records that already have an email. Set `False` to re-check every record, e.g. to cross-check what Facebook listed. |
| `follow_contact_pages` | `True` | When the homepage has no email, try `/contact`, `/kontakt`, `/contacto`, `/impressum` and friends. This is what lifts the hit rate from ~35% to ~50% — set `False` for homepage-only, which is much faster and much less thorough. |
| `use_fingerprint` | `True` | Retry bot-challenged sites with a real browser's TLS fingerprint. Set `False` to skip the retry and report them as `challenged`. |
| `use_llm` | `False` | Label each address `role` or `personal`. Needs an API key; off by default because it costs money. Everything else works either way. |
| `provider` | `None` | `"deepseek"` or `"openai"`. `None` picks whichever key is set. |
| `model` | `None` | Override the provider's default model — `deepseek-chat` or `gpt-4o-mini`. |

One site at a time, if you prefer:

```python
from facebook_page_info_scraper import enrich_site

enrich_site("https://example.com")
enrich_site("https://example.com", use_llm=True, provider="openai")
```

`enrich_site` takes the same options as `enrich_records`, minus `threads` and
`only_missing_email` — plus `session=` if you want to supply your own
`requests.Session`. It returns the result dict directly instead of attaching
it to a record.

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

<details>
<summary><b>Every field, with types</b></summary>

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

</details>

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

## 🔮 Roadmap

The first piece of the AI layer has landed: enrichment can ask a model
whether an address is a company inbox or a person, in any language. It sits
*behind* the deterministic work, not in front of it — every address is found
and scored by rules, and the model answers only the one question rules
cannot: what a word means in a language nobody enumerated.

Next along the same line is free-text extraction for unlabelled About rows
in languages whose formatting conventions vary. Rules first, model only
where rules come up empty.

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
