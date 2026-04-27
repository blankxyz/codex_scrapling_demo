# www-zhengguannews-cn-list-17 analysis

- Source URL: `https://www.zhengguannews.cn/list/17.html`
- Slug: `www-zhengguannews-cn-list-17`
- Homepage observed separately: `https://www.zhengguannews.cn/`
- Evidence:
  - [analysis_outputs/www-zhengguannews-cn-list-17/_probe.json](/home/blank/bohui_lab/codex_scrapling_demo/analysis_outputs/www-zhengguannews-cn-list-17/_probe.json)
  - [analysis_outputs/www-zhengguannews-cn-list-17/_detail_probe.json](/home/blank/bohui_lab/codex_scrapling_demo/analysis_outputs/www-zhengguannews-cn-list-17/_detail_probe.json)

## Summary

`www.zhengguannews.cn` is a multi-column portal homepage. For spider generation, the stable unit is a column page such as `list/17.html`, not the homepage itself.

- Homepage nav exposes channel entrypoints such as `list/16.html` (`郑州`), `list/17.html` (`独家`), `list/63.html` (`区县`), `list/19.html` (`河南`) and others.
- `list/17.html` is server-rendered on page 1.
- Infinite-scroll pagination exists and uses a stable JSON endpoint.
- Recommended runtime tier: `fetcher-html`
- Recommended session: `AsyncFetcher`

Decision:
`Tier B — the first-page list is present in the initial server-rendered HTML, so first-page extraction does not require a browser session.`

## List page findings

Rendered list structure:

- Main list wrapper: `.item-list #scrolllist`
- Item selector: `.item-list #scrolllist > .col-4`
- Link selector: `.item-list #scrolllist > .col-4 .video-title > a[href]`
- Title selector: `.item-list #scrolllist > .col-4 .video-title > a`
- Publish time selector: `.item-list #scrolllist > .col-4 .creat-time`
- Wait selector: `.item-list #scrolllist > .col-4 .video-title > a[href]`
- First-page visible item count: `15`

Notes:

- The page title stays generic as `正观新闻 - 居中 守正 观天下`; the active nav item and URL identify the column as `独家`.
- The first list item is a专题页: `/special/2117.html`.
- The remaining visible items are mostly `/news/<id>.html` article links.
- The list is already present in the HTML response body; no scroll is needed for page 1.

First-page titles in DOM order:

1. 铭记历史 山河见证
2. 新大众文艺浪尖上，做文化的“摆渡人” ——专访北大教授张颐武
3. 老手艺的守护人：一双“泥腿子”，踏出郑州非遗活地图
4. 老河大东门，一家21岁书店的最后守望
5. 程韬光的文化跋涉：用三种身份，读懂一座城
6. 送别“当代福尔摩斯”李昌钰：9年前曾做客郑报，一生践行 “人生没有不可能”
7. 《人民的名义》“程度”卷入债务纠纷
8. “梅姨”落网！寻子父亲申军良哽咽：“如果不找到她，我死不瞑目”
9. 平均年龄超70岁！郑州火车站的“银发雷锋团”，暖了亿万赶路人
10. 追踪｜男子遭前岳父砍杀身亡 凶手获死缓并限制减刑 受害方家属称将继续申诉
11. 墨白长篇小说《扑克牌的N种玩法》研讨会在郑州举行
12. 万家灯火背后的春运“守夜人”：凌晨4点的闹钟，为谁而响？
13. 文学归根处，中原起新声——豫籍文艺名家“归根还巢”两年记
14. 90 后乡村 “面子特派员”：跨越百里，把年味和孝心送到家
15. 鳌太线上的“生死劫”

## Network findings

Observed pagination request after scrolling:

- `POST /data`
- Post body:
  `m=nlist&data[recmd]=0&data[pageindex]=2&data[pagesize]=15&data[cateid]=17`

Observed response shape:

- Row array path: `data`
- Row fields:
  - detail URL: `url`
  - title: `title`
  - publish time: `reltime`
  - column/category: `catename`

Notes:

- No browser-only token was observed.
- The endpoint is stable enough to support pagination later, but page 1 does not need it.
- The homepage probe also showed that the site is a portal page aggregating many columns rather than a single flat feed.

## Detail page findings

Working sample URL:
`https://wap.zhengguannews.cn/html/news/485662.html`

Selectors:

- Title: `.news-main h2.news-title`
- Meta: `.news-main .news-maker.laiyuan, .news-main .news-mate`
- Content: `.news-main .news-text`
- Wait selector: `.news-main h2.news-title, .news-main .news-text`

Meta extraction:

- Publish time regex: `(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})`
- Source regex: not observed as a stable separate field
- Views regex: not observed

Content notes:

- Desktop URLs under `https://www.zhengguannews.cn/news/<id>.html` are not uniformly reliable; some items return `该新闻不存在`.
- The mobile detail URL pattern `https://wap.zhengguannews.cn/html/news/<id>.html` rendered a stable article body in the probe.
- The article body is concentrated in `.news-main .news-text`.
- Editor review lines such as `编辑`, `二审`, `三审` appear after the main content and should usually be excluded from the body payload.
- Related news is rendered below the article body and should not be merged into `content`.

## Spider recommendation

Use `AsyncFetcher` for a first-page-only spider.

- Reason: page 1 is available in initial HTML.
- Normalize standard article detail URLs from `/news/<id>.html` to `https://wap.zhengguannews.cn/html/news/<id>.html`.
- Keep a branch for `/special/<id>.html` if专题页 also needs collecting; otherwise filter those out.
- If pagination is added later, `POST /data` is the observed continuation path.
