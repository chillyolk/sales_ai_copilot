# sales_weekly_report / 销售周报 Skill

## 目标

基于汽车商业化广告销售宽表，自动生成销售经营周报 BI 看板，并支持下载为 PNG 图片。

## MVP 范围

- 支持全量、销售姓名、销售部门三类范围。
- 默认生成上周周报。
- 周定义为周一到周日。
- 使用固定 SQL 模板，不让模型自由生成周报 SQL。
- Python 负责指标计算，MiniMax 负责摘要和行动建议。
- 输出标准 blocks，并附带 report 元信息用于前端下载图片。

## 核心指标

- 消耗：`sum(cost_amount)`
- 确认收入：`sum(confirmed_revenue_amount)`
- 回款：`sum(received_amount)`
- 合同金额：`sum(contract_amount)`
- 有效线索：`sum(valid_lead_cnt)`
- 订单：`sum(order_cnt)`
- GMV：`sum(gmv_amount)`
- ROI：`sum(gmv_amount) / sum(cost_amount)`
- CPL：`sum(cost_amount) / sum(valid_lead_cnt)`

## 输出模块

1. 周报摘要
2. KPI 卡片
3. 近 4 周趋势
4. 客户贡献 TopN
5. 产品表现 TopN
6. 风险客户
7. 机会客户
8. 本周洞察
9. 下周行动建议

## 图片导出

MVP 推荐前端使用本地 `html2canvas` 将周报 DOM 转为 PNG。
