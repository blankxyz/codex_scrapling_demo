# Scrapling Spider Analysis: mmr-yntv-cn-btlby-sectionid-87-88

## Summary

- Source URL: `https://mmr.yntv.cn/mmr/btlby.html?sectionid=87,88&page=1&title=%E1%80%A1%E1%80%9B%E1%80%B1%E1%80%B8%E1%80%80%E1%80%BC%E1%80%AE%E1%80%B8%E1%80%9E%E1%80%90%E1%80%84%E1%80%BA%E1%80%B8`
- Method: Chrome CDP browser rendering and browser-captured Network/XHR evidence.
- Search engines: not used.
- Non-browser target fetching: not used.
- Page title / column: `အရေးကြီးသတင်း`
- First page count: `30` items
- API found: `GET https://yntv-api.yntv.cn/api/cms/getsection`
- API last_page observed: `21`

## Browser-Observed List API

- Observed URL: `https://yntv-api.yntv.cn/api/cms/getsection?section_id=87,88&page=1&size=30&_=1776237570887`
- Query parameters:
  - `section_id=87,88`
  - `page=1`
  - `size=30`
  - `_=<timestamp cache buster>`
- JSON paths:
  - rows: `data`
  - last page: `msg.last_page`
  - title: `data[].title`
  - detail URL: `data[].url`
  - publish timestamp: `data[].createtime` (Unix seconds, display timezone UTC+8)
  - type: `data[].type` (`news` or `video`)
  - image: `data[].image`
  - description: `data[].description`

## Rendered List DOM Fallback

- Item selector: `li.sec2_right_item`
- Link selector: `li.sec2_right_item a[href^="https://www.yntv.cn/"]`
- Title selector: `li.sec2_right_item .sec2_right_item_title`
- Publish time selector: `li.sec2_right_item .sec2_right_time`
- Wait selector: `li.sec2_right_item a[href^="https://www.yntv.cn/"]`

## First Page Titles

1. [news] 2025-08-29 10:23:22 - ယူနန်ပြည်နယ် သဲဟုန်တွင် မမေ့နိုင်သော အရသာတစ်ခုရှိပြီး ၎င်းမှာ ခရမ်းချဉ်သီး ဆန်ခေါက်ဆွဲဖြစ် - https://www.yntv.cn/news/20250826/1756191955753431.html
2. [video] 2025-08-07 16:22:08 - ကူမင်းမှ မှိုမီးပန်းပွဲတော်သည် "မှိုပုံပြင်" ၏ စိတ်ကူးယဉ်ဆန်သော ခံစားချက်ကို အပြည့်အဝ ပေးစွမ်း - https://www.yntv.cn/video/20250807/1754549359749674.html
3. [video] 2025-08-07 16:21:58 - Aerial views of Mingguang Town, Tengchong, Yunnan - https://www.yntv.cn/video/20250807/1754549383749676.html
4. [news] 2025-07-15 16:52:25 - Is it difficult to receive packages in remote areas? Technology has a solution! - https://www.yntv.cn/news/20250715/1752568058745239.html
5. [news] 2025-05-27 15:59:32 - ဟဲခုန်နယ်ခြား စောင့်ဂိတ်မှ တရုတ်နိုင်ငံသို့ လတ်ဆတ်သော ဗီယက်နမ်ရွက်ခြောက် ၈ ဒသမ ၈ တန် ဝင်ရောက် - https://www.yntv.cn/news/20250527/1748314278735940.html
6. [news] 2025-05-27 15:59:32 - The 2,400 mu of wasabi in Zhenxiong County has entered the leaf and petiole harvesting period - https://www.yntv.cn/news/20250527/1748314470735941.html
7. [news] 2025-05-26 16:21:28 - The first "Seven Bridges Chasing the Wind" Dianchi Greenway Cycling Tour was launched in Kunming - https://www.yntv.cn/news/20250526/1748247210735784.html
8. [news] 2025-05-26 16:21:19 - Pet owners! The "Travel Yunnan by Train" circular tourist train now allows pets under 15kg to board (with quarantine certificates) - https://www.yntv.cn/news/20250526/1748247349735785.html
9. [news] 2025-05-19 15:59:07 - ယင်ကျန်းကောင်တီ၊ သဲဟုန်၊ ယူနန် တွင် ယခုအချိန်သည် စပါးပျိုးပင်များ စိုက်ပျိုးရန် အချိန်ကောင်းဖြစ်ပါသည်။ - https://www.yntv.cn/news/20250519/1747639413734383.html
10. [news] 2025-05-19 11:22:42 - The red spheniscus in Menglian County, Yunnan Province, has entered the breeding season. - https://www.yntv.cn/news/20250519/1747623252734358.html
11. [video] 2025-05-16 13:28:12 - စက္ကူမြင်းစီးကာ ကခုန်ပြီး ဝမ်ရှန်းရှိကျွမ်းလူမျိုးတို့၏  စက္ကူမြင်းအက ကျက်သရေကို ခံစားလိုက်ပါ။ - https://www.yntv.cn/video/20250516/1747359992733827.html
12. [news] 2025-04-27 11:40:42 - In the first quarter of 2025, the average proportion of days with good air quality in 339 cities in China was 84.8%, and two major pollutant indicators decreased - https://www.yntv.cn/news/20250425/1745552793729927.html
13. [news] 2025-04-27 11:40:36 - On April 23, 2025, China and Azerbaijan signed a visa exemption agreement - https://www.yntv.cn/news/20250425/1745552661729926.html
14. [news] 2025-04-27 11:40:25 - အဝါရောင်တို့ဟူးသည် ယူနန်ပြည်နယ်၊ ရွှမ်းဝိမ် ကောင်တီ တွင် အထူးအစားအစာဖြစ်ပါတယ်။ - https://www.yntv.cn/news/20250425/1745549971729918.html
15. [news] 2025-04-27 11:40:25 - Thanks to photovoltaic water pumping, the problem of inconvenient water supply has been solved for 100,000 mu of farmland in Xuanwei City, Yunnan Province - https://www.yntv.cn/news/20250425/1745552452729924.html
16. [news] 2025-04-27 11:40:25 - Let's take a look at the changes of the "two countries, two parks" from satellite images - https://www.yntv.cn/news/20250425/1745552546729925.html
17. [news] 2025-04-27 11:36:52 - ပင်းချွမ်း ကောင်တီ၊ သာ့လီ၊ ယူနန်ပြည်နယ်မှသစ်သီးများသည်အာဆီယံနိုင်ငံများတွင်အလွန်ရေပန်းစားပါတယ်။  - https://www.yntv.cn/news/20250425/1745546818729895.html
18. [news] 2025-04-27 11:36:45 - တူညီသောဘောင်ရှိ ဇီးသီးအပွင့် ပေါ်ရှိငှက်နှစ်ကောင်သည် အလွန်စိတ်ဝင်စားစရာကောင်းပါတယ်။ - https://www.yntv.cn/news/20250425/1745547521729904.html
19. [news] 2025-04-27 11:34:18 - ယူနန်ပြည်နယ်ရှိ မွန်ဂိုလီးယားအပင် သည် လေးပုံတစ်ပုံ ရေခဲခေတ် (လွန်ခဲ့သည့် နှစ်သန်းပေါင်း ၂ သန်းခန့်က စတင်ခဲ့သော) မှ လွတ်မြောက်ခဲ့သော ရှေးဟောင်းအပင်ဖြစ်ပြီး အပင်နိုင်ငံ၏ "သက်ရှိရုပ်ကြွင်း" များထဲမှ တစ်ခုအဖြစ် လူသိများပါတယ်။   - https://www.yntv.cn/news/20250423/1745375274729489.html
20. [news] 2025-04-27 11:34:18 - ​The dried mangoes produced by workers in Jianshan County, Kampong Speu Province, Cambodia, only take 10 days to appear on the shelves of Chinese supermarkets - https://www.yntv.cn/news/20250423/1745376803729507.html
21. [news] 2025-04-27 11:34:18 - In Kaiyuan City, Honghe Prefecture, Yunnan Province, humanoid robots covered in silver and white flexibly completed high-altitude power grid operations after receiving instructions - https://www.yntv.cn/news/20250423/1745376985729508.html
22. [news] 2025-04-10 10:33:47 - This is Dali, Yunnan, a place that will make you fall in love with life.  - https://www.yntv.cn/news/20250409/1744187683726660.html
23. [news] 2025-04-10 10:33:40 - In Honghe, Yunnan, which is known as the "Hometown of Rice Noodles", how can you not give the rice noodles a try?  - https://www.yntv.cn/news/20250409/1744187400726659.html
24. [news] 2025-03-17 15:11:15 - Technicians are artificially pollinating Gastrodia elata - https://www.yntv.cn/news/20250317/1742195268722607.html
25. [news] 2025-02-20 10:50:41 - Electric two-wheelers, affectionately called "small electric donkeys" by the Chinese, have begun to be loved by overseas consumers - https://www.yntv.cn/news/20250219/1739954940717924.html
26. [news] 2025-02-20 10:50:33 - Walking into Mangtuan Village, Mengding Town, Dai paper with a history of more than 600 years is drying in the new Dai buildings - https://www.yntv.cn/news/20250219/1739955095717925.html
27. [news] 2025-01-24 16:05:12 - စက္ကူဖြတ်ခြင်းအနုပညာသည် တရုတ်နိုင်ငံတွင် ရှည်လျားသောသမိုင်းကြောင်းရှိ - https://www.yntv.cn/news/20250124/1737700147713338.html
28. [news] 2025-01-24 16:05:12 - ဟွာ့ရှန်းပွဲတော်သည် မြှောင်လူမျိုးတို့၏ ကြီးကျယ်ခမ်းနားသော ရိုးရာပွဲတော်တစ်ခုဖြစ် - https://www.yntv.cn/news/20250124/1737701414713340.html
29. [news] 2025-01-17 15:24:16 - On January 15, Shangri-La Shika Snow Mountain Snow Park officially opened, injecting new vitality into Diqing's winter tourism - https://www.yntv.cn/news/20250117/1737083749711944.html
30. [news] 2025-01-17 15:11:55 - ပေါင်ရှန်း ဒေသခံ တိုင်ရွာသားများသည် ကော်ဖီပြုလုပ်ရာတွင် ရှေးကျသောနည်းလမ်းကို အသုံးပြုကြ - https://www.yntv.cn/news/20250117/1737079629711934.html

## News Detail Template

- Sample URL: `https://www.yntv.cn/news/20250826/1756191955753431.html`
- Title selector: `#page_details_text_wrap .content_left .text_title`
- Meta selector: `#page_details_text_wrap .content_left .text_info`
- Publish time selector: `#page_details_text_wrap .content_left .text_time`
- Content selector: `#page_details_text_wrap .content_left > p`
- Publish time regex: `发布日期:\s*(\d{4}年\d{2}月\d{2}日)`
- Source regex: `source：\s*(.+)$`
- Content duplicated: `false` in observed sample

## Video Detail Template

- Sample URL: `https://www.yntv.cn/video/20250807/1754549359749674.html`
- Title selector: `#page_details_text_wrap .content_left .text_title`
- Meta selector: `#page_details_text_wrap .content_left .text_info`
- Description selector: `#page_details_text_wrap .content_left > p`
- Media source: inline script containing `Aliplayer`
- Media source regex: `"source"\s*:\s*"([^"]+)"`
- Observed media source: `https://video.yntv.cn/vod/20250807/71d610d4-9de7-422d-ae5c-713aae507061.mp4/index.m3u8`

## Spider Strategy

- Generated production spider should not require CDP.
- Recommended session: `AsyncDynamicSession`; switch to `AsyncStealthySession` if runtime validation gets target-side 400/403.
- Set `google_search=False`, `network_idle=False`, `capture_xhr="/api/cms/getsection"`.
- No pagination for current request. API supports pagination with `page` up to `msg.last_page` if needed later.
- Allow detail domains `www.yntv.cn` and media domain `video.yntv.cn` if collecting video URLs.
