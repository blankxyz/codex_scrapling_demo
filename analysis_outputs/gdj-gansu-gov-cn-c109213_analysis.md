# gdj-gansu-gov-cn-c109213 爬虫分析报告

- 输入列表页: `https://gdj.gansu.gov.cn/gdj/c109213/xwzxcdh.shtml`
- site_slug: `gdj-gansu-gov-cn-c109213`
- 栏目: `新闻中心 > 行业动态`
- 分析时间: 2026-04-15
- 分析约束: 仅使用本地 Chrome/CDP 浏览器证据；未使用搜索引擎；未使用 curl/wget/requests 等非浏览器 HTTP 客户端抓目标站。

## 页面结论

该列表页是动态渲染列表页，推荐使用浏览器会话中的接口数据生成爬虫。

浏览器/CDP 已验证：

- 页面标题: `行业动态`
- 页面 URL: `https://gdj.gansu.gov.cn/gdj/c109213/xwzxcdh.shtml`
- 列表栏目 channelId: `72986a1db9604235af9171cb4a34c7ca`
- 首次 XHR: `/common/search/72986a1db9604235af9171cb4a34c7ca...`
- XHR 响应类型: `application/json`
- 首次响应: `data.page = 1`, `data.rows = 20`, `data.total = 5620`
- 点击分页 `2` 后，浏览器再次发起同类 XHR，响应 `data.page = 2`
- 第一页详情链接已渲染在 DOM 中，形态为 `/gdj/c109213/{yyyymm}/{id}.shtml`

`requires_dynamic = true`。

`api_first_recommended = true`，但建议通过浏览器会话或复用浏览器生成的动态 token 访问接口。页面 JS 中的稳定接口模板和浏览器实际发出的请求存在差异：源码中是普通查询参数，实际 Network URL 被站点防护层改写为 `UAta9QfS` 动态 token 形式。

## 列表 API

浏览器加载的同源脚本 `https://gdj.gansu.gov.cn/gdj/xhtml/js/listPage.js` 中的接口模板：

```javascript
$.ajax({
  url: '/common/search/' + this.channelId
    + '?_isAgg=true&_isJson=true&_pageSize=' + parseInt($("#pageSize").val())
    + '&_template=index&_rangeTimeGte=&_channelName=&page=' + parseInt($("#page").val()),
  type: 'get',
  success: function(data) {
    table_page(data.data.total);
    table_each("list", ajax_success(data));
  }
})
```

稳定逻辑接口：

```text
GET https://gdj.gansu.gov.cn/common/search/{channelId}
```

逻辑参数：

```json
{
  "_isAgg": "true",
  "_isJson": "true",
  "_pageSize": 20,
  "_template": "index",
  "_rangeTimeGte": "",
  "_channelName": "",
  "page": 1
}
```

当前栏目：

```json
{
  "channelId": "72986a1db9604235af9171cb4a34c7ca",
  "channelCodeName": "c109213",
  "channelName": "行业动态"
}
```

浏览器 Network 中实际观测到的请求形态：

```text
GET https://gdj.gansu.gov.cn/common/search/72986a1db9604235af9171cb4a34c7ca?UAta9QfS={dynamic_token}
```

请求头特征：

```http
Accept: */*
Referer: https://gdj.gansu.gov.cn/gdj/c109213/xwzxcdh.shtml
X-Requested-With: XMLHttpRequest
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
```

注意：`UAta9QfS` 是浏览器/防护层生成的动态 token，不应硬编码。爬虫实现应优先让浏览器加载页面并通过页面 JS 或浏览器上下文触发分页请求。

## 响应结构

第一页响应结构：

```json
{
  "data": {
    "page": 1,
    "rows": 20,
    "channelId": "72986a1db9604235af9171cb4a34c7ca",
    "total": 5620,
    "relateSubChannels": "true",
    "results": []
  },
  "locationUrl": "...",
  "channelName": "行业动态"
}
```

`data.results[]` 字段：

```json
{
  "title": "全国电视频道全面清除虚假宣传医药广告",
  "content": "正文摘要/正文片段",
  "url": "/gdj/c109213/202604/174315227.shtml",
  "subTitle": "全国电视频道全面清除虚假宣传医药广告",
  "manuscriptId": "174315227",
  "publishedTime": 1775755803000,
  "publishedTimeStr": "2026-04-10 09:30:03",
  "channelName": "行业动态",
  "channelCodeName": "c109213",
  "channelId": "72986a1db9604235af9171cb4a34c7ca",
  "domainMetaList": []
}
```

来源字段位于 `domainMetaList[].resultList[]`：

```json
{
  "key": "source",
  "name": "来源",
  "value": "国家广播电视总局"
}
```

## 分页规则

页面隐藏/状态字段：

- `#pageSize`: 每页数量，当前为 `20`
- `#page`: 当前页码

分页函数：

```javascript
function table_page(totalHits) {
  var pageSize = parseInt($("#pageSize").val());
  var page = parseInt($("#page").val());
  var pageNum = Math.floor((totalHits + pageSize - 1) / pageSize);
  ...
}
```

当前浏览器响应：

```json
{
  "page": 1,
  "rows": 20,
  "total": 5620,
  "pageNum": 281
}
```

停止条件：

```python
last_page = ceil(total / rows)  # 5620 / 20 = 281
stop when page > last_page
```

浏览器点击分页 `2` 后已验证：

```json
{
  "clicked": true,
  "response.data.page": 2,
  "response.data.rows": 20,
  "response.data.total": 5620
}
```

## 第一页标题

浏览器 DOM 和 XHR 响应验证的第一页 20 条：

1. 全国电视频道全面清除虚假宣传医药广告
2. 国家广播电视总局部署开展“AI魔改”视频治理工作取得实效
3. 3月《好好的时光》《冬去春来》收视火热，纪录片《吴越国》等关注度高，元宵晚会拉升电视大屏活跃率
4. 17部电视剧网络剧列入重点作品版权保护预警名单
5. 中国代表团圆满完成国际电信联盟无线电通信部门第六研究组会议参会任务
6. 纪录片《聆听中国动画之音》3月27日全网上线
7. 建军百年重点电视剧创作推进会在京举行
8. 国家广播电视总局与中国教科文卫体工会召开第二次联席会议
9. 光影潮涌，剧向蓝海——第十五届中国国际新媒体短片节在深圳开幕
10. 曹淑敏会见巴西国家传媒公司总裁巴斯鲍姆
11. “广电+”点亮2026北京夜空
12. 国家广播电视总局举办电视剧《生命树》创作座谈会
13. 第七届非遗相声大会在深圳举办
14. 广东超高清视频产业跻身万亿级集群国家广播电视总局全链条推进成效显著
15. 电视剧赋能经济社会发展 成为两会热议话题
16. 央视和省级卫视春晚创近年收视纪录，《好好的时光》《纯真年代的爱情》等收视高开高走，2月电视大屏火爆春节假期
17. 国家广播电视总局举办电视剧《太平年》创作座谈会
18. 喜报！全国广电视听行业14个集体、6名个人荣获全国妇联表彰
19. 第二届法治中国“三微”优秀作品展播开启
20. “中国联合展台”春节期间精彩亮相2026年伦敦电视节

## 列表字段映射

```json
{
  "detail_url": "urljoin('https://gdj.gansu.gov.cn', result.url)",
  "title": "result.title",
  "summary": "result.content",
  "publish_time": "result.publishedTimeStr",
  "publish_timestamp_ms": "result.publishedTime",
  "content_id": "result.manuscriptId",
  "channel_name": "result.channelName",
  "channel_code": "result.channelCodeName",
  "source": "domainMetaList[].resultList[] where key == 'source'"
}
```

## DOM 备用方案

渲染后列表链接选择器：

```css
.pagelist a[href*="/gdj/c109213/"][href$=".shtml"]
```

列表项文本结构：

```css
.pagelist a
.pagelist li.sp
.pagelist li.sp .left p
.pagelist li.sp em
```

分页链接：

```css
#page_div a.zxfPagenum
#page_div a.nextpage
```

注意：DOM 由 XHR 响应生成，接口数据比 DOM 更稳定。

## 详情页解析

浏览器打开的详情页样本：

```text
https://gdj.gansu.gov.cn/gdj/c109213/202604/174315227.shtml
```

浏览器验证字段：

- 页面标题: `全国电视频道全面清除虚假宣传医药广告 - 行业动态`
- 正文标题: `全国电视频道全面清除虚假宣传医药广告`
- 发布时间: `2026-04-10 09:30:03`
- 来源: `国家广播电视总局`
- 浏览次数: `90`
- 正文容器: `.notice_content`

详情页选择器：

```json
{
  "title": "h6.text_title_f",
  "content": ".notice_content",
  "meta_container": ".titles",
  "fallback_main": ".content.w1200"
}
```

发布时间/来源可从 `.titles` 或 body 文本提取：

```python
publish_time = re.search(r"发布时间[:：]\\s*(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2})", text)
source = re.search(r"来源[:：]\\s*([^\\s]+)", text)
views = re.search(r"浏览次数[:：]\\s*(\\d+)", text)
```

正文边界：

- 起点: `.notice_content`
- 终点: `.notice_content` 自身结束
- 备用文本清洗时，在 `分享：`、`【关闭窗口】`、`友情链接` 前截断

## 爬虫生成建议

推荐实现：

1. 使用浏览器/动态抓取打开列表页，等待 `/common/search/{channelId}` XHR 完成。
2. 从 XHR JSON 读取 `data.results`，不要优先从 DOM 文本反推。
3. 翻页时在浏览器上下文中设置 `#page` 并调用页面函数 `table_ajax()`，或点击 `#page_div` 分页链接，让站点 JS 生成动态 token。
4. 对每条结果使用 `urljoin("https://gdj.gansu.gov.cn", result.url)` 得到详情页。
5. 详情页可直接由浏览器打开解析，标题用 `h6.text_title_f`，正文用 `.notice_content`。

浏览器上下文分页示例：

```javascript
$("#page").val(2);
table_ajax();
```

如果爬虫运行环境能稳定复现站点防护 token，也可以尝试直接请求源码中的逻辑接口；但本次浏览器 Network 证明实际请求会被改写为 `UAta9QfS` 动态 token，因此不要把某一次 token 或 Cookie 写死。

## 风险与注意点

- 原始 headless Chrome 直接打开曾出现空 DOM；通过用户启动的 Chrome CDP 会话可以成功取得真实页面和 XHR。说明会话状态/防护通过情况会影响结果。
- `UAta9QfS` 是动态 token，Cookie 也是会话相关，不能硬编码。
- 建议爬虫使用 DynamicFetcher/浏览器会话，并在页面上下文中执行分页。
- 本分析没有使用搜索引擎，也没有用非浏览器 HTTP 客户端抓目标站。
