# gdj-gansu-gov-cn-gdj-c109217-video-item-shtml analysis

- Source URL: `https://gdj.gansu.gov.cn/gdj/c109217/video_item.shtml`
- Analysis method: browser-rendered probe with `.venv/bin/python` and `patchright/playwright`
- CDP result: direct fresh-page CDP probe returned empty DOM with HTTP `400`; usable evidence came from rendered browser automation instead
- Anti-bot behavior: both list and detail first returned HTTP `412`, then the browser loaded challenge JS and re-requested the same page successfully

## Site / column

- Domain: `gdj.gansu.gov.cn`
- Base URL: `https://gdj.gansu.gov.cn`
- Page title: `本土纪录片`
- Column name: `本土纪录片`
- Channel meta on list page:
  - `<meta name="channelId" content="c0c8c340c68d4381998c567d89c3e38e">`
  - `<meta name="code" content="c109217">`

## List page DOM

- Item selector: `.news_list-item ul.pagelist > li`
- Link selector: `.news_list-item ul.pagelist > li > a[href*="/gdj/c109217/"][href$=".shtml"]`
- Title selector: `.news_list-item ul.pagelist > li > a > p`
- Publish time selector: `.news_list-item ul.pagelist > li > a > p > span`
- Wait selector: `.news_list-item ul.pagelist > li > a[href*="/gdj/c109217/"][href$=".shtml"]`
- Pagination container: `#page_div`
- First-page item count: `20`
- Pagination evidence: page bar shows `共8页`

## First-page titles

1. 石窟中国 第一集
2. 石窟中国 第二集
3. 石窟中国 第三集
4. 望首曲
5. 马家窑•彩陶上的中国 第一集《发现》
6. 马家窑•彩陶上的中国 第二集《密码》
7. 马家窑•彩陶上的中国 第三集《流变》
8. 戈壁是一片海——我在高原种夏菜
9. 戈壁是一片海——香菇夫妻致富路
10. 戈壁是一片海——沙海养虾人
11. 戈壁是一片海——戈壁滩上致富果
12. 戈壁是一片海——戈壁热带梦
13. 探秘神鹰谷（上）
14. 探秘神鹰谷（下）
15. 南梁纪事 第一集《太白起义枪声响》
16. 南梁纪事 第二集《黄土塬上举红旗》
17. 南梁纪事 第三集《南梁川里建政权》
18. 南梁纪事 第四集《边区引领新风尚》
19. 南梁纪事 第五集《列宁小学播火种》
20. 南梁纪事 第六集《红军长征过甘肃》

## Browser-observed list API

- Exists: yes
- Method: `GET`
- Capture pattern: `/common/search/`
- Observed path: `/common/search/c0c8c340c68d4381998c567d89c3e38e`
- Observed request shape:
  - `UAta9QfS=<dynamic token>`
  - `_isAgg=true`
  - `_isJson=true`
  - `_pageSize=20`
  - `_template=index`
  - `_rangeTimeGte=`
  - `_rangeTimeLt=`
  - `_channelName=`
  - `page=`
- Dynamic token: yes, browser-generated
- Response shape:
  - rows: `data.results`
  - page: `data.page`
  - total: `data.total`
  - detail URL: `data.results[].url`
  - title: `data.results[].title`
  - publish time: `data.results[].publishedTimeStr`
  - column name: `data.results[].channelName`
- Response summary:
  - `data.page = 1`
  - `data.rows = 20`
  - `data.total = 146`
  - `channelName = 本土纪录片`

## Detail page sample

- Sample URL: `https://gdj.gansu.gov.cn/gdj/c109217/202604/174316729.shtml`
- Title selector: `.newsDetails h6#title_f, .newsDetails h6#title_mm`
- Meta selector: `.newsDetails .notice.clearfix, .newsDetails .notice`
- Content selector: `.newsDetails #content`
- Video selector: `.newsDetails #content video[src], .newsDetails #content source[src$=".mp4"]`
- Wait selector: `.newsDetails #content video[src], .newsDetails #content`
- Sample video URL: `https://gdj.gansu.gov.cn/gdj/c109217/202604/174316729/files/bfea8e05eab240d9bc977a3a02121a27.mp4`
- Publish time regex: `发布时间[:：]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)`
- Source regex: `来源[:：]\s*([^\s【]*)`
- Views regex: `浏览次数[:：]\s*(\d+)`
- Content duplication: yes, desktop/mobile blocks are both present

## Spider notes

- Prefer `AsyncStealthySession`.
- Set `network_idle = false`.
- Prefer `capture_xhr="/common/search/"` instead of reconstructing the dynamic token manually.
- DOM fallback is reliable for page 1 because the first-page list is present in rendered HTML.
- Detail extraction should treat this section as video-oriented and read mp4 from the inline `<video>` element.
