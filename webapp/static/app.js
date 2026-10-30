const state = {
  csv: "",
  filename: "",
  result: null,
  health: null,
};

const $ = (selector) => document.querySelector(selector);
const market = $("#marketId");
const currency = $("#currency");
const dataDate = $("#dataDate");
const dropZone = $("#dropZone");
const fileInput = $("#fileInput");
const analyzeButton = $("#analyzeButton");
const aiButton = $("#aiButton");
const aiButtonTop = $("#aiButtonTop");
const message = $("#message");

function localDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const formatters = {
  money(value) {
    const code = state.result?.metrics?.meta?.currency || currency.value;
    return `${code} ${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  },
  percent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
  },
  number(value) {
    return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
  },
};

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setAiEnabled(enabled) {
  aiButton.disabled = !enabled;
  aiButtonTop.disabled = !enabled || !state.result;
}

function el(tag, attrs = {}, text = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "className") node.className = value;
    else node.setAttribute(key, value);
  });
  if (text !== "") node.textContent = text;
  return node;
}

function table(headers, rows) {
  const wrapper = el("div", { className: "table-wrap" });
  const dataTable = el("table");
  const thead = el("thead");
  const headRow = el("tr");
  headers.forEach(([label, numeric]) => headRow.append(el("th", numeric ? { className: "num" } : {}, label)));
  thead.append(headRow);
  const tbody = el("tbody");
  rows.forEach((row) => {
    const tr = el("tr");
    row.forEach(([value, numeric]) => tr.append(el("td", numeric ? { className: "num" } : {}, value)));
    tbody.append(tr);
  });
  dataTable.append(thead, tbody);
  wrapper.append(dataTable);
  return wrapper;
}

function readFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    state.csv = String(reader.result || "");
    state.filename = file.name;
    analyzeButton.disabled = false;
    setMessage(`已载入 ${file.name}`);
  };
  reader.onerror = () => setMessage("文件读取失败", true);
  reader.readAsText(file, "utf-8");
}

function requestOptions(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    state.health = await response.json();
    const apiStatus = $("#apiStatus");
    apiStatus.textContent = state.health.openai_configured
      ? `OpenAI 已配置 · ${state.health.model}`
      : "OpenAI 未配置";
    apiStatus.className = state.health.openai_configured ? "status ok" : "status muted";
    setAiEnabled(Boolean(state.health.openai_configured));
    $("#aiModel").textContent = state.health.model;
  } catch {
    $("#apiStatus").textContent = "本地服务不可用";
    $("#apiStatus").className = "status muted";
  }
}

async function analyze() {
  if (!state.csv.trim()) return;
  analyzeButton.disabled = true;
  setMessage("正在清洗数据并计算指标…");
  try {
    const response = await fetch(
      "/api/analyze",
      requestOptions({
        csv: state.csv,
        filename: state.filename,
        market_id: market.value,
        currency: currency.value,
        sales_window_days: Number($("#salesWindow").value),
        data_date: dataDate.value,
        as_of: dataDate.value,
        config_fields: $("#configFields").value.split(",").map((item) => item.trim()).filter(Boolean),
      }),
    );
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "分析失败");
    showResult(result);
    setMessage("分析完成。指标由脚本计算，业务判断仍需人工确认。");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    analyzeButton.disabled = false;
  }
}

function showResult(result) {
  state.result = result;
  const metrics = result.metrics;
  const meta = metrics.meta;
  const capacity = metrics.market_capacity;

  $("#emptyState").hidden = true;
  $("#resultsContent").hidden = false;
  $("#resultTitle").textContent = meta.market_id === "us-y1-pod" ? "美国 Y1 POD" : "欧洲 Y2";
  $("#resultMeta").textContent = `${meta.data_date} · ${meta.sales_window_days} 天销量窗口 · ${meta.currency}`;
  $("#rowCount").textContent = `${meta.row_count_kept} / ${meta.row_count_raw} 行`;
  $("#priceRange").textContent =
    metrics.price_bands.price_range?.length === 2
      ? `${formatters.money(metrics.price_bands.price_range[0])} - ${formatters.money(metrics.price_bands.price_range[1])}`
      : "无价格范围";
  $("#aiPanel").hidden = true;
  setAiEnabled(Boolean(state.health?.openai_configured));
  aiButtonTop.disabled = !state.health?.openai_configured;

  const kpiData = [
    ["窗口销量", formatters.number(capacity.total_sales), "样本商品合计"],
    ["窗口销售额", formatters.money(capacity.total_revenue), "由价格 × 销量补齐"],
    ["隐含均价", formatters.money(capacity.implied_average_price), `中位价 ${formatters.money(capacity.median_price)}`],
    ["单品均销", formatters.number(capacity.average_sales_per_listing), `${capacity.listing_count} 个商品`],
  ];
  $("#kpis").replaceChildren(
    ...kpiData.map(([label, value, note]) => {
      const card = el("article", { className: "kpi" });
      card.append(el("span", {}, label), el("strong", {}, value), el("small", {}, note));
      return card;
    }),
  );

  renderPriceBands(metrics.price_bands);
  renderConcentration(metrics.brand_concentration, metrics.seller_concentration);
  renderNewListing(metrics.new_listing_signal);
  renderConfigs(metrics.config_matrix);
  renderPreview(result.items);
}

function renderPriceBands(priceBands) {
  const bands = priceBands.suggested_bands || [];
  const maxSales = Math.max(...bands.map((band) => band.sales), 1);
  $("#priceChart").replaceChildren(
    ...bands.map((band) => {
      const row = el("div", { className: "bar-row" });
      row.append(
        el("span", { className: "bar-label" }, `${formatters.money(band.price_low)} - ${formatters.money(band.price_high)}`),
      );
      const track = el("div", { className: "bar-track" });
      const fill = el("div", { className: "bar-fill" });
      fill.style.width = `${Math.max((band.sales / maxSales) * 100, 2)}%`;
      track.append(fill);
      row.append(track, el("strong", { className: "bar-value" }, formatters.number(band.sales)));
      return row;
    }),
  );
  $("#bandTable").replaceChildren(
    table(
      [["价格带"], ["商品数", true], ["销量", true], ["单品均销", true], ["销售额", true]],
      bands.map((band) => [
        [`${formatters.money(band.price_low)} - ${formatters.money(band.price_high)}`, false],
        [band.item_count, true],
        [formatters.number(band.sales), true],
        [formatters.number(band.average_sales), true],
        [formatters.money(band.revenue), true],
      ]),
    ),
  );
}

function concentrationCard(data, label) {
  const box = el("div", { className: "metric-list" });
  [
    ["主体数", data.subject_count],
    ["CR3", formatters.percent(data.cr3)],
    ["CR10", formatters.percent(data.cr10)],
    ["HHI", data.hhi],
  ].forEach(([name, value]) => {
    const line = el("div", { className: "metric-line" });
    line.append(el("span", {}, name), el("strong", {}, value));
    box.append(line);
  });
  const top = data.top_list?.[0];
  if (top) {
    const line = el("div", { className: "metric-line" });
    line.append(el("span", {}, `头部${label}`), el("strong", {}, `${top.name} · ${formatters.percent(top.revenue_share)}`));
    box.append(line);
  }
  if (data.warning) box.append(el("p", { className: "warning" }, data.warning));
  if (data.missing_items) box.append(el("p", { className: "warning" }, `有 ${data.missing_items} 个商品缺少该字段。`));
  return box;
}

function renderConcentration(brand, seller) {
  const grid = el("div", { className: "two-column" });
  const brandCard = el("div");
  brandCard.append(el("p", { className: "eyebrow" }, "BRAND"), concentrationCard(brand, "品牌"));
  const sellerCard = el("div");
  sellerCard.append(el("p", { className: "eyebrow" }, "SELLER"), concentrationCard(seller, "卖家"));
  grid.append(brandCard, sellerCard);
  $("#concentration").replaceChildren(grid);
}

function renderNewListing(signal) {
  const box = el("div", { className: "metric-list" });
  const values = [
    ["新链接数量", signal.new_listing_count ?? 0],
    ["新链接商品占比", formatters.percent(signal.new_listing_item_share || 0)],
    ["新链接销量份额", formatters.percent(signal.new_listing_sales_share || 0)],
    ["相对全样本效率", `${formatters.number(signal.new_vs_all_efficiency || 0)}×`],
  ];
  values.forEach(([name, value]) => {
    const line = el("div", { className: "metric-line" });
    line.append(el("span", {}, name), el("strong", {}, value));
    box.append(line);
  });
  if (signal.status !== "OK") {
    box.append(el("p", { className: "warning" }, signal.reason || "新上架样本不足，暂不判断。"));
  }
  $("#newListing").replaceChildren(box);
}

function renderConfigs(matrix) {
  const selector = $("#configSelector");
  const fields = Object.keys(matrix || {});
  selector.replaceChildren(...fields.map((field) => el("option", { value: field }, field)));
  const draw = () => {
    const field = selector.value;
    if (!field || !matrix[field]) {
      $("#configMatrix").replaceChildren(el("p", { className: "warning" }, "没有可用的配置维度。"));
      return;
    }
    const data = matrix[field];
    $("#configMatrix").replaceChildren(
      table(
        [["配置值"], ["商品数", true], ["数量占比", true], ["销量占比", true], ["单品均销", true], ["标记"]],
        data.rows.map((row) => [
          [row.value, false],
          [row.item_count, true],
          [formatters.percent(row.item_share), true],
          [formatters.percent(row.sales_share), true],
          [formatters.number(row.average_sales), true],
          [row.flags.join(", ") || "-", false],
        ]),
      ),
    );
  };
  selector.onchange = draw;
  draw();
}

function renderPreview(items) {
  const rows = items.slice(0, 20).map((item) => [
    [item.title || "-", false],
    [formatters.money(item.price), true],
    [formatters.number(item.sales), true],
    [item.seller || "UNKNOWN", false],
    [item.brand || "UNKNOWN", false],
    [item.listing_age_days == null ? "-" : `${item.listing_age_days} 天`, true],
  ]);
  $("#dataPreview").replaceChildren(
    table(
      [["商品"], ["价格", true], ["销量", true], ["店铺"], ["品牌"], ["上架", true]],
      rows,
    ),
  );
}

async function runAi() {
  if (!state.result) return;
  const buttons = [aiButton, aiButtonTop];
  buttons.forEach((button) => { button.disabled = true; });
  $("#aiPanel").hidden = false;
  $("#aiOutput").textContent = "正在请求 OpenAI…";
  try {
    const response = await fetch(
      "/api/ai-analysis",
      requestOptions({
        metrics: state.result.metrics,
        business_context: $("#businessContext").value,
      }),
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "AI 分析失败");
    $("#aiOutput").textContent = payload.analysis;
    setMessage("OpenAI 分析完成。");
  } catch (error) {
    $("#aiOutput").textContent = error.message;
    setMessage(error.message, true);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") fileInput.click();
});
fileInput.addEventListener("change", () => fileInput.files[0] && readFile(fileInput.files[0]));
["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drag");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag");
  });
});
dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (file) readFile(file);
});

async function loadSample(sampleMarket) {
  setMessage("载入合成样本…");
  try {
    const response = await fetch(`/api/sample?market=${encodeURIComponent(sampleMarket)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "无法载入样本");
    state.csv = payload.csv;
    state.filename = payload.filename;
    market.value = sampleMarket;
    syncMarketCurrency();
    analyzeButton.disabled = false;
    setMessage(`已载入合成样本：${payload.filename}`);
    await analyze();
  } catch (error) {
    setMessage(error.message, true);
  }
}

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => loadSample(button.dataset.sample));
});

function syncMarketCurrency() {
  currency.value = market.value === "us-y1-pod" ? "USD" : "EUR";
  $("#configFields").value = market.value === "us-y1-pod"
    ? "print_theme,style,color_count,sku_count"
    : "style,material,color_count,sku_count";
}

market.addEventListener("change", syncMarketCurrency);
analyzeButton.addEventListener("click", analyze);
aiButton.addEventListener("click", runAi);
aiButtonTop.addEventListener("click", runAi);

dataDate.value = localDate();
syncMarketCurrency();
checkHealth().then(async () => {
  const params = new URLSearchParams(location.search);
  if (params.get("capture") === "1") {
    const response = await fetch("/api/capture/latest");
    if (response.ok) showResult(await response.json());
  } else if (params.get("sample")) {
    const sampleMarket = params.get("sample");
    if (sampleMarket === "us-y1-pod" || sampleMarket === "eu-y2") {
      await loadSample(sampleMarket);
    }
  }
});
