# Scrapling Spider Analysis: v-hinews-cn-xinwen-list-4

## Summary

- Source URL: `https://v.hinews.cn/xinwen/list-4.html`
- Method: reusable local CDP probe `tools/cdp_probe.py` plus browser-observed DOM/detail capture.
- Search engines: not used.
- Non-browser target fetching: not used as primary evidence.
- Page title / column: `椰现场——椰视频` / `椰现场`
- First page count: `18` items
- List API found: none
- Pagination: normal SSR pagination links such as `?page=2`
- Detail pages are server-rendered HTML under `/xinwen/show-*.html`

## Rendered List DOM

- Item selector: `.ysp06 > ul > li`
- Link selector: `.ysp06 a[href*="/xinwen/show-"]`
- Title selector: `.ysp06 .shipinTxtBg a, .ysp06 .bor1 p`
- Publish time selector: not visible on the list page
- Source selector: not visible on the list page
- Image selector: `.ysp06 img`
- Wait selector: `.ysp06 a[href*="/xinwen/show-"]`
- Pagination selector: `a[href*="/xinwen/list-4.html?page="]`
- Note: the list page is plain SSR HTML with direct `show-*.html` links. No browser-observed XHR/fetch request returned content rows.

## First Page Titles

1. [video] 天海防务智船制造与研发项目落户三亚崖州湾 赋能自贸港海洋经济新发展丨消博聊“企”来 - `/xinwen/show-1530195.html`
2. [video] 聚焦深海产业 辰海智造基金落地三亚崖州湾科技城丨消博聊“企”来 - `/xinwen/show-1530194.html`
3. [video] 29个生物医学新技术项目集中亮相！乐城这场医疗健康专场活动释放健康消费强引力 - `/xinwen/show-1530193.html`
4. [video] 海南自贸港全球产业招商大会数字经济专场高光回顾丨自贸潮涌 向数图强 - `/xinwen/show-1530192.html`
5. [video] 研学热潮涌动！多校学子走进儋州市科技馆，共探科学奥秘 - `/xinwen/show-1530189.html`
6. [video] 自贸财新鲜：一场大会看海南招商热何以从“流量”变“留量”？ - `/xinwen/show-1530186.html`
7. [video] 中国银行举办“百万同行 悦享中国”GBIC大会 暨“来华通”APP全球推介会 - `/xinwen/show-1530185.html`
8. [video] Ta来消博了 | 老盐季亮相消博会 海南味道走向世界 - `/xinwen/show-1530183.html`
9. [video] 校长在线｜全球通申六七个Offer，哈罗海口学子甜蜜的烦恼 - `/xinwen/show-1530179.html`
10. [video] 校长在线｜哈罗学生申请英美院校，在海南上学凭啥更有竞争力 - `/xinwen/show-1530178.html`
11. [video] 车型首展！华为携“五界”车型与首款鸿蒙AI眼镜亮相第六届消博会 | ta来消博了 - `/xinwen/show-1530177.html`
12. [video] 山海同心庆“三月三” 三亚大东海广场变身民族体育狂欢大舞台 - `/xinwen/show-1530176.html`
13. [video] 科大讯飞副总裁战文宇：全方位深耕海南市场，以AI技术助力自贸港建设 | 消博聊“企”来 - `/xinwen/show-1530174.html`
14. [video] 旅游零售巨头奥纬达Avolta：期待参与海南离岛免税业务 | 消博聊“企”来 - `/xinwen/show-1530173.html`
15. [video] 开联低空亮相海南低空经济招商专场 将参建垂直起降基地、深耕全链路低空服务 | 消博聊“企”来 - `/xinwen/show-1530171.html`
16. [video] 数智AI+体验馆：中国移动把“未来生活”带上消博 - `/xinwen/show-1530170.html`
17. [video] 九款风味美食飘香！万宁“三月三”太好吃了｜走进长丰·记者Vlog - `/xinwen/show-1530169.html`
18. [video] 含“金”量十足！18家银行集体“牵手”新海航 | 自贸财新鲜 - `/xinwen/show-1530166.html`

## Browser-Observed Network

- Browser-observed network for the list page contained only the main `document` response.
- No XHR/fetch request returned list rows.
- Content rows came from SSR HTML, not a captured list API.

## Detail Page Template

- Sample URL: `https://v.hinews.cn/xinwen/show-1530195.html`
- Title selector: `.v_brief a`
- Meta selector: `.v_word`
- Video selector: `.videobox video`
- Video URL attribute: `.videobox video::attr(src)`
- Poster selector: `.videobox video::attr(poster)`
- Content selector: `p.formatted`
- Publish time regex: `(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})`
- Source regex: `来源：\s*(.+?)\s*编辑：`
- Editor regex: `编辑：\s*(.+)$`
- Wait selector: `.videobox video`
- Content duplicated: `false`
- Detail note: the page contains a direct MP4 URL in `<video src="...mp4">` and the article text is rendered below the player as `p.formatted`.

## Spider Strategy

- Recommended runtime: `FetcherSession` only.
- Crawl the list HTML directly and follow `show-*.html` links.
- Pagination can be handled by following `?page=N` links; no browser-only interaction was observed.
- Detail parsing should extract title from `.v_brief a`, metadata from `.v_word`, video URL/poster from `.videobox video`, and正文段落 from `p.formatted`.
- This section appears to be video-only on the sampled first page, so a video-program schema is a better fit than a text-news schema.

## Evidence

- Raw browser probe: `analysis_outputs/_v_hinews_cn_xinwen_list_4_probe.json`
