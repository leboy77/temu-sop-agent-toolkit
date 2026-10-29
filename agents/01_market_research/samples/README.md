# Samples

本目录数据全部为合成数据，用于验证 Temu 市场分析 Agent 的清洗、计算和报告流程，不代表任何真实市场。

## 文件

- `us-y1-pod-listings.csv`：美国 Y1 POD 抓绒马甲类目的模拟导出。
- `us-y1-pod-listings.normalized.json`：标准化数据。
- `us-y1-pod-listings.metrics.json`：机器可读指标。
- `us-y1-pod-listings.metrics.md`：报告预览。
- `eu-y2-listings.csv`：欧洲 Y2 摇粒绒休闲裤类目的模拟导出。
- `eu-y2-listings.normalized.json`：标准化数据。
- `eu-y2-listings.metrics.json`：机器可读指标。
- `eu-y2-listings.metrics.md`：报告预览。

## 重新生成

```powershell
python agents/01_market_research/scripts/make_sample.py

python agents/01_market_research/scripts/temu_parser.py `
  agents/01_market_research/samples/us-y1-pod-listings.csv `
  --market-id us-y1-pod `
  --currency USD `
  --sales-window-days 30 `
  --data-date 2026-10-29 `
  --as-of 2026-10-29

python agents/01_market_research/scripts/temu_market_metrics.py `
  agents/01_market_research/samples/us-y1-pod-listings.normalized.json `
  --config agents/01_market_research/configs/us-y1-pod.json `
  --config-fields "print_theme,style,color_count,sku_count"
```

样本包含货币符号、千分位、上架日期、缺失销售额等脏数据，用于验证解析器。
