# Scrapling Spider Analysis: tianya-tv-cat-jiankangkepu

## Summary

- Source URL: `https://www.tianya.tv/cat/%e5%81%a5%e5%ba%b7%e7%a7%91%e6%99%ae`
- Method: Chrome CDP page target plus browser-observed DOM/network capture.
- Search engines: not used.
- Non-browser target fetching: not used as primary evidence.
- Page title / column: `健康科普 – 海南丽声` / `健康科普`
- First page count: `6` items
- List API found: none
- Detail type observed: WordPress video post with embedded mp4

## Rendered List DOM

- Item selector: `#recent-content > div[id^="post-"]`
- Link selector: `#recent-content > div[id^="post-"] h2.entry-title a`
- Thumbnail link selector: `#recent-content > div[id^="post-"] a.thumbnail-link`
- Title selector: `#recent-content > div[id^="post-"] h2.entry-title a`
- Category selector: `#recent-content > div[id^="post-"] .entry-category a`
- Views selector: `#recent-content > div[id^="post-"] .entry-views .view-count`
- Likes selector: `#recent-content > div[id^="post-"] .sl-button`
- Wait selector: `#recent-content > div[id^="post-"] h2.entry-title a`
- Pagination: not observed on the current category page

## First Page Titles

1. [video] 女生经期如何正确洗澡？ - https://www.tianya.tv/1922.html - 浏览 (55) / 喜欢(15)
2. [video] 女性月经量“突然减少”是因为什么？ - https://www.tianya.tv/1919.html - 浏览 (46) / 喜欢(17)
3. [video] 月经来之前的征兆有哪些？ - https://www.tianya.tv/1917.html - 浏览 (44) / 喜欢(15)
4. [video] 月经提前VS月经推迟哪个更可怕？ - https://www.tianya.tv/1915.html - 浏览 (43) / 喜欢(17)
5. [video] 来月经可以上体育课吗？ - https://www.tianya.tv/1913.html - 浏览 (44) / 喜欢(16)
6. [video] 月经推迟竟然才是“正常的”吗？ - https://www.tianya.tv/1905.html - 浏览 (42) / 喜欢(15)

## Browser-Observed Network

- No browser-observed XHR/fetch request returned list rows for this category page.
- Observed auxiliary requests:

## Detail Page Template

- Sample URL: `https://www.tianya.tv/1922.html`
- Title selector: `h1.entry-title`
- Meta selector: `.entry-meta`
- Author selector: `.entry-author a`
- Publish time selector: `.entry-date`
- Views selector: `.entry-views .view-count`
- Content selector: `.entry-content`
- Video selector: `video.wp-video-shortcode source[src], video.wp-video-shortcode[src]`
- Publish time regex: `(\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{2})`
- Views regex: `浏览\((\d+)\)`
- Wait selector: `h1.entry-title`
- Content duplicated: `false`
- Observed media source: `https://www.tianya.tv/wp-content/uploads/2026/04/【科普285】超重要！女生如何正确洗澡？成片.mp4?_=1`

## Spider Strategy

- Generated production spider can use `FetcherSession` only.
- Crawl the category HTML directly and follow real detail links.
- No browser rendering is required for production crawling of this page.
- Treat this category as video content: extract `video_url` from the `<video>`/`<source>` element on detail pages.
- No pagination control was visible on the current page; if other category pages show page numbers later, inspect `.pagination .page-numbers`.

## Evidence

- Raw browser probe: `analysis_outputs/_tianya_tv_cat_health_probe.json`
