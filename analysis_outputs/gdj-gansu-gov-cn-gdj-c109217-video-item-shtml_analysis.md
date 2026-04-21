# gdj.gansu.gov.cn 本土纪录片分析

- Source URL: `https://gdj.gansu.gov.cn/gdj/c109217/video_item.shtml`
- Slug: `gdj-gansu-gov-cn-gdj-c109217-video-item-shtml`
- Primary evidence method: local visible Chrome CDP
- Column name: `本土纪录片`
- Analysis status: success

## List Page

The list page was successfully extracted from the visible Chrome session after the front-door challenge had already been cleared in that session.

Useful selectors:

- list container: `.news_list-item`
- item selector: `.news_list-item ul.pagelist > li`
- link selector: `.news_list-item ul.pagelist > li > a`
- title selector: `.news_list-item ul.pagelist > li > a > p`
- publish time selector: `.news_list-item ul.pagelist > li > a > p > span`

Observed first-page count: `20`

Observed first-page titles:

- 石窟中国 第一集
- 石窟中国 第二集
- 石窟中国 第三集
- 望首曲
- 马家窑•彩陶上的中国 第一集《发现》
- 马家窑•彩陶上的中国 第二集《密码》
- 马家窑•彩陶上的中国 第三集《流变》
- 戈壁是一片海——我在高原种夏菜
- 戈壁是一片海——香菇夫妻致富路
- 戈壁是一片海——沙海养虾人
- 戈壁是一片海——戈壁滩上致富果
- 戈壁是一片海——戈壁热带梦
- 探秘神鹰谷（上）
- 探秘神鹰谷（下）
- 南梁纪事 第一集《太白起义枪声响》
- 南梁纪事 第二集《黄土塬上举红旗》
- 南梁纪事 第三集《南梁川里建政权》
- 南梁纪事 第四集《边区引领新风尚》
- 南梁纪事 第五集《列宁小学播火种》
- 南梁纪事 第六集《红军长征过甘肃》

The page is server-rendered HTML. No useful list XHR/API schema was observed. The paginator shows `8` pages, but this run did not reverse-engineer the page-turning logic, so this analysis is suitable for a first-page spider.

## Detail Page

Sample detail URL:

- `https://gdj.gansu.gov.cn/gdj/c109217/202604/174316729.shtml`

Useful selectors:

- title: `.newsDetails #title_f, .newsDetails #title_mm`
- meta block: `.newsDetails .notice`
- content block: `.newsDetails #content`
- video selector: `.newsDetails #content video[src$='.mp4'], .newsDetails #content source[src$='.mp4']`

Observed metadata patterns:

- publish time regex: `发布时间：\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})`
- source regex: `来源：\s*([^\s【]+)?`
- views regex: `浏览次数[:：]\s*(\d+)`

Observed video URL pattern:

- `/gdj/c109217/<yyyymm>/<article_id>/files/<uuid>.mp4`

The detail HTML contains both desktop and mobile templates, each with a `#content` block. Prefer desktop `.newsDetails #content` first.

## Spider Notes

- Use browser-rendered requests only for analysis; production spider code should not depend on a local CDP endpoint.
- For this section, `AsyncStealthySession` is the safer default because the list page initially required a real visible Chrome session to become analyzable.
- The current analysis is reliable for first-page extraction and per-detail video capture.

Artifacts:

- `analysis_outputs/gdj-gansu-gov-cn-gdj-c109217-video-item-shtml_visible_tab.json`
- `analysis_outputs/gdj-gansu-gov-cn-gdj-c109217-detail_visible.json`
- `analysis_outputs/gdj-gansu-gov-cn-gdj-c109217-video-item-shtml_analysis.json`
