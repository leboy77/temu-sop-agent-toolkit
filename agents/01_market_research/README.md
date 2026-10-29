# 01 - Temu Market Research Agent

Temu 版市场分析 Agent，覆盖欧洲 Y2 与美国 Y1 POD。它沿用“脚本计算、Agent 解读”的思路，但把参考框架中的 Shopee 巴西 / Mercado Livre 规则替换为 Temu 的销量窗口、价格带、款式与 SKU 结构、卖家集中度、新上架信号、履约和合规风险。

## 它回答什么

1. 这个类目是否适合公司当前货盘？
2. 数据里是否存在清晰的需求和价格带？
3. 品牌、卖家或少数链接是否占据了主要销量？
4. 哪些款式、图案、材质或 SKU 组合可能是机会？
5. 新品是否还有进入空间？
6. 下一步应做哪一个价格带和商品配置？

它不负责最终选品审批、供应商压价、正式定价或自动上架。

## 处理链

```text
类目导出
  -> temu_parser.py
  -> normalized.json
  -> temu_market_metrics.py
  -> metrics.json + metrics.md
  -> 01_category_precheck.md
  -> 02_market_analysis.md
  -> 下游商品卡 / 核价 / 内容模块
```

## 脚本

```powershell
python agents/01_market_research/scripts/temu_parser.py `
  agents/01_market_research/samples/us-y1-pod-listings.csv `
  --market-id us-y1-pod `
  --currency USD `
  --sales-window-days 30 `
  --data-date 2026-10-29

python agents/01_market_research/scripts/temu_market_metrics.py `
  agents/01_market_research/samples/us-y1-pod-listings.normalized.json `
  --config agents/01_market_research/configs/us-y1-pod.json `
  --config-fields "print_theme,style,color_count"
```

## 模块边界

| 由脚本负责 | 由 Agent 负责 |
| --- | --- |
| 容量、均价、价格分箱 | 判断市场是否有足够机会 |
| 品牌/卖家 CR3、CR10、HHI | 判断壁垒来自品牌、产品还是店铺 |
| 款式/配置交叉表 | 判断哪个配置适合公司 |
| 新上架数量与销量份额 | 判断新品是否仍有窗口 |
| 榜单和原始字段 | 解释竞争结构、风险和下一步证据 |

## 数据口径

- 每次分析必须声明市场、币种、数据日期和销量窗口。
- 单期快照只能描述“现在”，不能判断增长或下滑。
- 商品价格必须使用同一币种；EUR、USD、CNY 不能混合。
- `listing_age_days` 需要注明是平台展示、工具估算还是人工核对。
- 缺失销量、价格、品牌和上架时间时应明确标注，不能猜。

## 市场差异

- **欧洲 Y2**：额外检查 VAT、欧代、制造商、包装 EPR、标签、多国仓配和语言。
- **美国 Y1 POD**：额外检查图案和人物版权、尺码、图案在不同底色上的呈现、三仓配送和 POD/普通商品模式。

详见 [configs](configs/) 与 [prompts](prompts/)。

## 参考来源

结构参考 MIT 项目 [AI-Cross-Border-Ecommerce-Agent-Toolkit](https://github.com/heqiangdiao-wq/AI-Cross-Border-Ecommerce-Agent-Toolkit) 的市场分析模块；本目录为针对 Temu 的独立实现，不沿用其巴西市场阈值作为平台规则。
