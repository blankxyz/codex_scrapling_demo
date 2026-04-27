# Scrapling Fetching Skill

You are an expert at using Scrapling's fetching layer. When writing or debugging Scrapling fetching code, follow the APIs, patterns, and best practices below precisely.

## Installation

```bash
pip install "scrapling[fetchers]"
scrapling install          # downloads browser binaries for StealthyFetcher / DynamicFetcher
pip install "scrapling[all]"   # everything including Spider framework
```

---

## Choosing the Right Fetcher

| Fetcher | Speed | JS support | Cloudflare bypass | When to use |
|---|---|---|---|---|
| `Fetcher` | Very fast | No | No | Public APIs, plain HTML pages |
| `FetcherSession` | Very fast | No | No | Multi-request flows needing cookie persistence |
| `StealthyFetcher` | Medium | No | Yes (auto) | Cloudflare / bot-protected pages without JS requirement |
| `DynamicFetcher` | Slow | Yes | Yes (auto) | Pages that require JS execution |
| Async variants | Same as above | Same | Same | Concurrent scraping |

---

## Fetcher — fast HTTP requests

Uses TLS fingerprint impersonation, no real browser.

```python
from scrapling.fetchers import Fetcher

# GET
page = Fetcher.get('https://example.com/', timeout=30)

# POST (form data or JSON)
page = Fetcher.post('https://example.com/api', json={'key': 'value'})
page = Fetcher.post('https://example.com/form', data={'field': 'val'})

# PUT / DELETE
page = Fetcher.put('https://example.com/resource/1', json={...})
page = Fetcher.delete('https://example.com/resource/1')
```

### Key parameters (all methods)

```python
Fetcher.get(
    url,
    params={'q': 'query'},          # query string parameters
    headers={'X-Custom': 'value'},
    cookies={'session': 'abc'},
    timeout=30,                     # seconds; default 30
    follow_redirects=True,
    max_redirects=10,
    retries=3,                      # default 3
    retry_delay=1,                  # seconds between retries
    proxy='http://user:pass@host:port',
    auth=('username', 'password'),  # HTTP Basic auth
    verify=True,                    # SSL verification
    impersonate='chrome',           # TLS fingerprint: 'chrome', 'firefox135', etc.
    http3=False,                    # enable HTTP/3
    stealthy_headers=True,          # auto-add anti-detection headers (default True)
)
```

---

## FetcherSession — persistent sessions

Maintains cookies/state across multiple requests. Use as context manager.

```python
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as session:
    login = session.post('https://example.com/login', data={'user': '...', 'pass': '...'})
    page  = session.get('https://example.com/dashboard')  # cookies carried over
    data  = page.css('.stat::text').getall()
```

### ProxyRotator

```python
from scrapling.fetchers import ProxyRotator, FetcherSession

rotator = ProxyRotator(['http://proxy1:8080', 'http://proxy2:8080'])
with FetcherSession(proxy_rotator=rotator) as session:
    page = session.get('https://example.com/')
```

---

## StealthyFetcher — Cloudflare / bot-protection bypass

Uses a modified Firefox (Camoufox) with stealth patches. Automatically solves Cloudflare Turnstile.

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    'https://example.com',
    headless=True,
    network_idle=True,              # wait until network is idle
)
titles = page.css('h1::text').getall()
```

### Key parameters

```python
StealthyFetcher.fetch(
    url,
    headless=True,                  # headless browser
    solve_cloudflare=True,          # auto-solve Turnstile (default True)
    network_idle=False,             # wait for network idle before returning
    disable_resources=True,         # block images/fonts for speed
    block_webrtc=True,              # prevent WebRTC IP leaks
    hide_canvas=True,               # defeat canvas fingerprinting
    allow_webgl=True,
    google_search=False,            # spoof Google referrer
    timeout=30,
    wait=2000,                      # ms to wait after load, OR a CSS selector string
    wait_selector='.content',       # wait for this selector to appear
    wait_selector_state='visible',  # 'attached' | 'visible' | 'hidden' | 'stable'
    page_action='window.scrollTo(0, document.body.scrollHeight)',  # JS to run
    extra_headers={'Accept-Language': 'en-US'},
    blocked_domains=['ads.example.com'],
    proxy='http://user:pass@host:port',
    adaptive=True,                  # enable adaptive element tracking
)
```

---

## DynamicFetcher — full browser automation (Playwright/Chromium)

Use when the page requires JavaScript to render its content.

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    'https://example.com/',
    headless=True,
    network_idle=True,
)
data = page.xpath('//span[@class="value"]/text()').getall()
```

Parameters are identical to `StealthyFetcher.fetch()`.

---

## Async fetchers

All fetchers have async equivalents. Use when making concurrent requests.

### AsyncFetcher

```python
import asyncio
from scrapling.fetchers import AsyncFetcher

async def scrape():
    page = await AsyncFetcher.get('https://example.com/')
    return page.css('.title::text').getall()

asyncio.run(scrape())
```

### AsyncStealthySession — concurrent stealth requests

```python
import asyncio
from scrapling.fetchers import AsyncStealthySession

async def scrape_many(urls):
    async with AsyncStealthySession(max_pages=10) as session:
        tasks = [session.fetch(url) for url in urls]
        pages = await asyncio.gather(*tasks)
    return pages

pages = asyncio.run(scrape_many(['https://a.com', 'https://b.com']))
```

`max_pages` controls the browser tab pool size.

---

## Response object

All fetchers return a **`Response`** object, which extends `Selector` (the parsing class). All parsing methods are available directly on the response.

```python
page = Fetcher.get('https://example.com/')

# HTTP metadata
page.status          # int, e.g. 200
page.reason          # str, e.g. "OK"
page.url             # final URL after redirects
page.headers         # response headers dict
page.request_headers # headers sent in the request
page.cookies         # response cookies dict
page.body            # raw bytes
page.encoding        # detected encoding
page.history         # list of redirect responses
page.meta            # extra metadata (e.g. proxy used)
page.captured_xhr    # list of captured XHR Response objects

# Parsing (inherited from Selector — use directly)
page.css('.item')
page.css_first('h1::text').get()
page.xpath('//a/@href').getall()
page.find('div', class_='main')
page.re(r'\d+')
```

---

## Common patterns

### Simple page scrape

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')
for el in page.css('.quote'):
    print(el.css_first('.text::text').get())
    print(el.css_first('.author::text').get())
```

### Login then scrape (session)

```python
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as s:
    s.post('https://example.com/login', data={'user': 'u', 'pass': 'p'})
    page = s.get('https://example.com/protected')
    data = page.css('.data::text').getall()
```

### Bypass Cloudflare

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    'https://protected-site.com',
    headless=True,
    solve_cloudflare=True,
    network_idle=True,
    disable_resources=True,
)
```

### Wait for dynamic content

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    'https://spa-site.com',
    wait_selector='.loaded-content',
    wait_selector_state='visible',
)
```

### Concurrent async scraping

```python
import asyncio
from scrapling.fetchers import AsyncFetcher

async def scrape_all(urls):
    tasks = [AsyncFetcher.get(u) for u in urls]
    pages = await asyncio.gather(*tasks)
    return [p.css_first('title::text').get() for p in pages]

titles = asyncio.run(scrape_all(['https://a.com', 'https://b.com']))
```

### Capture XHR / API calls

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch('https://example.com/', network_idle=True)
for xhr in page.captured_xhr:
    print(xhr.url, xhr.status)
```

---

## Spider framework (multi-session orchestration)

```python
from scrapling.spiders import Spider, Response, Request
from scrapling.fetchers import FetcherSession, AsyncStealthySession

class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com/']
    concurrent_requests = 10

    def configure_sessions(self, manager):
        manager.add('fast', FetcherSession(impersonate='chrome'))
        manager.add('stealth', AsyncStealthySession(headless=True), lazy=True)

    async def parse(self, response: Response):
        for link in response.css('a::attr(href)').getall():
            sid = 'stealth' if 'protected' in link else 'fast'
            yield Request(link, callback=self.parse_detail, sid=sid)

    async def parse_detail(self, response: Response):
        yield {'title': response.css_first('h1::text').get(), 'url': response.url}

result = MySpider().start()
result.items.to_json('output.json')
```

---

## What NOT to do

- Do NOT use `Fetcher` for pages that require JavaScript — use `DynamicFetcher`.
- Do NOT use `StealthyFetcher` or `DynamicFetcher` for simple public pages — they are slow; use `Fetcher`.
- Do NOT call `scrapling install` inside Python code; it is a CLI command run once after pip install.
- Do NOT create a new `StealthyFetcher` / `DynamicFetcher` instance per request in a loop — use `AsyncStealthySession` with `max_pages` for concurrent scraping.
- Do NOT access `.text` directly on a `Response` to get the raw HTML body; use `.body` (bytes) or `.html_content` (inner HTML of root element). For full document HTML use `str(page)`.
- Do NOT ignore `page.status` — always check for non-200 responses when reliability matters.
