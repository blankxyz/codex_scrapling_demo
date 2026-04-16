# Scrapling Spider Analysis: hkbtv-cn-common1858408493966991361

## Summary

- Source URL: `https://hkbtv.cn/#/common1858408493966991361?type=1858408493966991361`
- Method: Chrome CDP page target plus in-page browser fetch/XHR capture.
- Search engines: not used.
- Non-browser target fetching: not used as primary evidence.
- Page title / column: `要闻 - 海广网` / `要闻`
- First-page API record count: `20`
- First-page visible article count after flattening nested modules: `37`
- List API found: `POST https://hkbtv.cn/tv-station/api/article/list`
- Detail API found: `POST https://hkbtv.cn/tv-station/api/details/article`
- API pages observed: `23`

## Browser-Observed List API

- Observed URL: `https://hkbtv.cn/tv-station/api/article/list`
- Request body:
  - `page=1`
  - `limit=20`
  - `publishingPath=3`
  - `classifyCode=1858408493966991361`
  - `classifyLevel=1`
- JSON paths:
  - rows: `data.records`
  - nested articles: `data.records[].articles[]`
  - total: `data.total`
  - current page: `data.current`
  - pages: `data.pages`
  - title: `data.records[].articles[].title`
  - detail id: `data.records[].articles[].articleId`
  - detail type: `data.records[].articles[].articleType`
  - publish time: `data.records[].articles[].releaseTime`
  - source: `data.records[].articles[].sourceArticle`
  - image: `data.records[].articles[].coverMapAddress`
- URL building rule:
  - `https://hkbtv.cn/#/article?type=article&id={articleId}&articleType={articleType}`

## Rendered List DOM

- Route URL: `https://hkbtv.cn/#/common1858408493966991361?type=1858408493966991361`
- Mixed modules observed on the same page: `最新播报`, `新闻轮播`, `热点要闻`, and a single-article feed.
- Broad record selector: `.cont_item`
- Main card selector: `.module_card .list > .li`
- Main clickable selector: `.module_card .list > .li section.card`
- Main title selector: `.module_card .list > .li .label`
- Main publish time selector: `.module_card .list > .li .text span:last-child`
- Main source selector: `.module_card .list > .li .text .item_text`
- Single-card selector: `.module_card_box2 > .li section.card_list`
- Single-card title selector: `.module_card_box2 > .li .title`
- Single-card publish time selector: `.module_card_box2 > .li .text span:last-child`
- Wait selector: `.module_card .list > .li .label`
- Note: rendered cards do not expose stable `<a href>` URLs; article routes come from API `articleId` and `articleType`.

## First Page Titles

1. [最新播报] 2026年04月07日 14时12分 - 郑丽文率团抵达大陆参访 - https://hkbtv.cn/#/article?type=article&id=6439661907059168057&articleType=0
2. [最新播报] 2026年04月07日 11时08分 - 长征路上，有三个地方叫“瑞金” - https://hkbtv.cn/#/article?type=article&id=6439661907059168040&articleType=0
3. [最新播报] 2026年03月28日 20时31分 - 中菲举行南海问题双边磋商 - https://hkbtv.cn/#/article?type=article&id=6439661907059167559&articleType=0
4. [最新播报] 2026年03月25日 12时10分 - 国台办：统一后，台湾民众可以自驾直达北京 - https://hkbtv.cn/#/article?type=article&id=6439661907059167286&articleType=0
5. [最新播报] 2025年12月13日 15时26分 - 侵华日军暴行再添铁证！新一批731部队罪行档案今日公布 - https://hkbtv.cn/#/article?type=article&id=6439661907059160324&articleType=0
6. [最新播报] 2025年09月11日 14时11分 - 擎开放之旗 领服贸之先——从服贸会之变看中国服务业开放新标杆 - https://hkbtv.cn/#/article?type=article&id=6439661907059153233&articleType=0
7. [新闻轮播] 2026年04月12日 10时47分 - 两岸交流合作再进一程！中央台办受权发布十项措施 - https://hkbtv.cn/#/article?type=article&id=6439661907059168347&articleType=0
8. [新闻轮播] 2026年04月11日 23时03分 - 国家安全 头等大事 - https://hkbtv.cn/#/article?type=article&id=6439661907059168296&articleType=0
9. [新闻轮播] 2026年04月10日 17时10分 - 贯彻实施民族团结进步促进法 为实现中华民族伟大复兴凝聚磅礴法治力量 - https://hkbtv.cn/#/article?type=article&id=6439661907059168220&articleType=0
10. [新闻轮播] 2026年04月10日 17时10分 - 中华人民共和国民族团结进步促进法 - https://hkbtv.cn/#/article?type=article&id=6439661907059168219&articleType=0
11. [新闻轮播] 2026年04月10日 17时09分 - 人民日报：推进中华民族共同体建设，实现中华民族伟大复兴 - https://hkbtv.cn/#/article?type=article&id=6439661907059168218&articleType=0
12. [新闻轮播] 2026年04月03日 13时24分 - 各地扎实开展树立和践行正确政绩观学习教育 - https://hkbtv.cn/#/article?type=article&id=6439661907059167857&articleType=0
13. [热点要闻] 2026年04月13日 12时22分 - 两岸专家：十项涉台新政充满诚意善意，为两岸关系和平发展注入强劲动能 - https://hkbtv.cn/#/article?type=article&id=6439661907059168433&articleType=0
14. [热点要闻] 2026年04月13日 12时20分 - 写在第六届中国国际消费品博览会举办之际 - https://hkbtv.cn/#/article?type=article&id=6439661907059168426&articleType=0
15. [热点要闻] 2026年03月28日 16时47分 - 权威数读｜一周“靓”数 - https://hkbtv.cn/#/article?type=article&id=6439661907059167552&articleType=0
16. [热点要闻] 2026年03月21日 21时55分 - 沃野染新绿 春耕绘丰景——从春耕一线看“十五五”开局农业生产新气象 - https://hkbtv.cn/#/article?type=article&id=6439661907059167099&articleType=0
17. [热点要闻] 2026年03月10日 15时52分 - 我在两会听信心｜沉甸甸的法典草案，写满守护绿水青山的“硬杠杠” - https://hkbtv.cn/#/article?type=article&id=6439661907059166345&articleType=0
18. [热点要闻] 2026年02月11日 14时29分 - 新华时评｜安全生产检查要“除患”，坚决杜绝“走过场” - https://hkbtv.cn/#/article?type=article&id=6439661907059164642&articleType=0
19. [热点要闻] 2025年12月22日 18时06分 - 中央经济工作会议中的“十五五”名词：“好房子” - https://hkbtv.cn/#/article?type=article&id=6439661907059160979&articleType=0
20. [热点要闻] 2025年12月07日 23时35分 - 中国队8-1战胜日本队！ - https://hkbtv.cn/#/article?type=article&id=6439661907059159796&articleType=0
21. [文章] 2026年04月14日 14时09分 - 我国加快制造强国建设夯实高质量发展根基 - https://hkbtv.cn/#/article?type=article&id=6439661907059168531&articleType=0
22. [文章] 2026年04月13日 20时34分 - 公安部组织开展“强治理、护民安、促发展”主题宣传活动 - https://hkbtv.cn/#/article?type=article&id=6439661907059168473&articleType=0
23. [文章] 2026年04月10日 11时38分 - 写在中国（内蒙古）自由贸易试验区获批之际 - https://hkbtv.cn/#/article?type=article&id=6439661907059168202&articleType=0
24. [文章] 2026年04月10日 11时38分 - 新华社权威快报｜加大对新型隐性腐败惩治力度 两高发布最新司法解释 - https://hkbtv.cn/#/article?type=article&id=6439661907059168200&articleType=0
25. [文章] 2026年04月03日 20时40分 - 公安部等两部门部署金融领域“黑灰产”违法犯罪集群打击 - https://hkbtv.cn/#/article?type=article&id=6439661907059167892&articleType=0
26. [文章] 2026年04月01日 17时22分 - 为欺诈骗保“划红线”——国家医保局解读医保基金监管新规 - https://hkbtv.cn/#/article?type=article&id=6439661907059167741&articleType=0
27. [文章] 2026年03月26日 13时28分 - 博鳌亚洲论坛｜从全球经济治理的“旁观者”到“塑造者”：博鳌亚洲论坛嘉宾热议全球南方角色与作用 - https://hkbtv.cn/#/article?type=article&id=6439661907059167397&articleType=0
28. [文章] 2026年03月25日 18时56分 - 2025年度“中国科学十大进展”发布 - https://hkbtv.cn/#/article?type=article&id=6439661907059167332&articleType=0
29. [文章] 2026年03月25日 18时55分 - 首次写入国家五年规划，旅游强国怎么建、建什么？ - https://hkbtv.cn/#/article?type=article&id=6439661907059167329&articleType=0
30. [文章] 2026年03月25日 18时54分 - 博鳌亚洲论坛旗舰报告发布 亚洲仍是世界经济主要增长引擎 - https://hkbtv.cn/#/article?type=article&id=6439661907059167326&articleType=0
31. [文章] 2026年03月25日 18时51分 - 维护市场价格竞争环境 2026年市场监管部门将持续发力 - https://hkbtv.cn/#/article?type=article&id=6439661907059167311&articleType=0
32. [文章] 2026年03月18日 20时31分 - 国家发展改革委推出新一批重大外资项目 - https://hkbtv.cn/#/article?type=article&id=6439661907059166932&articleType=0
33. [文章] 2026年03月17日 13时57分 - 起步有力 开局良好——透视2026年中国经济开年表现 - https://hkbtv.cn/#/article?type=article&id=6439661907059166853&articleType=0
34. [文章] 2026年03月16日 23时33分 - 权威数读｜前2个月经济起步有力、开局良好 - https://hkbtv.cn/#/article?type=article&id=6439661907059166830&articleType=0
35. [文章] 2026年03月16日 23时33分 - 树立和践行正确政绩观｜深学细悟强党性 知行合一建新功——中央和国家机关扎实开展树立和践行正确政绩观学习教育 - https://hkbtv.cn/#/article?type=article&id=6439661907059166829&articleType=0
36. [文章] 2026年03月15日 21时10分 - 两会热词在基层｜韧性中国：练好内功 做强自身 - https://hkbtv.cn/#/article?type=article&id=6439661907059166695&articleType=0
37. [文章] 2026年03月14日 14时49分 - 两会热词在基层｜活力中国：向“新”而行 以“质”致远 - https://hkbtv.cn/#/article?type=article&id=6439661907059166626&articleType=0

## Detail API

- Observed URL: `https://hkbtv.cn/tv-station/api/details/article`
- Sample body: `{"articleId":"6439661907059168433","articleType":"0"}`
- Response fields:
  - title: `data.title`
  - source: `data.sourceArticle`
  - publish time: `data.releaseTime`
  - summary: `data.summary`
  - content HTML escaped: `data.content`
  - cover: `data.coverMapAddress`
  - access URL: `data.accessUrl`
  - comments: `data.commentList`
- Important note: `data.content` is HTML-escaped, so a generated spider should `html.unescape(...)` before parsing text/html.

## Detail Page Template

- Sample route: `https://hkbtv.cn/#/article?type=article&id=6439661907059168433&articleType=0`
- Page title: `详情 - 海广网`
- Title selector: `.article_title`
- Container selector: `main.el-main.nav_content`
- Content selector: `.page_content .article_content p`
- Publish time regex: `(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})`
- Source regex: `([^\d\s]{2,})(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})`
- Views/share regex: `分享\s*(\d+)`
- Wait selector: `.article_title`
- Content duplicated: `true`
- Observed content length from detail API HTML: `2449`

## Spider Strategy

- Recommended runtime: `FetcherSession` for both list and detail APIs.
- Browser rendering is optional and mainly useful for DOM validation; it is not required for production scraping of this route.
- List pagination: increment POST body `page` from `2` to `23` if full-history crawling is needed.
- Flatten `data.records[].articles[]` into article items; do not assume one API row equals one article.
- Build public article route from API ids when needed: `/#/article?type=article&id={articleId}&articleType={articleType}`.
- Prefer detail API over clicking DOM cards because metadata and escaped HTML content arrive in one response.
- Comment API is also available: `POST /tv-station/api/details/comment`.

## Evidence

- Raw browser probe: `analysis_outputs/_hkbtv_probe.json`
- Browser-captured classify API: `POST /tv-station/api/details/classify` with route options including `要闻` / `1858408493966991361`.
