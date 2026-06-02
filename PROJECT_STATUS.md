# 项目状态总结 / Project Status

## 1. 项目概览

本项目是一个面向汽车商业化广告销售场景的本地 AI 数据分析 Demo，名称为：

```text
XiaoShuTong AI Copilot / 销数通 AI Copilot
```

目标是让销售通过自然语言会话完成：

- 数据问数
- 客户经营分析
- 投放效果诊断
- 归因分析
- 销售话术建议
- 类 BI 看板式结果查看

当前项目目录：

```text
/Users/bytedance/sale_mobile_ai
```

远程 GitHub 仓库：

```text
git@github.com:chillyolk/sales_ai_copilot.git
```

## 2. 当前技术栈

当前版本采用轻量本地 Demo 架构：

| 层级 | 技术 |
|---|---|
| 前端 | 原生 HTML / CSS / JavaScript |
| 后端 | Python 3 标准库 `http.server` |
| 查询引擎 | SQLite in-memory |
| 数据源 | CSV 宽表 |
| AI 模型 | MiniMax Chat Completions API |
| 密钥管理 | macOS Keychain 或临时环境变量 |
| 版本管理 | Git + GitHub |

整体链路：

```text
浏览器前端
  -> /api/chat
Python 本地后端
  -> 意图识别与技能路由
     -> general_chat 普通销售对话
     -> sql_query 数据查询
     -> attribution_analysis 归因分析
  -> SQLite 查询 CSV 数据（按需）
  -> MiniMax 生成话术/总结/诊断报告
  -> 结构化 blocks 返回前端 BI 化展示
```

## 3. 核心文件

| 文件 | 说明 |
|---|---|
| `server.py` | Python 本地后端，负责 CSV 加载、MiniMax 调用、意图路由、技能执行、SQL 查询和结构化响应 |
| `index.html` | 前端会话页面，支持 PC 和移动端，渲染 AI 对话和 BI blocks |
| `README.md` | 中英文项目说明，包含架构、启动方式、API、安全说明等 |
| `PRD.md` | 产品需求文档，描述销数通 AI Copilot 的能力和验收标准 |
| `ads_auto_commercial_mock_20260101_20260531.csv` | 当前唯一数据源，启动时加载到 SQLite 内存表 |
| `start_app.sh` | 启动脚本 |
| `stop_app.sh` | 停止脚本 |
| `save_minimax_key.sh` | 将 MiniMax API Key 保存到 macOS Keychain 的脚本 |
| `.env.local.example` | 环境变量示例，不包含真实 Key |
| `.gitignore` | 忽略 `.env.local`、日志、pid、pyc 等本地文件 |

## 4. 当前已实现能力

### 4.1 普通销售对话

用户可以问：

```text
我想拜访一个客户，告诉我几个拜访客户比较有用的话术
```

系统会走：

```text
general_chat
```

特点：

- 不生成 SQL
- 不查询数据
- 直接给销售话术、沟通建议、追问建议

### 4.2 常规自然语言问数

用户可以问：

```text
哪些客户逾期应收最高？
```

系统会走：

```text
sql_query
```

特点：

- MiniMax 生成 SQL
- 后端安全执行 SQL
- 返回分析结论、结果表格、SQL 明细和推荐追问

### 4.3 归因分析

用户可以问：

```text
我的客户中本月环比上月消耗下降20%的客户出现哪些问题，给我做归因分析
```

系统会走：

```text
attribution_analysis
```

当前支持：

- 自动识别最新月份和上月
- 找出本月较上月消耗下降超过 20% 的客户
- 拆解：曝光、点击、线索、有效线索、订单、GMV、CPL、ROI
- 生成归因诊断报告
- 返回 KPI 卡、标签、发现、图表、明细表、行动建议和推荐追问

### 4.4 前端 BI Blocks 展示

前端目前支持以下结构化 blocks：

- `summary`：结论卡片
- `kpi_cards`：核心指标卡片
- `tags`：标签
- `insights`：主要发现
- `chart`：简单柱状图
- `table`：明细表格
- `actions`：行动建议
- `followups`：推荐追问

### 4.5 多会话与移动端体验

当前前端支持：

- 右侧顶部标题为“销数通”，标题栏更紧凑
- 左侧品牌为“销数通 AI Copilot”
- 输入框左侧支持手动技能选择
- 顶部支持 icon 形式的新建会话和清空当前会话
- 左侧栏支持会话列表，可切换当前和历史会话
- 会话记录保存在浏览器 `localStorage`
- 移动端默认收起左侧栏，可通过标题栏左侧 icon 从屏幕左侧滑出
- 移动端抽屉中集中展示推荐问题和会话列表

### 4.6 安全能力

当前安全设计：

- API Key 不暴露给前端
- 推荐将 Key 存入 macOS Keychain
- `.env.local` 被 `.gitignore` 忽略
- SQL 只允许 `SELECT`
- 禁止 `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `CREATE` 等语句
- 禁止多语句执行
- SQL 必须包含目标表 `ads_auto_commercial_daily_wide`
- 自动追加 `LIMIT`

## 5. 数据源状态

当前数据源文件：

```text
ads_auto_commercial_mock_20260101_20260531.csv
```

启动时加载为 SQLite 内存表：

```text
ads_auto_commercial_daily_wide
```

数据规模：

- 记录数：约 30,000 行
- 字段数：81
- 时间范围：2026-01-01 至 2026-05-31

覆盖场景：

- 客户资金账户
- 销售组织
- 区域城市
- 汽车品牌/车系
- 广告产品
- 充值消耗
- 收入合同
- 应收回款
- 曝光点击
- 线索转化
- 到店试驾
- 订单成交
- GMV / ROI / CPL

## 6. 启动方式

### 6.1 首次保存 MiniMax API Key

推荐使用 macOS Keychain，不把 Key 写入项目文件：

```bash
./save_minimax_key.sh
```

输入 MiniMax API Key 后，之后可以直接启动。

### 6.2 启动应用

```bash
./start_app.sh
```

访问：

```text
http://127.0.0.1:8000
```

### 6.3 停止应用

```bash
./stop_app.sh
```

### 6.4 临时环境变量启动

如果不使用 Keychain，也可以临时启动：

```bash
MINIMAX_API_KEY="your_api_key" ./start_app.sh
```

不要将真实 Key 写入 README、代码、PRD 或提交到 GitHub。

## 7. Git 状态与远程仓库

远程仓库：

```text
git@github.com:chillyolk/sales_ai_copilot.git
```

当前主要提交：

```text
8f834a5 Initial sales AI copilot demo
fb99f0c Add bilingual project README
1cd9634 Add intent routing and BI-style analysis blocks
```

后续常用命令：

```bash
git status
git add <文件>
git commit -m "提交说明"
git push
```

推送时如果 SSH 使用异常，之前成功使用过的方式是显式指定 SSH key：

```bash
GIT_SSH_COMMAND='ssh -i /Users/bytedance/.ssh/id_ed25519 -o UserKnownHostsFile=/Users/bytedance/.ssh/known_hosts -o StrictHostKeyChecking=yes' git push
```

## 8. 当前未提交/不应提交的本地文件

以下文件是本地运行状态或敏感配置，不应提交：

```text
.env.local
server.log
server.pid
```

当前 `.gitignore` 已忽略这些文件。

另外，计划文件的正式位置是：

```text
/Users/bytedance/.genius/plans/jaunty-singing-giraffe.md
```

如果项目根目录出现 `jaunty-singing-giraffe.md`，它只是计划副本，通常不需要提交。

## 9. 最稳妥的上下文恢复方式

如果之后退出 Genius Code，再次进入时可以使用：

```bash
cd /Users/bytedance/sale_mobile_ai
genius -c
```

但需要注意：

- `genius -c` 通常可以继续最近会话上下文
- 不保证完整恢复所有历史聊天原文
- 很长的工具输出、早期讨论和大段 diff 可能被压缩或丢失

因此，最稳妥的恢复方式是基于项目文件和 Git 状态重新建立上下文。

如果下次回来后上下文不完整，可以直接告诉 Genius：

```text
读取 README.md、PRD.md、PROJECT_STATUS.md、git log 和当前代码，帮我恢复项目上下文
```

建议优先读取：

```text
README.md
PRD.md
PROJECT_STATUS.md
server.py
index.html
git log --oneline -5
git status --short --ignored
```

因为当前项目关键内容都已经落在文件和 Git 里，所以即使历史会话没有完整恢复，也可以通过这些文件继续开发。

## 10. 后续推荐迭代方向

### 10.1 短期

- 优化意图识别准确率
- 增加更多销售技能：客户简报、风险扫描、机会推荐、拜访前报告
- 优化归因分析，支持产品结构、区域结构、销售负责人维度拆解
- 优化前端 BI 样式和移动端体验

### 10.2 中期

- 将 `server.py` 拆分为更清晰的模块
- 引入 FastAPI 管理接口和 schema
- 将 CSV/SQLite 升级为 DuckDB 或 PostgreSQL
- 增加会话历史和报告持久化

### 10.3 长期

- 前端升级为 React / Vue / Next.js
- 增加用户登录和销售组织权限
- 接入 CRM、BI、广告投放平台
- 支持自动报告导出和任务推送
