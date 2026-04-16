# Scrapling Spider Analysis: www-hinews-cn-column-97894cbd59064f64b938c7a3e6dade8a

## 概览

- 源列表页：`https://www.hinews.cn/column/97894cbd59064f64b938c7a3e6dade8a?city=1`
- 分析方式：Chrome CDP 直连目标页，成功抓到首屏渲染 DOM、一个详情页 DOM，以及点击 `查看更多` 后的分页接口请求与响应。
- 搜索引擎：未使用。
- 非浏览器直连目标站点抓取：未作为分析证据使用。
- 站点类型：Nuxt 渲染的栏目页，第一页为 SSR/首屏已出列表，后续分页通过前端 `POST` 接口追加。

## 站点与栏目

- 域名：`www.hinews.cn`
- 页面标题：`海口新闻网_南海网`
- 可见栏目名：`海口频道`
- 栏目 UUID：`97894cbd59064f64b938c7a3e6dade8a`
- 详情页域名：`https://www.hinews.cn`

## 列表页 DOM 结论

- 列表容器：`ul.l_list`
- 列表项：`ul.l_list > li`
- 详情链接：`ul.l_list > li h3 > a`
- 标题字段：`ul.l_list > li h3 > a`
- 发布时间：`ul.l_list > li ul.brief_box > li:first-child`
- 来源：`ul.l_list > li ul.brief_box > li:last-child`
- 图片：`ul.l_list > li img.row_two_img`
- 分页按钮：`button.more_list`
- 列表等待选择器：`ul.l_list > li h3 > a`
- 详情 URL 规范化基址：`https://www.hinews.cn`
- 首屏条数：`20`

## 分页与接口

- 已直接观察到的列表接口：`POST https://rm-comapi-pc.hinews.cn/open-service/content/getNewsIndexManyLevelByUuidSplit`
- 固定参数：`uuid=97894cbd59064f64b938c7a3e6dade8a`、`siteId=12`
- 分页参数：`pageNo`
- 页大小字段：`pageSize`
- 响应列表路径：`data.list[]`
- 详情 URL 模板：`https://www.hinews.cn/page?n={id}&m=1&s={siteLayoutModuleArticleStyleId}`

## 详情页 DOM 结论

- 样例详情页：`https://www.hinews.cn/page?n=2816953&m=1&s=1044`
- 标题选择器：`h2.page_h2`
- 元信息容器：`ul.page_brief`
- 来源选择器：`ul.page_brief li:first-child a`
- 发布时间选择器：`ul.page_brief li:last-child`
- 正文容器：`#bs_content > div:first-child`
- 媒体资源：`#bs_content img, #bs_content video[src]`

## 证据文件

- `analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_probe_20260416.json`
- `analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_loadmore_probe_20260416.json`
- `analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_api_body_20260416.json`
