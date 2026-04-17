# NXNews 警界传真列表页分析

- Source URL: `https://www.nxnews.net/sh/jjcz/`
- Slug: `www-nxnews-net-sh-jjcz`
- Analysis method: Chrome CDP via `.venv/bin/python tools/cdp_probe.py`
- Site domain: `www.nxnews.net`
- Column name: `警界传真`
- Page title: `宁夏新闻网`

## 列表页

- 列表容器：`#list`
- 列表项选择器：`#list li`
- 链接选择器：`#list a[href]`
- 标题选择器：`#list li p`
- 日期选择器：`#list li span#time`
- 当前页条数：`20`
- 分页存在：是
- 分页示例：
  - `https://www.nxnews.net/sh/jjcz/index_1.html`
  - `https://www.nxnews.net/sh/jjcz/index_19.html`
- 分页规律：`index_{n}.html`

注意：

- 列表 HTML 结构不规范，实际是 `a` 包裹 `li`。
- 页面重复使用 `id="time"` 作为每条新闻日期节点，不适合依赖唯一 ID 语义，但浏览器中 `#list li span#time` 实测可稳定命中 20 条。
- 列表中混有站外链接，首条详情指向 `news.cnr.cn`，如果 spider 仅抓本站，需要在提取后按 host 过滤。

## 首屏标题

1. 基层警事：胡杨不语，守护无声
2. 宁夏用好3037个治保委护航平安
3. 西吉公安破获一起“请托转学”诈骗案
4. 紧盯重点 全域覆盖 宁夏公安厅抓实廉政警示教育
5. 西夏公安拦截2起电诈挽损300余万元
6. 胜利街派出所：组建摩托车巡逻车队 让平安触手可及
7. 宁夏公安多元共治化解矛盾风险
8. 石嘴山交警试点电摩专用道
9. 银川市公安局特警支队党委荣膺“五星级基层党组织”称号
10. 盗采砂石暴力抗法3人被刑拘！宁夏公安破获一起妨害公务案
11. 一枚取卡针守住群众3万余元
12. 民警徒手刨沙救出被困车辆
13. 车主变造号牌受严惩
14. 银川车管所“内外兼修”为业务办理提速
15. 无视禁飞规定，宁夏又一人违规操作无人机被依法处罚
16. 跟着森林警察巡山
17. 一学生为泄愤网购牛粪寄给舍友
18. 【网络中国节·清明】H5｜清明时节缅怀银川公安英烈
19. 宁夏公安节目《星辰如你 誓言无声》亮相清明全国公安系统音乐朗诵会
20. 幼童走失，民警暖心守护

## 网络观察

- 未观察到承载列表数据的 JSON/XHR 接口。
- 观察到一个 `POST https://www.nxnews.net/Ahxwd_botd98165315` 请求，但返回 `application/octet-stream`，且未见列表数据结构，不适合作为列表抓取入口。
- 因此应采用 DOM 列表抓取策略，而不是 `capture_xhr`。

## 详情页

- 样本 URL: `https://www.nxnews.net/sh/jjcz/202604/t20260415_1472486.html`
- 主标题选择器：`.zwbt`
- 副标题选择器：`.zwfbt`
- 元信息选择器：`.zmm6`
- 正文选择器：`.article`
- 发布时间正则：`\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2}`
- 来源正则：`来源[:：]\\s*([^\\s]+)`
- 编辑/责任编辑：`.editor`

样本页观察：

- 主标题：`宁夏用好3037个治保委护航平安`
- 副标题：`3.2万余名治保员遍布城乡`
- 时间与来源：`2026-04-15 18:38:44 来源:宁夏法治报`
- 正文位于 `.article` 内，未见多份重复正文容器。

## Spider 生成建议

- 推荐 session：`AsyncStealthySession`
- 列表等待选择器：`#list`
- 详情等待选择器：`.zwbt, .article`
- 列表抓取应从 `#list a[href]` 读取 href，并结合 `#list li p`、`#list li span#time` 解析标题和日期。
- 如果只保留本站详情，应过滤 `urlparse(url).netloc == "www.nxnews.net"`。
- 分页可按 `index_{n}.html` 递进，直到下一页不存在或页面重复。
