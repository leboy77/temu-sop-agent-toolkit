# 04 - Exception Taxonomy

| 类型 | 典型原因 | 处理 |
| --- | --- | --- |
| `INPUT_MISSING` | 商品参数、成本、重量、合规资料缺失 | 停止并补齐，不猜测 |
| `PRICE_BELOW_FLOOR` | 券后价或活动价低于盈亏线 | 阻止发布，提交审批 |
| `ASSET_MISMATCH` | SKU、色值、图片数量或文件不对应 | 重建素材绑定 |
| `ASSET_QUALITY_REJECTED` | 图片尺寸、清晰度、合规或版权问题 | 标记不可自动重试，换图后重建 |
| `COMPLIANCE_REJECTED` | 税务、主体、标签、参数或敏感表述不合规 | 人工作出整改决定 |
| `AUTH_EXPIRED` | 店铺或 ERP 授权失效 | 重新授权，不重试提交 |
| `PLATFORM_LIMIT` | 当日上架数量、对象数或字段限制 | 分批拆单 |
| `ERP_TIMEOUT` | 推单、查询或面单接口超时 | 先查询幂等状态，再决定是否重试 |
| `PUBLISH_UNKNOWN` | 点击后未拿到明确结果 | 查询商品列表，禁止直接重复提交 |
| `FULFILLMENT_DELAY` | 仓库、物流、库存或面单异常 | 责任人和预计恢复时间写入日志 |
| `DATA_INSUFFICIENT` | 曝光、订单或评论量不足 | 只记录观察，不给优化结论 |

## 重试规则

1. `INPUT_MISSING`、`COMPLIANCE_REJECTED`、`PRICE_BELOW_FLOOR` 不允许自动重试。
2. `AUTH_EXPIRED` 先恢复授权，再重新执行前置检查。
3. `ERP_TIMEOUT`、`PUBLISH_UNKNOWN` 必须先查询当前状态。
4. 只在确认变更未生效时重试。
5. 每次重试保留原 `run_id` 和重试序号，记录变更。

## 异常记录最小字段

`run_id, product_brief_id, stage, error_type, symptom, evidence, retryable, owner, action, result, timestamp`
