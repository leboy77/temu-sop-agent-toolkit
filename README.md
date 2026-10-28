# Temu SOP and Agent Toolkit

一套面向欧洲 Y2 与美国 Y1 POD 的 Temu 运营标准、AI 辅助模块和自动化工具接口。

本项目的目标不是把后台点击步骤直接包装成 Agent，而是把运营工作拆成四层：

1. **通用流程**：所有市场共用的商品生命周期、质量门和异常处理。
2. **市场 Playbook**：欧洲 Y2 与美国 Y1 POD 的仓库、时效、税务、合规和工具差异。
3. **能力模块**：选品、核价、素材、上架、合规、履约、增长和售后。
4. **自动化工具**：计算脚本、浏览器扩展和 ERP 适配说明。

## 核心原则

- 数据只有一份事实来源，商品参数、价格和合规信息不得在多个文档中互相覆盖。
- 确定性计算交给脚本，Agent 只负责解释、补全文案和提出建议。
- 核价、合规、批量提交和资金相关动作必须经过人工审批。
- 提交结果未知时先查询，禁止盲目重试，避免重复上架或重复推单。
- 平台规则必须记录来源、负责人和复核日期，不能把经验值永久硬编码。
- 原始内部资料、账号、地址、联系方式、Token、真实 SKU 和客户信息不得进入公开仓库。

## 业务主线

```text
市场配置 + 商品资料 + 核价表
          |
          v
选品判断 -> 核价/SKU -> 素材生产 -> 合规审查
                                      |
                                      v
                                  上架发布
                                      |
                                      v
                              订单 / ERP / 面单
                                      |
                                      v
                         活动/流量/广告 -> 售后/评论
                                      |
                                      v
                                复盘、修补、归档
```

## 目录

```text
core/          通用流程、数据契约、质量门和异常分类
markets/       欧洲 Y2 与美国 Y1 POD 的市场配置和操作说明
modules/       八个可复用业务能力
schemas/       机器可读的数据结构
templates/     商品、核价、合规和日报模板
scripts/       确定性计算与检查
examples/      脱敏的端到端示例
automations/   现有浏览器扩展和 RPA 的接入边界
docs/          来源映射和迁移计划
archive/       私有原件说明，不存放原始 PDF
```

## 快速开始

1. 复制 `templates/product_brief.yaml`，填写一个真实但已脱敏的商品。
2. 复制 `templates/price_sheet.csv`，补齐成本、重量、退货率和费用。
3. 运行 `python scripts/calc_price.py templates/price_sheet.csv`。
4. 按目标市场打开 `markets/eu-y2/README.md` 或 `markets/us-y1-pod/README.md`。
5. 从 `modules/00_orchestrator/README.md` 开始推进状态。
6. 每次异常写入 `templates/exception_log.csv`，不要只留在聊天或截图中。

## 与已有工具的关系

现有核价、自动复色、下架归档和广告监控工具属于本项目的执行层。它们应读取标准化输入、输出运行记录，不应自行决定选品、定价或合规结论。

## 当前状态

这是基于两份内部培训资料的 v0 重构草案。市场阈值和平台规则在正式使用前必须由业务负责人复核。

参考架构：[AI-Cross-Border-Ecommerce-Agent-Toolkit](https://github.com/heqiangdiao-wq/AI-Cross-Border-Ecommerce-Agent-Toolkit)。
