---
name: temu-sop-agent-toolkit
description: >
  Temu 欧洲 Y2 与美国 Y1 POD 运营 SOP 总入口。用于选品、核价、SKU、
  商品素材、合规、上架、ERP/履约、活动、流量、广告和售后分析。
  不用于绕过平台规则、伪造数据、自动审批或未经人工确认的批量提交。
metadata:
  version: 0.2.0
  category: e-commerce/temu-operations
  status: draft
---

# Temu SOP Skill

先确定市场和当前商品状态，再进入对应模块。任何模块都不得跳过上游阻塞项。

## 路由

| 任务 | 入口 |
| --- | --- |
| 判断当前该做什么、检查上下游是否齐全 | `modules/00_orchestrator/README.md` |
| 选品、采集、款式筛选 | `modules/01_selection/README.md` |
| 核价、SKU 结构、最低价 | `modules/02_pricing/README.md` |
| 商品图、SKC 颜色图、标题和卖点 | `modules/03_assets/README.md` |
| 商品列表字段、模板和批量发布 | `modules/04_listing/README.md` |
| 税务、欧代、制造商、标签和图片合规 | `modules/05_compliance/README.md` |
| 订单推送、面单、库存和物流 | `modules/06_fulfillment/README.md` |
| 活动、流量加速和广告诊断 | `modules/07_growth/README.md` |
| 售后、退款、差评和知识回流 | `modules/08_aftersales/README.md` |

## 硬约束

1. 缺少商品参数、价格、图片授权或合规资料时输出 `[INPUT_MISSING]`，不得猜测。
2. 售价低于 `break_even_price` 时阻止发布，除非业务负责人明确记录战略亏损及退出条件。
3. 合规资料不完整时阻止正式上架，不用“先上架后补”替代审批。
4. 提交结果未知时只做状态查询；确认失败后才能按重试策略重新提交。
5. 所有面向买家的文本使用目标市场语言；内部备注使用中文。
6. 原始内部 PDF、后台截图、真实账号和敏感地址只保存在私有环境。

## 输出

每次完整运行时输出：

- 当前状态和下一状态
- 已完成的质量门
- 阻塞项及负责人
- 本次使用的市场配置版本
- 商品、价格、素材和合规产物路径
- 可复测的成功指标
