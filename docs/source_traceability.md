# Source Traceability

本文件记录两份内部资料如何映射到新框架。原始 PDF 不进入代码仓库，仅保留本页的页级索引。

## 欧洲 Y2

| 原始页 | 内容 | 新位置 |
| --- | --- | --- |
| 1-3 | 仓库、配送区域和运费模板 | `markets/eu-y2/setup_and_fulfillment.md` |
| 4-14 | 采集、商品模板、SKU 和图片准备 | `modules/01_selection`, `modules/03_assets` |
| 15-18 | VAT、欧代、制造商和包装法 | `markets/eu-y2/compliance.md` |
| 19-31 | ERP 绑定、订单推送和面单 | `modules/06_fulfillment` |
| 32-40 | 库存、批量合规和活动 | `modules/04_listing`, `modules/07_growth` |
| 41-48 | PS 模板、AI 生图和任务执行 | `modules/03_assets` |
| 49-50 | 每日运营与异常动作 | `markets/eu-y2/daily_operations.md` |
| 51-60 | 自动复色、下架归档、广告监控 | `automations/` |

## 美国 Y1 POD

| 原始页 | 内容 | 新位置 |
| --- | --- | --- |
| 1-5 | 三仓、运费、核价表与测试款 | `markets/us-y1-pod/`, `modules/02_pricing` |
| 6-13 | 运营平台绑定、配置与采集 | `markets/us-y1-pod/setup_and_fulfillment.md` |
| 14-20 | 店铺配置、POD/普通商品业务模式 | `markets/us-y1-pod/market_profile.json` |
| 21-23 | 尺码表、SKC 颜色图和店铺模板 | `modules/03_assets`, `modules/04_listing` |
| 24-31 | 采集、编辑图片和批量上架 | `markets/us-y1-pod/pod_listing_workflow.md` |
| 32-39 | AI 出图、标题模板和常见失败 | `modules/03_assets`, `core/04_exception_taxonomy.md` |
| 40-51 | 第三方发布、运营账号、核价、活动和流量 | `modules/04_listing`, `modules/07_growth` |
| 52-65 | 自动复色、下架归档、广告监控 | `automations/` |

## 质量说明

- 两份 PDF 都以后台截图为主，许多页面没有可用文字层。
- 本重构对全部页面进行了 OCR，并抽查关键页面版式。
- OCR 仅用于定位流程；涉及数字、地址和产品参数时，以原图和后台当前状态为准。
- 任何无法稳定确认的规则都标记为 `verify_before_use`，不作为 Agent 事实。
