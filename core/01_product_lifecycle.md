# 01 - Product Lifecycle

## 状态机

```text
DRAFT
  -> PRICED
  -> ASSETS_READY
  -> COMPLIANCE_READY
  -> PUBLISH_READY
  -> PUBLISHED
  -> LIVE
  -> OPTIMIZING
  -> ARCHIVED
```

任意状态可以进入：

- `BLOCKED`：缺少输入或未通过质量门。
- `REVIEW_REQUIRED`：结果不确定或需要人工决策。
- `FAILED`：确认失败，且重试策略已执行完毕。

## 状态定义

| 状态 | 进入条件 | 必要产物 |
| --- | --- | --- |
| DRAFT | 已创建商品卡 | 商品基础信息、目标市场、来源 |
| PRICED | 核价通过 | 成本表、盈亏价、目标售价、SKU 结构 |
| ASSETS_READY | 图片和文案完整 | 图片清单、标题、卖点、参数、授权记录 |
| COMPLIANCE_READY | 合规审查通过 | 税务、主体、标签、禁限售检查结果 |
| PUBLISH_READY | 上架字段校验通过 | SKC/SPU、类目、属性、库存、模板版本 |
| PUBLISHED | 平台返回明确成功 | 商品 ID、发布时间、发布结果 |
| LIVE | 平台列表中可检索且状态正确 | 列表截图或导出记录、首次校验时间 |
| OPTIMIZING | 已有可分析数据 | 活动、流量、广告、售后指标基线 |
| ARCHIVED | 停止运营或下架 | 原因、库存、素材归档和最终状态 |

## 阻塞规则

- `DRAFT -> PRICED`：缺少采购价、物流价、重量、退货率或费用时阻塞。
- `PRICED -> ASSETS_READY`：缺少实际商品图、图片授权或 SKU 与图片对应关系时阻塞。
- `ASSETS_READY -> COMPLIANCE_READY`：参数、标签或市场合规资料不完整时阻塞。
- `COMPLIANCE_READY -> PUBLISH_READY`：批量模板与当前商品版本不一致时阻塞。
- `PUBLISHED -> LIVE`：必须回列表或通过平台查询确认，不以点击成功代替发布成功。
- `LIVE -> OPTIMIZING`：至少存在有效时间窗和基线指标。

## 版本规则

- 商品卡每次实质变更递增 `revision`。
- 核价、素材、合规和上架分别记录所消费的商品卡版本。
- 上游商品卡变更后，下游状态回到最近一个受影响的质量门。
- 不允许用新文件覆盖旧版本；保留变更原因和审批人。
