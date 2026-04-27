# www-hngrrb-cn-shizheng analysis

- Source URL: `http://www.hngrrb.cn/shizheng/`
- Slug: `www-hngrrb-cn-shizheng`
- Evidence: CDP probe saved at [analysis_outputs/_www-hngrrb-cn-shizheng_probe.json](/home/blank/bohui_lab/codex_scrapling_demo/analysis_outputs/_www-hngrrb-cn-shizheng_probe.json)

## Summary

This is a server-rendered list-to-detail news page for the `时政` channel on `www.hngrrb.cn`.

- Page title: `时政- 河南工人日报 河南工人日报官方网站`
- Column name: `时政`
- Recommended runtime tier: `fetcher-html`
- Recommended session: `AsyncFetcher`
- List API: not observed

Decision:
`Tier B — list content is present in the initial server-rendered HTML document and no browser-only list token or JSON list API was observed in CDP network logs.`

## List page findings

Rendered list structure:

- Main container: `main.list-page`
- Featured item: `.first-news`
- Regular list wrapper: `.list-page-box .news-page`
- Regular list item: `.list-page-box .news-page > .media`
- Link selector: `a[href*='/shizheng/']`
- Title selector: `.news-ds p, .media-heading`
- Publish time / source text: `.clear > span.left`
- Wait selector: `main.list-page .list-page-box .news-page`

Notes:

- The first large featured card is separate from the regular `.media` list.
- The featured card exposes title and detail link but not publish time in the list block.
- Pagination exists in HTML. Observed next-page link: `/shizheng/list_2.html`
- A visible `加载查看更多` link points to that next HTML page.

First-page titles in DOM order:

1. 丙午年黄帝故里拜祖大典隆重举行
2. 我国服务贸易稳居全球前列
3. 河南一季度农险为453.7万户农户提供风险保障1172.05亿元
4. 河南省级碳计量中心建设工作全面启动
5. 中国报业经营管理大会在贵州兴义召开
6. 2026年河南省事业单位招聘联考启动
7. 国务院印发《关于推进服务业扩能提质的意见》
8. 全国5G基站总数已达495.8万个
9. 一季度央企固定资产投资同比增23.5%
10. 三部门发文破解“工厂开窗还是关窗生产”执法标准不一难题
11. 一季度我省GDP达15914.52亿元 同比增长5.2%

## Network findings

No list JSON API or browser-tokenized list XHR was observed.

Observed XHRs are unrelated to list extraction:

- `POST /ajax/?t=...` returning current paper image URL
- `POST /ajax/?t=...` returning click-tracking success

This means the article list is coming from initial HTML, not from post-load JSON.

## Detail page findings

Sample URL:
`http://www.hngrrb.cn/shizheng/202604/120519.html`

Selectors:

- Title: `main.post-page .post-main > h2`
- Meta: `main.post-page .post-main .post-share > span.left`
- Content: `main.post-page .post-main .post-text`
- Wait selector: `main.post-page .post-main h2`
- Editor block: `.news-info`
- Disclaimer block: `.category`

Meta extraction:

- Publish time regex: `(\\d{4}年\\d{2}月\\d{2}日\\d{2}:\\d{2})`
- Source regex: `来源：\\s*([^\\s]+)`
- Views regex: not observed

Content notes:

- Main article body is concentrated in `.post-text`.
- No duplicated article body container was observed in the sampled detail page.
- The body can include a leading image followed by `<p>` paragraphs.

## Spider recommendation

Use `AsyncFetcher`.

- Reason: HTML already contains the list and detail payloads needed for extraction.
- `google_search=false`
- `network_idle=false`
- Pagination was not analyzed beyond existence because only the first page was requested.

Practical extraction split:

- Featured card: `.first-news`
- Regular list items: `.list-page-box .news-page > .media`

If you want one spider to cover both blocks, union selectors are workable:

- Item selector: `main.list-page .first-news, main.list-page .list-page-box .news-page > .media`
- Title selector: `.news-ds p, .media-heading`
