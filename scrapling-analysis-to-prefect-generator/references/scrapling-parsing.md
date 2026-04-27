# Scrapling Parsing Skill

You are an expert at using the Scrapling Python library for HTML parsing and web scraping. When helping the user write or debug Scrapling parsing code, follow the patterns, APIs, and best practices below precisely.

## Installation

```bash
pip install scrapling
scrapling install  # optional: installs browser dependencies for fetchers
```

Requires Python 3.9+.

## Core Classes

### `Selector` — the main parsing class

```python
from scrapling.parser import Selector

# Parse an HTML string
page = Selector(html_content)

# With base URL (enables absolute URL resolution) and adaptive tracking
page = Selector(html_content, url='https://example.com', adaptive=True)
```

All selection methods on `Selector` return either:
- A **`Selectors`** list (multiple elements) — for `.css()`, `.xpath()`, `.find_all()`
- A **`Selector`** instance (single element) — for `.css_first()`, `.xpath_first()`, `.find()`

### `Selectors` — list of elements

Subclasses Python's `list`, so all list operations work. Calling `.css()`, `.xpath()` etc. on a `Selectors` object maps the call across all elements.

### `TextHandler` — returned by text methods

A `str` subclass. All string operations (`split`, `replace`, `strip`, slicing) return `TextHandler` again. Adds `.re()` and `.re_first()` for in-place regex extraction.

### `AttributesHandler` — returned by `.attrib`

A read-only dict-like object for element attributes. Additional methods:
- `.search_values(keyword)` — search attribute values
- `.json_string()` — serialize to JSON string

---

## Selection Methods

### CSS Selectors

```python
elements = page.css('div.product')          # → Selectors
element  = page.css_first('div.product')    # → Selector  (~10% faster for single)

# Pseudo-elements (Scrapy-style)
texts = page.css('h1::text').getall()       # all text nodes
href  = page.css('a::attr(href)').get()     # attribute value
```

### XPath Selectors

```python
elements = page.xpath('//div[@class="item"]')        # → Selectors
element  = page.xpath_first('//div[@class="item"]')  # → Selector (faster)

# XPath text/attribute extraction
texts = page.xpath('//h1/text()').getall()
hrefs = page.xpath('//a/@href').getall()
```

### BeautifulSoup-style Find

```python
# Find first matching element
el = page.find('div', class_='product', id='main')

# Find all matching elements
els = page.find_all('a')
```

### Regex Extraction

```python
# On the page or any element
emails    = page.re(r'[\w\.-]+@[\w\.-]+\.\w+')          # → list[TextHandler]
first_url = page.re_first(r'https?://[^\s"\']+')         # → TextHandler | None

# Chain on XPath/CSS text results
names = page.xpath('//span/text()').re(r'Name:\s*(.*)')
```

---

## Data Extraction

### Text

```python
text     = element.text                     # direct text (TextHandler)
all_text = element.get_all_text()           # recursive, separator=' '
all_text = element.get_all_text(separator='\n', ignore_tags=['script', 'style'])
```

### Attributes

```python
href  = element.attrib['href']              # direct access
href  = element.attrib.get('href', '')      # safe access
attrs = element.attrib                      # AttributesHandler (dict-like)
results = element.attrib.search_values('cdn')
```

### HTML Content

```python
inner_html  = element.html_content         # inner HTML string
pretty      = element.prettify()            # formatted HTML
```

### `.get()` / `.getall()` — for pseudo-element results

Use these when the selector extracts text/attribute nodes (not elements):

```python
title  = page.css('h1::text').get()        # first result or None
titles = page.css('h1::text').getall()     # list of all results
href   = page.css('a::attr(href)').get()
hrefs  = page.css('a::attr(href)').getall()
```

---

## DOM Navigation

```python
parent    = element.parent                  # immediate parent Selector
ancestors = element.path                    # list of ancestor tag names
children  = element.children               # child Selectors
siblings  = element.siblings               # sibling Selectors
next_el   = element.next_element           # next sibling
prev_el   = element.previous_element       # previous sibling
below     = element.below_elements         # all descendants
tag       = element.tag                    # tag name string, e.g. "div"

# Find ancestor matching a condition
article = element.find_ancestor(lambda e: e.tag == 'article')
```

---

## Smart / Adaptive Features

### `find_similar()` — structural siblings

Finds all elements with the same structural fingerprint as a given element. Useful for repeated items (product cards, table rows):

```python
first_card = page.css_first('.product-card')
all_cards  = first_card.find_similar()
```

### Adaptive Tracking (`adaptive=True`)

When enabled, Scrapling stores element fingerprints (tag, text, attributes, surrounding context) in a local SQLite database. On future parses it can re-locate elements even if the page structure changes slightly. Use for long-running scrapers that need resilience to layout changes.

---

## Common Patterns

### Extract a list of items

```python
from scrapling.parser import Selector

page = Selector(html)
products = []
for card in page.css('.product-card'):
    products.append({
        'name':  card.css_first('h2::text').get(),
        'price': card.css_first('.price::text').get(),
        'url':   card.css_first('a::attr(href)').get(),
    })
```

### Scrape a table

```python
rows = page.css('table tbody tr')
data = []
for row in rows:
    cols = row.css('td::text').getall()
    data.append(cols)
```

### XPath with conditions

```python
links = page.xpath('//a[contains(@class, "external")]/@href').getall()
bold  = page.xpath('//p//b/text()').getall()
```

### Regex on text nodes

```python
# Extract dates from anywhere on the page
dates = page.re(r'\d{4}-\d{2}-\d{2}')

# Chain regex on a specific node's text
page.css('div.info::text').re(r'Phone:\s*([\d\-]+)')
```

### Find one, get all similar

```python
# Great when there's no clean shared class
sample  = page.css_first('ul.results li')
all_lis = sample.find_similar()
texts   = [li.text for li in all_lis]
```

---

## Performance Tips

- Prefer `css_first` / `xpath_first` over `css` / `xpath` when you only need one element — ~10% faster.
- Use `::text` and `::attr(name)` pseudo-elements with `.get()` / `.getall()` instead of chaining `.text` / `.attrib` for cleaner one-liners.
- `adaptive=True` adds overhead from SQLite; only enable it when structural resilience is needed.

---

## What NOT to do

- Do NOT import `Selector` from `lxml` or `parsel` — always use `from scrapling.parser import Selector`.
- Do NOT call `.text` on a `Selectors` list; iterate or use `::text` pseudo-elements.
- Do NOT use `.get()` on an element Selector; `.get()` is only for text/attribute pseudo-element results.
- Do NOT assume `.css()` returns `None` on no match — it returns an empty `Selectors` list; use `.css_first()` which returns `None`.
