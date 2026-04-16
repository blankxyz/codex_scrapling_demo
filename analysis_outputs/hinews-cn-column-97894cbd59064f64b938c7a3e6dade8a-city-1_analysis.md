# Scrapling Spider Analysis: hinews-cn-column-97894cbd59064f64b938c7a3e6dade8a-city-1

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

页面 DOM 片段显示的列表结构为：

- `ul.l_list > li > a[target="_blank"] > img.row_two_img`
- `ul.l_list > li > h3.f20.p15 > a[target="_blank"]`
- `ul.l_list > li > h3 > ul.list-inline.brief_box`

注意：

- 少量列表项没有首图，`li` 下可能没有前置图片链接，但 `h3 > a` 仍然存在。
- 首屏文章链接为相对路径，如 `/page?n=2816953&m=1&s=1044`，应拼成绝对 URL。

## 首屏标题

1. 2026环岛赛海口开赛 杜尚・拉约维奇力压群雄赢得揭幕战
2. 海口以“加减法”优化城市更新营商环境
3. 全球服务中心“海南站”揭牌落地海口秀英 琼粤协同赋能自贸港开放发展
4. 第六届消博会出行攻略：打车、公交全指南
5. 海口龙华区与济源市万洋集团签订战略合作协议 万洋集团贸易总部将落户龙华
6. 海口秀英区多方合力爱心助农 销售冬瓜5万余斤
7. 第六届消博会绿色消费主题活动在海口举行 发布绿色消费倡议
8. 2026年海南招商大会人工智能专场在海口成功举办
9. 一站“逛”全省百余精品楼盘 2026第二届海南自贸港房展会在海口开幕
10. 国际艺术IP落地自贸港！第八届“钢琴岛”音乐节7月在海口启幕
11. 香港澳至尊集团主席蔡志辉：今年计划在海口开设品牌旗舰专卖店
12. 消博会最靓的 “仔”！排爆犬戴上智能眼镜硬核巡逻
13. 侨商聚椰城 寻机消博会——“2026世界侨商海南行”活动启幕
14. 80余家品牌齐聚，“老字号 新主场”主题活动在海口骑楼老街启动
15. 2026年海南自贸港全球产业招商大会低空经济专场在海口举办 | 消博进行时
16. 从枝头到全国 海口三门坡2000亩桂早荔抢“鲜”上市
17. 封关机遇叠加消博会 海口综保区直播解锁进口消费品投资新路径
18. 海南自贸港AI数智生态共创研讨会举办 秀英区首个科技企业孵化器正式启动
19. 水木年华海口站演唱会18日唱响！凭消博会证件购票享专属折扣
20. 2026中国品牌出海博览会将于10月在海口举办

## 分页与接口

点击 `button.more_list` 后：

- 点击前条数：`20`
- 点击后条数：`40`
- 说明：第一页来自首屏渲染；点击后通过接口拉取第 2 页并追加到同一 `ul.l_list`

已直接观察到的列表接口：

- 方法：`POST`
- 接口：`https://rm-comapi-pc.hinews.cn/open-service/content/getNewsIndexManyLevelByUuidSplit`
- 表单参数：
  - `uuid=97894cbd59064f64b938c7a3e6dade8a`
  - `pageNo=2`（点击一次 `查看更多` 时）
  - `siteId=12`
- 响应状态：`200`
- 响应结构：
  - 顶层：`code`, `msg`, `data`
  - 分页字段：`data.pageNo`, `data.pageSize`, `data.count`
  - 列表字段：`data.list[]`
  - 行包装：`data.list[].moduleNewsDataBO`
  - 正文数据：`data.list[].moduleNewsDataBO.contentNewsBO`

在已捕获的第 2 页响应中：

- `data.pageNo = 2`
- `data.pageSize = 20`
- `data.count = null`
- `data.list.length = 20`

字段映射：

- 文章 ID：`data.list[].moduleNewsDataBO.contentNewsBO.id`
- 标题：`data.list[].moduleNewsDataBO.contentNewsBO.title`
- 发布时间：`data.list[].moduleNewsDataBO.contentNewsBO.publishTime`
- 时间戳：`data.list[].moduleNewsDataBO.contentNewsBO.timeStamp`
- 来源：`data.list[].moduleNewsDataBO.contentNewsBO.source.name`
- 缩略图：`data.list[].moduleNewsDataBO.contentNewsBO.thumbnail`
- 样式/详情模板参数：`data.list[].moduleNewsDataBO.contentNewsBO.siteLayoutModuleArticleStyleId`

接口响应里未直接给出可用的完整详情 URL，但第一页 DOM 已证明详情页模板为：

- `/page?n=<id>&m=1&s=<siteLayoutModuleArticleStyleId>`

因此该栏目详情 URL 可按下面模板构造：

- `https://www.hinews.cn/page?n={id}&m=1&s={siteLayoutModuleArticleStyleId}`

本页已验证的首条详情样例：

- `https://www.hinews.cn/page?n=2816953&m=1&s=1044`

## 详情页 DOM 结论

- 样例详情页：`https://www.hinews.cn/page?n=2816953&m=1&s=1044`
- 页面标题：`2026环岛赛海口开赛 杜尚・拉约维奇力压群雄赢得揭幕战-南海网`
- 标题选择器：`h2.page_h2`
- 元信息容器：`ul.page_brief`
- 来源选择器：`ul.page_brief li:first-child a`
- 发布时间选择器：`ul.page_brief li:last-child`
- 正文容器：`#bs_content > div:first-child`
- 详情页等待选择器：`h2.page_h2`
- 图片/视频资源：`#bs_content img, #bs_content video[src]`

可用正则：

- 发布时间：`(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})`
- 来源：`来源：\\s*(.+?)(?=时间：|$)`

补充判断：

- `#bs_content` 内第一层 `div` 为主体正文。
- `#bs_content` 后半部分还包含作者、责任编辑等辅助信息。
- 当前样例未发现正文重复容器，`content_duplicated = false`。

## 推荐爬取策略

- 推荐会话：`AsyncStealthySession`
- 首屏：直接从 DOM 抓取，避免把第一页也强依赖到接口回放
- 翻页：优先复用已观察到的 `POST /open-service/content/getNewsIndexManyLevelByUuidSplit`
- 分页参数：递增 `pageNo`
- 固定参数：
  - `uuid=97894cbd59064f64b938c7a3e6dade8a`
  - `siteId=12`
- DOM 回退：
  - 列表：`ul.l_list > li`
  - 链接：`ul.l_list > li h3 > a`
  - 时间：`ul.l_list > li ul.brief_box > li:first-child`
  - 来源：`ul.l_list > li ul.brief_box > li:last-child`
- 详情解析：
  - 标题：`h2.page_h2`
  - 元信息：`ul.page_brief`
  - 正文：`#bs_content > div:first-child`

## 风险与备注

- 第一页主要依赖 SSR DOM，分页才触发列表接口；因此如果后续 spider 只抓第一页，DOM 方案更直接。
- 分页接口响应中 `data.count` 当前为 `null`，不能依赖总数判断终止。
- 详情 URL 不是接口里的现成字段，而是需要根据 DOM 已验证模板和接口字段拼接。
- 列表页右侧还混有领导、问政、活动等侧栏内容，选择器必须限定在 `ul.l_list` 下。

## 证据文件

- 首屏与详情页 CDP 探针：`analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_probe_20260416.json`
- `查看更多` 点击探针：`analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_loadmore_probe_20260416.json`
- 分页接口完整响应：`analysis_outputs/_hinews_cn_column_97894cbd59064f64b938c7a3e6dade8a_api_body_20260416.json`
