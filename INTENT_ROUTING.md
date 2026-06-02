# 会话意图识别与技能路由说明

## 1. 总体流程

当前会话意图识别和技能路由主要实现在：

```text
server.py
```

核心入口函数：

```python
handle_chat(payload)
```

整体处理流程：

```text
前端 /api/chat
  -> handle_chat()
  -> detect_intent()
  -> 根据 skill 路由
     -> general_chat_skill()
     -> sql_query_skill()
     -> attribution_analysis_skill()
  -> 返回 answer + blocks + debug + sql/rows 等
```

也就是说，每次用户输入后，系统会先判断用户意图，再选择对应技能执行。

---

## 2. 当前支持的 Intent

当前 `detect_intent()` 会返回 3 类主要意图。

### 2.1 general_chat

普通销售对话，不查数据。

适合场景：

- 拜访话术
- 客户沟通建议
- 客户异议处理
- 开场白
- 邀约话术
- 谈判建议
- 销售表达优化

示例问题：

```text
我想拜访一个客户，告诉我几个拜访客户比较有用的话术
```

返回示例：

```json
{
  "intent": "general_chat",
  "skill": "general_chat",
  "requires_data": false,
  "confidence": 0.85
}
```

---

### 2.2 data_query

常规数据查询。

适合场景：

- 排名
- TopN
- 客户筛选
- 余额查询
- 逾期查询
- ROI / CPL / 线索 / 订单查询
- 区域、品牌、销售维度分析

示例问题：

```text
哪些客户逾期应收最高？
```

返回示例：

```json
{
  "intent": "data_query",
  "skill": "sql_query",
  "requires_data": true,
  "confidence": 0.8
}
```

---

### 2.3 attribution_analysis

归因诊断类问题。

适合场景：

- 环比下降
- 同比下降
- 为什么变差
- 原因分析
- 诊断
- 问题拆解
- 消耗、线索、订单、ROI、CPL 的变化归因

示例问题：

```text
我的客户中本月环比上月消耗下降20%的客户出现哪些问题，给我做归因分析
```

返回示例：

```json
{
  "intent": "attribution_analysis",
  "skill": "attribution_analysis",
  "requires_data": true,
  "confidence": 0.9
}
```

---

## 3. 当前支持的 Skill

当前系统有 3 个主要技能。

---

## 3.1 技能一：general_chat

### 作用

普通销售对话，不查数据库。

### 入口函数

```python
general_chat_skill(question, history)
```

### 使用场景

例如用户问：

```text
我想拜访一个客户，告诉我几个拜访客户比较有用的话术
```

系统不会生成 SQL，也不会查询 SQLite，而是直接调用 MiniMax，让它作为“汽车广告销售教练”生成话术建议。

### Prompt 角色

当前 prompt 大意是：

```text
你是汽车广告销售教练，负责帮助销售准备客户拜访、沟通话术、异议处理和行动建议。
如果用户没有要求查具体数据，不要编造数据；直接给可落地的话术和沟通框架。
输出要简洁，适合销售直接复制使用。
```

### 返回结构

```json
{
  "intent": "general_chat",
  "skill": "general_chat",
  "answer": "...",
  "blocks": [
    {
      "type": "summary",
      "title": "销售沟通建议",
      "content": "..."
    },
    {
      "type": "tags",
      "items": ["不需要查数", "销售话术", "客户沟通"]
    },
    {
      "type": "followups",
      "items": [
        "帮我生成一版更强势的商务话术",
        "如果客户说预算不够，我该怎么回应？",
        "帮我结合客户投放数据做拜访简报"
      ]
    }
  ]
}
```

### 特点

- 不查数据
- 不生成 SQL
- 返回销售话术
- 前端以卡片形式展示

---

## 3.2 技能二：sql_query

### 作用

自然语言问数。

### 入口函数

```python
sql_query_skill(question, history)
```

### 使用场景

例如：

```text
哪些客户逾期应收最高？
```

或者：

```text
本月客户消耗 Top10 是谁？
```

### 处理流程

```text
用户问题
  -> generate_sql()
  -> execute_sql()
  -> summarize()
  -> 返回 summary/table/followups blocks
```

### 第一步：生成 SQL

调用：

```python
generate_sql(question, history)
```

MiniMax 会基于 `schema_text()` 生成 JSON：

```json
{
  "sql": "SELECT ...",
  "reason": "查询逻辑说明"
}
```

### 第二步：SQL 安全检查并执行

调用：

```python
execute_sql(sql)
```

执行前会经过：

```python
is_safe_select(sql)
```

安全规则：

- 必须以 `SELECT` 开头
- 禁止 `INSERT`
- 禁止 `UPDATE`
- 禁止 `DELETE`
- 禁止 `DROP`
- 禁止 `ALTER`
- 禁止 `CREATE`
- 禁止多语句
- 必须包含目标表名 `ads_auto_commercial_daily_wide`

然后自动补：

```sql
LIMIT
```

### 第三步：总结结果

调用：

```python
summarize(question, sql, reason, rows)
```

MiniMax 会根据查询结果生成销售能看懂的结论和建议。

### 返回结构

```json
{
  "intent": "data_query",
  "skill": "sql_query",
  "answer": "...",
  "blocks": [
    {
      "type": "summary",
      "title": "查询结论",
      "content": "..."
    },
    {
      "type": "table",
      "title": "查询结果",
      "columns": ["..."],
      "rows": []
    },
    {
      "type": "followups",
      "items": ["..."]
    }
  ],
  "debug": {
    "sql": "...",
    "reason": "..."
  },
  "sql": "...",
  "reason": "...",
  "columns": ["..."],
  "rows": []
}
```

### 特点

- 适合常规问数
- 会生成 SQL
- 会查询 SQLite
- 会返回 SQL 明细
- 前端展示结论 + 表格 + 追问

---

## 3.3 技能三：attribution_analysis

### 作用

归因诊断分析。

### 入口函数

```python
attribution_analysis_skill(question, history)
```

### 使用场景

例如：

```text
我的客户中本月环比上月消耗下降20%的客户出现哪些问题，给我做归因分析
```

### 当前支持范围

当前是一个最小可用版本，固定支持：

```text
本月 vs 上月
消耗下降 >= 20%
客户维度
```

也就是它会自动找：

```text
当前数据里最新月份
当前数据里上一个月份
```

然后筛选：

```text
本月消耗较上月下降超过 20% 的客户
```

当前数据中通常是：

```text
2026-05 vs 2026-04
```

### 第一步：识别最新两个月

调用：

```python
get_latest_months()
```

逻辑：

```sql
SELECT DISTINCT stat_month
FROM ads_auto_commercial_daily_wide
ORDER BY stat_month DESC
LIMIT 2
```

返回：

```text
current_month, previous_month
```

### 第二步：筛选消耗下降客户

使用固定 SQL，按客户维度聚合：

- `customer_account_id`
- `customer_account_name`
- `sales_name`
- `customer_level`
- `stat_month`

计算：

- 上月消耗
- 本月消耗
- 消耗变化金额
- 消耗变化比例

筛选条件：

```sql
prev.cost_amount > 0
AND (cur.cost_amount - prev.cost_amount) / prev.cost_amount <= -0.2
```

含义：

```text
本月较上月下降 20% 或更多
```

### 第三步：拆解归因指标

当前会同时查询和计算以下指标。

#### 流量层

- `impression_cnt`
- `click_cnt`
- 曝光变化
- 点击变化

#### 线索层

- `lead_cnt`
- `valid_lead_cnt`
- 线索变化
- 有效线索变化
- CPL 变化

#### 转化层

- `order_cnt`
- 订单变化

#### 效果层

- `gmv_amount`
- ROI 变化

#### 费用层

- `cost_amount`
- CPL
- ROI

### 第四步：规则生成主要原因

当前有一个本地函数：

```python
infer_causes(row)
```

它会基于指标变化生成原因标签。

规则大致是：如果某指标变化小于等于 `-20%`，则认为它是主要问题。

当前判断项：

```python
[
  ("曝光下滑", impression_change),
  ("点击下滑", click_change),
  ("线索下滑", lead_change),
  ("订单下滑", order_change),
  ("GMV 下滑", gmv_change),
]
```

如果：

```python
cpl_change >= 20%
```

则增加：

```text
CPL 上升
```

如果：

```python
roi_change <= -20%
```

则增加：

```text
ROI 下降
```

最后每个客户最多取前 3 个原因。

### 第五步：生成证据摘要

程序会先整理结构化证据：

```json
{
  "current_month": "2026-05",
  "previous_month": "2026-04",
  "affected_count": 8,
  "total_decline": 153300.51,
  "avg_decline": -0.683,
  "top_customers": [],
  "insights": []
}
```

然后把这些证据交给 MiniMax，让它生成诊断报告。

重点原则：

```text
模型只基于程序准备的数据证据写结论
```

这样比让模型直接自由分析更安全。

### 返回结构

```json
{
  "intent": "attribution_analysis",
  "skill": "attribution_analysis",
  "answer": "...",
  "blocks": [
    {
      "type": "summary",
      "title": "归因诊断结论",
      "content": "..."
    },
    {
      "type": "kpi_cards",
      "items": [
        { "label": "分析月份", "value": "2026-04 → 2026-05" },
        { "label": "下降客户数", "value": 8 },
        { "label": "消耗减少", "value": "153,301" },
        { "label": "平均降幅", "value": "-68.3%" }
      ]
    },
    {
      "type": "tags",
      "items": ["消耗下降≥20%", "月环比", "归因诊断", "需优先跟进"]
    },
    {
      "type": "insights",
      "items": []
    },
    {
      "type": "chart",
      "title": "消耗下降 Top 客户",
      "chartType": "bar",
      "data": {
        "items": []
      }
    },
    {
      "type": "table",
      "title": "客户归因明细",
      "columns": [],
      "rows": []
    },
    {
      "type": "actions",
      "items": []
    },
    {
      "type": "followups",
      "items": []
    }
  ],
  "debug": {
    "sql": "...",
    "reason": "筛选本月较上月消耗下降超过 20% 的客户，并拆解流量、线索、转化、效果指标变化。"
  }
}
```

### 特点

- 不是单纯 SQL 查询
- 是一个多步骤诊断技能
- 程序先算证据
- 模型再写诊断报告
- 前端用 BI 卡片展示

---

## 4. 手动技能选择

除了自动意图识别，前端输入框左侧现在提供技能选择器。

### 4.1 可选项

技能选择器展示 4 个选项：

| 展示名称 | 传给后端的 skill | 行为 |
|---|---|---|
| 自动 | `auto` | 根据用户输入内容调用 `detect_intent()` 自动路由 |
| 普通对话 | `general_chat` | 不自动路由，直接调用普通销售对话技能 |
| 数据查询 | `sql_query` | 不自动路由，直接调用数据查询技能 |
| 归因分析 | `attribution_analysis` | 不自动路由，直接调用归因分析技能 |

### 4.2 前端请求

前端 `sendMessage()` 会在 `/api/chat` 请求中传入当前选择：

```json
{
  "message": "用户输入内容",
  "history": [],
  "skill": "auto"
}
```

当用户选择具体技能时，例如“数据查询”：

```json
{
  "message": "本月消耗 Top10 是谁？",
  "history": [],
  "skill": "sql_query"
}
```

### 4.3 后端行为

后端 `handle_chat()` 的规则：

1. `skill` 为空或 `auto`：执行自动意图识别。
2. `skill` 为 `general_chat` / `sql_query` / `attribution_analysis`：跳过自动意图识别，直接调用对应技能。
3. `skill` 非法：返回错误，不执行未知技能。

手动选择时，后端会返回：

```json
{
  "intent": "manual_select",
  "skill": "sql_query",
  "route": {
    "forced": true
  }
}
```

这样前端执行明细中可以明确看到当前是手动选择的技能。

---

## 5. 当前自动路由规则详情

当前自动路由函数是：

```python
detect_intent(question)
```

内部定义了三组关键词。

---

### 4.1 归因诊断关键词

```python
diagnosis_keywords = [
    "归因",
    "诊断",
    "原因",
    "为什么",
    "环比",
    "同比",
    "下降",
    "下滑",
    "波动",
    "拆解"
]
```

仅命中这些还不够，还需要问题中同时包含下面任一业务指标词：

```python
["客户", "消耗", "线索", "订单", "roi", "cpl"]
```

完整判断逻辑：

```python
if any(k in question for k in diagnosis_keywords) \
   and any(k in question for k in ["客户", "消耗", "线索", "订单", "roi", "cpl"]):
    return attribution_analysis
```

所以这类问题会走归因分析：

```text
我的客户中本月环比上月消耗下降20%的客户出现哪些问题
```

```text
为什么客户线索下滑了
```

```text
帮我诊断 ROI 下降原因
```

```text
订单环比下降的客户有哪些问题
```

---

### 4.2 普通销售对话关键词

```python
chat_keywords = [
    "话术",
    "怎么说",
    "怎么聊",
    "拜访",
    "沟通",
    "客户异议",
    "开场白",
    "邀约",
    "谈判",
    "说服"
]
```

判断逻辑：

```python
if any(k in question for k in chat_keywords):
    return general_chat
```

所以这类问题会走普通销售对话：

```text
我想拜访一个客户，告诉我几个话术
```

```text
客户说预算不够，我该怎么说？
```

```text
帮我写一个邀约客户复盘的开场白
```

```text
客户对投放效果有异议，我怎么沟通？
```

---

### 4.3 常规问数关键词

```python
query_keywords = [
    "哪些",
    "top",
    "排名",
    "多少",
    "查询",
    "筛选",
    "余额",
    "逾期",
    "回款",
    "消耗",
    "roi",
    "cpl",
    "线索",
    "订单"
]
```

判断逻辑：

```python
if any(k in q for k in query_keywords):
    return data_query
```

所以这类问题会走 SQL 查询：

```text
哪些客户逾期应收最高？
```

```text
本月客户消耗 Top10 是谁？
```

```text
哪些客户余额快没了？
```

```text
线索通和信息流广告哪个效果更好？
```

```text
哪些客户适合追加预算？
```

---

### 4.4 默认兜底

如果以上都没命中：

```python
return general_chat
```

也就是说，默认会走普通对话。

例如：

```text
你好
```

```text
帮我想想今天怎么安排客户跟进
```

会走：

```text
general_chat
```

这样设计的原因是：对于不明确的问题，强制生成 SQL 更容易出错；默认走普通对话更安全。

---

## 5. 路由优先级

当前优先级是：

```text
1. attribution_analysis
2. general_chat
3. data_query
4. general_chat fallback
```

### 第一优先级：归因分析

如果问题里有：

```text
归因 / 诊断 / 原因 / 为什么 / 环比 / 同比 / 下降 / 下滑
```

并且同时涉及：

```text
客户 / 消耗 / 线索 / 订单 / ROI / CPL
```

就优先走归因分析。

例如：

```text
客户消耗下降的原因是什么？
```

即使里面有“客户”和“消耗”，也不会走普通 SQL 查询，而是走归因分析。

---

### 第二优先级：普通销售对话

如果没有命中归因分析，但命中了：

```text
话术 / 拜访 / 怎么说 / 沟通
```

就走普通对话。

例如：

```text
客户说 ROI 不好，我该怎么说？
```

这里有 `ROI`，也有 `怎么说`。

因为没有命中归因条件中的“原因/诊断/下降”等，所以会走：

```text
general_chat
```

---

### 第三优先级：常规问数

如果没有命中归因，也没有命中普通销售沟通，但命中了问数关键词，就走：

```text
sql_query
```

例如：

```text
ROI 最高的客户是谁？
```

---

### 第四优先级：兜底普通对话

都没命中时，走：

```text
general_chat
```

---

## 6. 每个技能是否查数据

| 技能 | 是否查数据 | 是否生成 SQL | 是否调用 MiniMax | 主要用途 |
|---|---:|---:|---:|---|
| `general_chat` | 否 | 否 | 是 | 话术、沟通建议、销售教练 |
| `sql_query` | 是 | 是 | 是 | 普通问数、排行、筛选、对比 |
| `attribution_analysis` | 是 | 固定 SQL | 是 | 环比下降、问题诊断、归因报告 |

说明：

- `general_chat` 只调用模型，不查 SQLite。
- `sql_query` 调模型生成 SQL，再查 SQLite，再调模型总结。
- `attribution_analysis` 使用后端固定 SQL 查询和计算，再调模型写报告。

---

## 7. 前端如何展示不同技能结果

不管哪个技能，后端都会返回统一结构：

```json
{
  "intent": "...",
  "skill": "...",
  "answer": "...",
  "blocks": [],
  "debug": {},
  "sql": "...",
  "reason": "...",
  "columns": [],
  "rows": []
}
```

前端逻辑是：

```js
if (meta.blocks 存在) {
  renderBlocks(meta.blocks)
} else {
  markdownLite(answer)
}
```

目前支持这些 block：

| block type | 前端展示 |
|---|---|
| `summary` | 结论卡片 |
| `kpi_cards` | KPI 指标卡 |
| `tags` | 标签 |
| `insights` | 主要发现 |
| `chart` | 简单柱状图 |
| `table` | HTML 表格 |
| `actions` | 行动建议列表 |
| `followups` | 推荐追问按钮 |

同时，前端折叠区会展示：

- intent
- skill
- SQL
- 查询逻辑
- rows 明细

---

## 8. 当前设计优点

### 8.1 不再所有问题都强制转 SQL

销售问话术时不会再走数据库。

### 8.2 SQL 问数能力保留

原有问数能力没有丢。

### 8.3 复杂分析开始技能化

归因分析不再只是“让模型自由发挥”，而是：

```text
程序先找证据
模型再写报告
```

### 8.4 前端展示更像 BI

归因分析结果会以：

- KPI
- 标签
- 图表
- 表格
- 行动建议

来展示。

### 8.5 保留旧字段

`sql/reason/columns/rows` 还保留，方便调试和兼容。

---

## 9. 当前不足

### 9.1 意图识别还是规则型

当前还不是模型分类器，主要靠关键词。

可能误判，例如：

```text
帮我想想客户消耗预算怎么沟通
```

有“沟通”，可能走 `general_chat`；但如果用户其实想查数据，就需要进一步追问或优化规则。

### 9.2 归因分析目前是固定口径

现在固定是：

```text
最新月 vs 上月
消耗下降 >= 20%
客户维度
```

还不支持灵活解析：

```text
下降 10%
近 7 天 vs 前 7 天
按品牌归因
按销售归因
按产品归因
```

### 9.3 技能还比较少

当前只有：

```text
general_chat
sql_query
attribution_analysis
```

后续可以加：

```text
customer_brief
risk_scan
opportunity_recommendation
visit_report
sales_action_list
```

### 9.4 前端图表还是轻量实现

目前图表是 CSS 简单柱状图，不是 ECharts/AntV。

---

## 10. 后续推荐优化

### 10.1 意图识别升级为混合模式

当前是规则：

```text
关键词 -> intent
```

后续可以变成：

```text
规则优先 -> MiniMax 分类兜底 -> 必要时向用户澄清
```

MiniMax 分类输出：

```json
{
  "intent": "data_query",
  "skill": "sql_query",
  "requires_data": true,
  "confidence": 0.82,
  "reason": "用户询问客户消耗排名，需要查询数据"
}
```

### 10.2 归因技能参数化

让归因分析支持：

- 阈值：10%、20%、30%
- 时间：本周/上周、本月/上月、指定月份
- 指标：消耗、线索、订单、GMV、ROI、CPL
- 维度：客户、品牌、区域、销售、广告产品

### 10.3 增加更多技能

优先建议加：

1. `customer_brief`：客户拜访前简报
2. `risk_scan`：风险客户扫描
3. `opportunity_recommendation`：追加预算机会推荐
4. `sales_action_list`：今日销售跟进清单

### 10.4 前端更进一步 BI 化

后续可以升级：

- ECharts 图表
- 筛选器
- 卡片 drill-down
- 客户详情弹窗
- 报告导出
- 一键复制话术/建议动作

---

## 11. sales_weekly_report 标准 Skill

当前新增标准 Skill 文件包：

```text
skills/sales_weekly_report/
```

后端技能名：

```text
sales_weekly_report
```

前端展示名：

```text
销售周报
```

### 11.1 触发方式

#### 手动触发

在输入框左侧技能选择器中选择：

```text
销售周报
```

然后输入：

```text
帮我生成上周销售周报
```

#### 自动路由

自动路由会识别以下关键词：

- 周报
- 周总结
- 本周复盘
- 上周复盘
- 经营周报
- 销售周报
- 生成看板

命中后路由到：

```json
{
  "intent": "sales_weekly_report",
  "skill": "sales_weekly_report",
  "requires_data": true
}
```

### 11.2 能力范围

当前 MVP 支持：

- 默认上周周报
- 周一到周日口径
- 全量销售周报
- 根据问题中的销售姓名或销售部门做范围过滤
- 固定 SQL 模板查询
- Python 计算指标
- MiniMax 生成摘要和行动建议
- BI blocks 展示
- PNG 图片下载

### 11.3 输出结构

该 Skill 会返回：

```json
{
  "intent": "sales_weekly_report",
  "skill": "sales_weekly_report",
  "report": {
    "type": "weekly_report",
    "downloadable": true,
    "filename": "销售周报_2026-05-19_2026-05-25.png"
  },
  "blocks": []
}
```

前端检测到 `report.downloadable = true` 后，会显示“下载图片”按钮。

### 11.4 说明

周报 Skill 不依赖模型生成 SQL，而是使用 `skills/sales_weekly_report/queries/` 中的固定 SQL 模板。模型只负责基于数据证据生成摘要和下周行动建议。
