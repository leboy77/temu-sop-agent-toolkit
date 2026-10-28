# 00 - Orchestrator

## 职责

根据商品当前状态决定下一步、检查上游输入、记录阻塞项，并阻止模块越级执行。

## 最小输入

- `market_id`
- `product_brief_id`
- 当前状态
- 已完成的质量门
- 上游产物版本

## 输出

```yaml
product_brief_id: ""
market_id: ""
current_state: ""
next_action: ""
passed_gates: []
blocking_items: []
required_owner: ""
run_id: ""
```

## 规则

1. 每次只推进一个状态。
2. 输入缺失时停止，列出缺失字段和受影响模块。
3. 商品卡版本变化后，重新检查受影响的质量门。
4. 发布、推单、退款和资金动作必须包含人工审批记录。
5. 不在一个任务中同时修改价格、图片和合规资料，避免无法归因。
