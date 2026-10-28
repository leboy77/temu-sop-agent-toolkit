# 美国 Y1 POD 试点

## 商品

- 商品卡：`DEMO-US-POD-001`
- 模式：POD
- 类目：休闲裤
- SKU：黑色 M
- 状态：`DRAFT`

## 运行假设

- 采购价：50 CNY
- 重量：0.6 kg
- 示例运费：70 CNY/kg + 5 CNY
- 退货率：7%
- 平台费：10%
- 广告费：5%
- 目标毛利率：20%
- 拟售价：150 CNY

## 验收

运行：

```powershell
python scripts/calc_price.py examples/us-y1-pod/pilot-price-sheet.csv
```

如果状态为 `REVIEW_REQUIRED` 或 `BLOCKED`，必须调整价格或成本，不得进入素材生产。

## 后续步骤

1. 补齐商品卡中的材质、尺码表和图片。
2. 先测试基础款，不做批量裂变。
3. 通过合规检查后再生成批量模板。
