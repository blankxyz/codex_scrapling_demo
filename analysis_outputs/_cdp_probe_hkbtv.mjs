import fs from "node:fs/promises";
import path from "node:path";

const URL = process.argv[2] || "https://hkbtv.cn/#/common1858408493966991361?type=1858408493966991361";
const OUT = process.argv[3] || "analysis_outputs/_hkbtv_probe.json";

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function createTarget(url) {
  const resp = await fetch(`http://127.0.0.1:9222/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  return resp.json();
}

async function closeTarget(id) {
  try {
    await fetch(`http://127.0.0.1:9222/json/close/${id}`);
  } catch {}
}

async function ensureOutDir(file) {
  await fs.mkdir(path.dirname(file), { recursive: true });
}

async function main() {
  const target = await createTarget("about:blank");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  const pending = new Map();
  const responses = new Map();
  let seq = 0;

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject, method });
      ws.send(JSON.stringify({ id, method, params }));
    });

  ws.onmessage = async event => {
    const msg = JSON.parse(event.data.toString());
    if (msg.id) {
      const task = pending.get(msg.id);
      if (!task) return;
      pending.delete(msg.id);
      if (msg.error) task.reject(msg.error);
      else task.resolve(msg.result);
      return;
    }

    if (msg.method === "Network.requestWillBeSent") {
      const p = msg.params;
      responses.set(p.requestId, {
        ...(responses.get(p.requestId) || {}),
        requestId: p.requestId,
        url: p.request.url || "",
        method: p.request.method,
        postData: (p.request.postData || "").slice(0, 120000),
        requestHeaders: p.request.headers || {},
        type: p.type || "",
      });
    }

    if (msg.method === "Network.responseReceived") {
      const p = msg.params;
      const url = p.response.url || "";
      if (!["Document", "XHR", "Fetch"].includes(p.type)) return;
      responses.set(p.requestId, {
        ...(responses.get(p.requestId) || {}),
        requestId: p.requestId,
        url,
        method: (responses.get(p.requestId) || {}).method || "",
        postData: (responses.get(p.requestId) || {}).postData || "",
        requestHeaders: (responses.get(p.requestId) || {}).requestHeaders || {},
        type: p.type,
        status: p.response.status,
        mimeType: p.response.mimeType,
        headers: p.response.headers,
      });
    }

    if (msg.method === "Network.loadingFinished") {
      const item = responses.get(msg.params.requestId);
      if (!item || item.body !== undefined) return;
      try {
        const body = await send("Network.getResponseBody", { requestId: msg.params.requestId });
        item.body = (body.body || "").slice(0, 300000);
        item.base64Encoded = !!body.base64Encoded;
      } catch {
        item.body = "";
      }
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  await send("Page.enable");
  await send("Network.enable", { maxTotalBufferSize: 0, maxResourceBufferSize: 0 });
  await send("Runtime.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", {
    source: `
      (() => {
        const trim = value => String(value || '').slice(0, 300000);
        window.__capture = [];
        const push = item => {
          try { window.__capture.push(item); } catch {}
        };
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
          const [input, init] = args;
          const method = (init && init.method) || (input && input.method) || 'GET';
          const body = (init && init.body) || '';
          const url = typeof input === 'string' ? input : (input && input.url) || '';
          const res = await origFetch.apply(this, args);
          try {
            const clone = res.clone();
            const text = await clone.text();
            push({ kind: 'fetch', url, method, body: trim(body), status: res.status, responseText: trim(text), contentType: clone.headers.get('content-type') || '' });
          } catch {}
          return res;
        };
        const open = XMLHttpRequest.prototype.open;
        const send = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
          this.__captureMethod = method;
          this.__captureUrl = url;
          return open.call(this, method, url, ...rest);
        };
        XMLHttpRequest.prototype.send = function(body) {
          this.addEventListener('loadend', function() {
            try {
              push({
                kind: 'xhr',
                url: this.__captureUrl || '',
                method: this.__captureMethod || 'GET',
                body: trim(body || ''),
                status: this.status,
                responseText: trim(this.responseText || ''),
                contentType: this.getResponseHeader('content-type') || ''
              });
            } catch {}
          });
          return send.call(this, body);
        };
      })();
    `,
  });
  await send("Page.navigate", { url: URL });
  await sleep(18000);

  const dom = await send("Runtime.evaluate", {
    returnByValue: true,
    expression: `(() => {
      const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
      const listNodes = [...document.querySelectorAll('.cont_item, .li, .card, .card_list, .module_card, [class*=card], [class*=list]')];
      const titleNodes = [...document.querySelectorAll('.title, .label, [class*=title], h1, h2, h3')];
      const anchors = [...document.querySelectorAll('a[href]')].map(node => ({
        tag: node.tagName.toLowerCase(),
        className: node.className || '',
        text: text(node).slice(0, 240),
        href: node.href || node.getAttribute('href') || ''
      })).filter(x => x.href).slice(0, 300);
      const firstTitles = [];
      for (const node of titleNodes) {
        const value = text(node);
        if (value && value.length > 6 && !firstTitles.includes(value)) firstTitles.push(value);
        if (firstTitles.length >= 40) break;
      }
      const cards = listNodes.map(node => ({
        tag: node.tagName.toLowerCase(),
        className: node.className || '',
        text: text(node).slice(0, 300),
        title: node.getAttribute('title') || '',
        href: node.getAttribute('href') || node.href || '',
      })).filter(x => x.text).slice(0, 120);
      const headings = [...document.querySelectorAll('h1,h2,h3,h4,.title,[class*=title],[class*=menu],[class*=nav]')]
        .map(node => ({ tag: node.tagName.toLowerCase(), className: node.className || '', text: text(node).slice(0, 120) }))
        .filter(x => x.text).slice(0, 120);
      return {
        url: location.href,
        title: document.title,
        bodyText: text(document.body).slice(0, 12000),
        cardCount: document.querySelectorAll('.cont_item').length || document.querySelectorAll('.li').length,
        firstTitles,
        anchors,
        cards,
        headings,
        html: document.documentElement.outerHTML.slice(0, 250000)
      };
    })()`,
  });

  await send("Runtime.evaluate", {
    expression: `(() => {
      const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
      const current = location.href;
      const sameHost = href => {
        try { return new URL(href, location.href).host === location.host; } catch { return false; }
      };
      const anchor = [...document.querySelectorAll('a[href]')].find(a => {
        const href = a.href || a.getAttribute('href') || '';
        return href && href !== current && sameHost(href) && text(a).length > 6 && !href.startsWith('javascript:');
      });
      if (anchor) {
        location.href = anchor.href || anchor.getAttribute('href');
        return;
      }
      const first = document.querySelector(
        '.cont_item .card_list, .cont_item .card, .li .card, .li section, article, [class*=item], [class*=card], [class*=list] > *'
      );
      if (first) first.click();
    })()`,
  });
  await sleep(8000);

  const detail = await send("Runtime.evaluate", {
    returnByValue: true,
    expression: `(() => {
      const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
      const candidates = [...document.querySelectorAll('h1,h2,h3,.title,[class*=title],main,article,.content,[class*=content],p')]
        .map(node => ({
          tag: node.tagName.toLowerCase(),
          className: node.className || '',
          text: text(node).slice(0, 1000)
        }))
        .filter(x => x.text).slice(0, 160);
      return {
        url: location.href,
        title: document.title,
        bodyText: text(document.body).slice(0, 12000),
        candidates,
        html: document.documentElement.outerHTML.slice(0, 250000)
      };
    })()`,
  });

  const browserCapture = await send("Runtime.evaluate", {
    returnByValue: true,
    expression: "window.__capture || []",
  });

  const payload = {
    source_url: URL,
    dom: dom.result.value,
    detail: detail.result.value,
    network: [...responses.values()],
    browserCapture: browserCapture.result.value,
  };

  await ensureOutDir(OUT);
  await fs.writeFile(OUT, JSON.stringify(payload, null, 2), "utf8");
  await closeTarget(target.id);
  ws.close();
  console.log(OUT);
}

main().catch(async err => {
  console.error(err);
  process.exit(1);
});
