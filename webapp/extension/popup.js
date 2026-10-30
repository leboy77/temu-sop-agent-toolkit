const $ = (selector) => document.querySelector(selector);
const captureButton = $("#capture");
const sendButton = $("#send");
const downloadCsvButton = $("#downloadCsv");
const downloadJsonButton = $("#downloadJson");
let captured = null;

function localDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setStatus(text, type = "") {
  const node = $("#status");
  node.textContent = text;
  node.className = `status ${type}`.trim();
}

function captureTemuListings(cardSelector) {
  const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const numberFromText = (text) => {
    const match = String(text || "").replace(/\s/g, "").match(/(\d[\d,.]*)(万|亿|K|M|\+)?/i);
    if (!match) return null;
    let value = Number(match[1].replace(/,/g, ""));
    if (!Number.isFinite(value)) return null;
    const suffix = (match[2] || "").toUpperCase();
    if (suffix === "万") value *= 10000;
    if (suffix === "亿") value *= 100000000;
    if (suffix === "K") value *= 1000;
    if (suffix === "M") value *= 1000000;
    return value;
  };
  const looksLikeProductUrl = (url) =>
    /\/(goods|product)|\-g-\d+|\-s\.html/i.test(url);
  const priceFrom = (text) => {
    const money = text.match(/(?:US\$|USD|EUR|CNY|R\$|\$|€|¥)\s*([\d.,]+)|([\d.,]+)\s*(?:USD|EUR|CNY)/i);
    return money ? numberFromText(money[1] || money[2]) : null;
  };
  const soldFrom = (text) => {
    const match = text.match(/([\d.,]+\s*[KkMm万]?\+?)\s*(?:sold|pieces|items|件|已售)/i)
      || text.match(/(?:已售|销量)\s*([\d.,]+\s*[KkMm万]?\+?)/i);
    return match ? numberFromText(match[1]) : null;
  };
  const ratingFrom = (text) => {
    const match = text.match(/(?:rating|评分)\s*([0-5](?:\.\d)?)|([0-5](?:\.\d)?)\s*★/i);
    return match ? Number(match[1] || match[2]) : null;
  };
  const reviewFrom = (text) => {
    const match = text.match(/([\d,.]+)\s*(?:reviews?|评价|评论)/i);
    return match ? numberFromText(match[1]) : null;
  };
  const ageFrom = (text) => {
    const days = text.match(/(\d+)\s*(?:days?|天)\s*(?:ago|前)?/i);
    if (days) return Number(days[1]);
    const months = text.match(/(\d+)\s*(?:months?|个月)\s*(?:ago|前)?/i);
    return months ? Number(months[1]) * 30 : null;
  };

  const cards = cardSelector
    ? [...document.querySelectorAll(cardSelector)]
    : [...document.querySelectorAll("a[href]")]
        .filter((anchor) => looksLikeProductUrl(anchor.href))
        .map((anchor) => {
          let node = anchor;
          for (let depth = 0; depth < 8 && node.parentElement; depth += 1) {
            node = node.parentElement;
            if (
              priceFrom(node.innerText) !== null &&
              clean(node.innerText).length > 15
            ) break;
          }
          return node;
        });

  const rows = [];
  const seen = new Set();
  for (const card of cards) {
    if (!(card instanceof Element)) continue;
    const anchors = card.matches("a[href]")
      ? [card]
      : [...card.querySelectorAll("a[href]")].filter((anchor) => looksLikeProductUrl(anchor.href));
    const anchor = anchors[0];
    if (!anchor || seen.has(anchor.href)) continue;
    seen.add(anchor.href);
    const text = clean(card.innerText);
    const imageAlt = [...card.querySelectorAll("img")].map((img) => clean(img.alt)).find(Boolean);
    const title = clean(anchor.innerText) || imageAlt || text.slice(0, 180);
    const price = priceFrom(text);
    if (!title || price === null) continue;
    rows.push({
      title,
      price,
      sales: soldFrom(text),
      seller: "UNKNOWN",
      brand: "UNKNOWN",
      rating: ratingFrom(text),
      review_count: reviewFrom(text),
      listing_age_days: ageFrom(text),
      url: anchor.href,
      status: "visible_capture"
    });
  }
  return {
    pageUrl: location.href,
    pageTitle: document.title,
    rows
  };
}

async function capture() {
  captureButton.disabled = true;
  setStatus("正在读取当前页面…");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("无法获取当前标签页");
    const [injection] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: captureTemuListings,
      args: [$("#cardSelector").value.trim()],
    });
    const data = injection?.result;
    if (!data || !data.rows?.length) {
      throw new Error("未识别到商品。请在插件中填写商品卡片 CSS 选择器后重试。");
    }
    captured = {
      market_id: $("#market").value,
      currency: $("#currency").value,
      sales_window_days: Number($("#salesWindow").value),
      target_market: $("#market").value === "us-y1-pod" ? "United States" : "Europe",
      data_date: localDate(),
      page_url: data.pageUrl,
      page_title: data.pageTitle,
      items: data.rows,
    };
    $("#captureSummary").innerHTML = `捕获 <strong>${data.rows.length}</strong> 个商品，其中 ${data.rows.filter((row) => row.sales != null).length} 个包含页面销量。`;
    sendButton.disabled = false;
    downloadCsvButton.disabled = false;
    downloadJsonButton.disabled = false;
    setStatus("采集完成。确认销量口径后再分析。", "ok");
  } catch (error) {
    captured = null;
    sendButton.disabled = true;
    downloadCsvButton.disabled = true;
    downloadJsonButton.disabled = true;
    setStatus(error.message || String(error), "error");
  } finally {
    captureButton.disabled = false;
  }
}

async function sendToDashboard() {
  if (!captured) return;
  if (!captured.sales_window_days) {
    setStatus("页面销量口径不确定，请选择 7/30/90 天或先导出 JSON。", "error");
    return;
  }
  sendButton.disabled = true;
  setStatus("正在发送到本地分析台…");
  try {
    const response = await fetch("http://127.0.0.1:8766/api/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(captured),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "本地分析台拒绝了数据");
    setStatus("发送成功，正在打开分析台。", "ok");
    await chrome.storage.local.set({
      lastCaptureAt: new Date().toISOString(),
      lastCaptureCount: captured.items.length,
    });
    await chrome.tabs.create({ url: "http://127.0.0.1:8766/?capture=1" });
  } catch (error) {
    setStatus(`${error.message} 可先下载 JSON 再上传。`, "error");
  } finally {
    sendButton.disabled = false;
  }
}

function downloadJson() {
  if (!captured) return;
  const blob = new Blob([JSON.stringify(captured, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `temu-capture-${Date.now()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function downloadCsv() {
  if (!captured) return;
  const columns = [
    "title", "price", "sales", "seller", "brand", "rating", "review_count",
    "listing_age_days", "sku_count", "color_count", "url", "status",
  ];
  const escape = (value) => {
    const text = value == null ? "" : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  };
  const rows = [
    columns.join(","),
    ...captured.items.map((item) => columns.map((column) => escape(item[column])).join(",")),
  ];
  const blob = new Blob([`\ufeff${rows.join("\r\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `temu-capture-${captured.market_id}-${captured.data_date}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

$("#market").addEventListener("change", () => {
  $("#currency").value = $("#market").value === "us-y1-pod" ? "USD" : "EUR";
});
captureButton.addEventListener("click", capture);
sendButton.addEventListener("click", sendToDashboard);
downloadCsvButton.addEventListener("click", downloadCsv);
downloadJsonButton.addEventListener("click", downloadJson);
