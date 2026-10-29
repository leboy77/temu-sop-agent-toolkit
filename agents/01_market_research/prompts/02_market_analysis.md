# TASK - Market Analysis

只有 `precheck_pass=true` 才能执行。所有指标只引用 `metrics_report`。

## 1. 数据可信度

声明样本量、数据日期、销量窗口、币种、配置字段解析失败数和上架时间来源。

## 2. 市场容量

解释：

- 窗口总销量和销售额
- 均价、中位价和隐含均价
- 单商品平均销量
- 单期数据是否足以判断趋势

## 3. 集中度

分别解释品牌和卖家：

- CR3、CR10、HHI
- 销售额份额与商品数份额
- 头部是品牌、白牌、效率型卖家还是铺品型卖家
- 主体少于 10 个时不使用 CR10 下结论

## 4. 价格带

- 描述销量曲线和显著波谷
- 对每个建议价格带给出商品数、销量、均销、收入和竞争强度
- 与成本结构交叉，标出市场好卖但公司无利润的区间
- 没有成本数据时输出 `【待确认】`

## 5. 配置与 SKU

按 `print_theme`、`style`、`material`、`fit`、`color_count`、`sku_count` 等维度解释：

- 主流但竞争激烈的配置
- 数量少但单品效率高的配置
- 是否被头部卖家占据
- 是否增加 POD、尺码或合规复杂度

## 6. 新上架信号

使用脚本的 `new_listing_signal`：

- 新链接数量、销量份额和平均销量
- 是否比成熟链接更强或更弱
- 是否存在低价驱动或小样本问题
- 若上架时间不可靠，明确停止该结论

## 7. 竞争与权利

仅描述可观察事实：

- 标题、主图、款式和价格策略
- 图案、材质和 SKU 差异
- 竞品评论中的需求信号
- 图片和图案是否存在未确认权利

不得断言竞品刷单或直接复制其素材。

## 8. 最终输出

```yaml
market_decision: supported_with_conditions
target_price_range: []
mainstream_config: {}
opportunity_config: {}
brand_barrier: low
seller_barrier: medium
new_listing_signal: {}
downstream_actions: []
pending_confirmations: []
```

`market_decision` 只能是：

- `supported`
- `supported_with_conditions`
- `not_supported`
- `data_insufficient`

末尾附分析合规扫描。
