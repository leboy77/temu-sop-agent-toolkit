# 欧洲 Y2 试点

## 商品

- 商品卡：`DEMO-EU-Y2-001`
- 模式：半托管
- 类目：服饰
- SKU：深蓝 M
- 状态：`DRAFT`

## 目标

用一个低复杂度商品验证：

- 仓库和配送模板；
- VAT/欧代/制造商/包装资料；
- SKU 与图片映射；
- ERP 推单与面单；
- 每日核价与异常记录。

## 验收

```powershell
python scripts/calc_price.py examples/eu-y2/pilot-price-sheet.csv
```

核价通过后，完成 `templates/compliance_pack.md`，再进行上架。任何材料地址或主体不一致都应输出 `REVIEW_REQUIRED`。
