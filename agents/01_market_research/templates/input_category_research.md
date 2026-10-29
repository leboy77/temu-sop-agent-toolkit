# Temu 类目研究输入

```yaml
market_id: eu-y2 | us-y1-pod
platform: temu
target_market: ""
category: ""
currency: ""
sales_window_days: 30
data_date: "YYYY-MM-DD"
data_source: ""

metrics_report: ""
sample_size: 0

company_capabilities:
  has_stock_or_incoming: false
  has_stable_supplier: false
  cost_is_acceptable: false
  fits_target_market: false
  fits_warehouse_and_shipping: false
  can_handle_size_and_after_sales: false
  notes: ""

product_profile:
  weight_kg: 0
  package_dimensions: ""
  material: ""
  color_count: 0
  sku_count: 0
  is_pod: false
  has_print_or_character: false
  rights_status: pending
  requires_certification: []
  contains_battery: false

cost_structure:
  currency: ""
  unit_cost: 0
  freight: 0
  platform_fee_rate: 0
  ad_cost_rate: 0
  return_rate: 0
  target_margin_rate: 0
  notes: ""

competitors: []
competitor_reviews: []
config_dimensions: []
pending_confirmations: []
```

## 数据规则

- `price` 使用当前成交或页面展示价，不混用申报价。
- `sales` 使用与 `sales_window_days` 一致的窗口。
- 币种不能混合。
- 竞品使用 A/B/C 代号，不公开真实店铺名。
- 缺失字段留空并标记，不填估计值。
