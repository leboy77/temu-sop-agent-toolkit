---
name: temu-market-research
description: >
  Temu 欧洲 Y2 与美国 Y1 POD 类目研究 Agent。读取类目商品导出，
  计算容量、价格带、品牌/卖家集中度、款式与 SKU 分布、新上架信号，
  并输出是否继续开发、目标价格带和待补数据。用于看类目、比竞品、
  判断新品窗口和确定产品配置。
allowed-tools:
  - Bash(python *)
  - Read
  - Write
metadata:
  version: 0.1.0
  category: e-commerce/temu-market-research
  license: MIT
---

# Temu Market Research Skill

## 启动顺序

1. 确认 `market_id`、目标国家、币种、销量窗口和数据日期。
2. 运行 `scripts/temu_parser.py`，缺关键字段时先修数据，不进入分析。
3. 运行 `scripts/temu_market_metrics.py`，指标只引用脚本输出。
4. 使用 `prompts/01_category_precheck.md` 判断是否值得继续。
5. 前置通过后，使用 `prompts/02_market_analysis.md` 解读价格带、集中度、配置和新品窗口。
6. 将结果按 `templates/output_market_analysis.md` 交给核价、商品卡和内容模块。

## 硬约束

- 不编造销量、价格、品牌、卖家、上架时间或评论。
- 单期数据不得推断增长或下滑。
- 样本不足时不给精确集中度结论。
- 不以竞品图片、标题或参数直接充当己方事实。
- 不把工具估算的上架时间当作平台事实。
- 不因为“市场有销量”跳过版权、认证、履约和售后判断。
- 最终是否开发商品由业务负责人决定。

## 最低可用输入

- 商品标题
- 当前售价
- 同一窗口的销量
- 卖家
- 品牌或“无品牌”
- 上架时间或上架天数
- 数据日期
- 市场与币种

推荐补充 SKU 数、颜色数、款式、图案、材质、评分、评价数、活动价和商品状态。
