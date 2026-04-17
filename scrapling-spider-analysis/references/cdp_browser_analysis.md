# CDP Browser Analysis Notes

## CDP Connection

Use local Chrome CDP when the user has started it. Default to performing the real CDP action directly instead of probing health endpoints first:

```text
http://127.0.0.1:9222
```

If the direct connection or tab action fails, report the concrete error and only then decide whether to debug CDP further or switch to another local browser-rendered method. Browser observations should include rendered DOM and network responses.

When Python is needed for browser probing in this repo, use only the local virtualenv interpreter:

```text
.venv/bin/python
```

Do not call `python` or `python3` for analysis helpers.

Prefer reusing the local generic probe before inventing a new site-specific script:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
.venv/bin/python tools/cdp_probe.py \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

Write a one-off probe only when this generic tool cannot expose the interaction you need.

## Evidence Rules

- Browser-captured network requests are valid evidence.
- Browser-rendered DOM is valid evidence.
- A curl command copied by the user from DevTools is valid as a clue, but do not rely on replaying it as the primary analysis method.
- Search engine snippets are not evidence for this skill.
- Direct target HTTP requests outside the browser are not evidence for this skill.

## Things To Extract

List page:

- `document.title`
- visible column heading
- item/link selectors
- first-page title list
- publish-time text
- list API/XHR request and response shape

Detail page:

- title selector
- metadata selector
- content selector
- publish time/source/view regexes
- duplicate content behavior

## Common Government Site Pattern

Some sites build list data with a browser-only token:

```text
/common/search/<channelId>?<dynamic_token>&_isAgg=true&_isJson=true&_pageSize=20&_template=index&page=1
```

For spider generation, prefer Scrapling browser `capture_xhr="/common/search/"` instead of reconstructing the token.

## Output Discipline

Always save both:

- `analysis_outputs/${SLUG}_analysis.md`
- `analysis_outputs/${SLUG}_analysis.json`

Keep JSON stable enough for the generator skill to read automatically.
