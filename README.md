# XiaoShuTong AI Copilot / 销数通 AI Copilot

[中文](#中文说明) | [English](#english)

---

## 中文说明

### 项目简介

销数通 AI Copilot 是一个面向汽车商业化广告销售场景的本地 AI 数据分析 Demo。

用户可以在网页会话框中输入自然语言问题，例如：

- 哪些客户适合追加预算？
- 哪些客户消耗高但没有订单？
- 线索通和信息流广告哪个效果更好？
- 哪些客户余额快没了？
- 哪些客户逾期应收最高？

系统会先识别用户意图：普通销售沟通类问题直接由大模型生成话术和建议；数据查询类问题会调用 MiniMax 生成 SQL 并查询本地 CSV 数据源；归因诊断类问题会执行多步数据查询和指标拆解，再生成面向销售的诊断报告和行动建议。

### 核心能力

- 自然语言问数
- 普通销售对话与拜访话术建议
- 意图识别与技能路由
- 输入框左侧手动技能选择：自动 / 普通对话 / 数据查询 / 归因分析
- 本地多会话列表，支持新建、切换、清空当前会话
- 会话记录保存在浏览器 localStorage
- 移动端左侧抽屉，集中展示推荐问题和会话列表
- 销售经营数据分析
- 客户投放效果诊断
- 月环比消耗下降客户归因分析
- 追加预算机会识别
- 余额、逾期、低效投放等风险发现
- 类 BI 的 KPI 卡片、标签、图表、表格和行动建议展示
- SQL 查询明细展示
- PC 与移动端响应式页面
- 本地 CSV 数据源自动加载为 SQLite 查询表
- API Key 不暴露给前端

### 技术栈

本项目采用轻量本地 Demo 架构：

| 层级 | 技术 |
|---|---|
| 前端 | 原生 HTML / CSS / JavaScript |
| 后端 | Python 3 标准库 `http.server` |
| 查询引擎 | SQLite in-memory |
| 数据源 | CSV 宽表 |
| AI 模型 | MiniMax Chat Completions API |
| 密钥管理 | macOS Keychain 或临时环境变量 |

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

### 数据源

默认数据文件：

```text
ads_auto_commercial_mock_20260101_20260531.csv
```

启动时会加载为 SQLite 内存表：

```text
ads_auto_commercial_daily_wide
```

数据覆盖：

- 时间范围：2026-01-01 至 2026-05-31
- 字段数：81
- 记录数：约 30,000 行
- 场景：汽车商业化广告经营、客户充值消耗、线索转化、销售业绩、回款与逾期等

### 目录结构

```text
.
├── index.html                                  # 前端会话页面
├── server.py                                   # Python 本地后端服务
├── start_app.sh                                # 启动脚本
├── stop_app.sh                                 # 停止脚本
├── save_minimax_key.sh                         # 保存 MiniMax Key 到 macOS Keychain
├── .env.local.example                          # 环境变量示例，不包含真实 Key
├── .gitignore                                  # 忽略本地密钥和运行日志
├── PRD.md                                      # 产品需求文档
├── ads_auto_commercial_mock_20260101_20260531.csv
└── *.md                                        # 数据方案和 mock 数据说明文档
```

### 快速开始

#### 1. 保存 MiniMax API Key

推荐使用 macOS Keychain 保存密钥，避免将 Key 写入项目文件：

```bash
./save_minimax_key.sh
```

按提示输入 MiniMax API Key。

> 注意：不要将真实 Key 写入 README、代码或 `.env.local` 并提交到 GitHub。

#### 2. 启动应用

```bash
./start_app.sh
```

启动成功后访问：

```text
http://127.0.0.1:8000
```

#### 3. 停止应用

```bash
./stop_app.sh
```

### 临时环境变量启动

如果不想使用 Keychain，也可以临时传入 Key：

```bash
MINIMAX_API_KEY="your_api_key" ./start_app.sh
```

### 配置项

默认配置位于 `.env.local.example`：

```bash
MINIMAX_API_URL="https://api.minimaxi.com/v1/chat/completions"
MINIMAX_MODEL="MiniMax-M2"
```

如需自定义，可复制为 `.env.local` 并修改：

```bash
cp .env.local.example .env.local
```

`.env.local` 已被 `.gitignore` 忽略。

### API 接口

#### 健康检查

```http
GET /api/health
```

返回示例：

```json
{
  "ok": true,
  "table": "ads_auto_commercial_daily_wide",
  "columns": 81,
  "minimaxConfigured": true,
  "model": "MiniMax-M2"
}
```

#### 会话问数

```http
POST /api/chat
Content-Type: application/json

{
  "message": "哪些客户适合追加预算？",
  "history": []
}
```

返回内容包括：

- `answer`：AI 生成的销售分析结论
- `sql`：实际执行的 SQL
- `reason`：查询逻辑说明
- `columns`：查询结果字段
- `rows`：查询结果数据

### SQL 安全限制

后端对模型生成的 SQL 做了基础安全限制：

- 仅允许 `SELECT`
- 禁止 `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `CREATE` 等语句
- 禁止多语句执行
- 必须查询目标表 `ads_auto_commercial_daily_wide`
- 自动追加 `LIMIT`

### 安全注意事项

- 不要提交真实 API Key
- `.env.local`、`server.log`、`server.pid` 已被忽略
- 推荐使用 `save_minimax_key.sh` 将 Key 存入 macOS Keychain
- 如果 Key 曾经泄露，请立即在 MiniMax 控制台轮换

### 当前限制

当前版本是本地 Demo，不是生产级系统：

- 无用户登录与权限体系
- 无对话持久化
- SQLite 为内存态，服务重启会重新加载 CSV
- 未做多用户并发优化
- 未接入正式数据库或 BI 系统
- 前端未使用工程化框架

### 后续演进方向

- 前端升级为 React / Vue / Next.js
- 后端升级为 FastAPI / Node.js
- 数据层升级为 PostgreSQL / DuckDB / ClickHouse
- 引入指标语义层
- 加入销售组织权限与客户权限
- 接入 CRM、BI、广告投放平台
- 增加报告导出和任务推送能力

---

## English

### Overview

XiaoShuTong AI Copilot is a local AI-powered data analysis demo for automotive advertising sales teams.

Users can ask business questions in natural language, such as:

- Which customers are suitable for additional budget?
- Which customers spend a lot but generate no orders?
- Which performs better, Lead Ads or Feed Ads?
- Which customers are likely to run out of balance?
- Which customers have the highest overdue receivables?

The application first detects the user's intent. General sales communication questions are answered directly by the model. Data analysis questions are converted into SQL and queried against the local CSV dataset. Attribution diagnosis questions run multi-step metric comparisons before MiniMax generates a sales-oriented diagnostic report and action recommendations.

### Key Features

- Natural language data analysis
- General sales conversation and customer visit talking points
- Intent detection and skill routing
- Manual skill selector in the input box: Auto / General Chat / Data Query / Attribution Analysis
- Local multi-session list with create, switch, and clear-current-session support
- Session records persisted in browser localStorage
- Mobile sidebar drawer for recommended questions and session history
- Sales performance analysis
- Customer advertising performance diagnosis
- Month-over-month spend decline attribution analysis
- Budget expansion opportunity detection
- Balance, overdue receivable, and inefficient spending risk discovery
- BI-like KPI cards, tags, charts, tables, and action recommendations
- SQL query details display
- Responsive UI for desktop and mobile
- Local CSV automatically loaded into SQLite
- API key is kept on the backend side and never exposed to the frontend

### Tech Stack

This project uses a lightweight local demo architecture:

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML / CSS / JavaScript |
| Backend | Python 3 standard library `http.server` |
| Query Engine | In-memory SQLite |
| Data Source | CSV wide table |
| AI Model | MiniMax Chat Completions API |
| Secret Management | macOS Keychain or temporary environment variable |

Architecture:

```text
Browser frontend
  -> /api/chat
Local Python backend
  -> intent detection and skill routing
     -> general_chat
     -> sql_query
     -> attribution_analysis
  -> SQLite queries CSV data when needed
  -> MiniMax generates talking points, summaries, or diagnosis reports
  -> structured blocks rendered as BI-like cards in frontend
```

### Dataset

Default data file:

```text
ads_auto_commercial_mock_20260101_20260531.csv
```

It is loaded into an in-memory SQLite table on startup:

```text
ads_auto_commercial_daily_wide
```

Dataset profile:

- Date range: 2026-01-01 to 2026-05-31
- Columns: 81
- Rows: around 30,000
- Scenarios: automotive advertising operations, customer recharge and spending, lead conversion, sales performance, receivables and overdue analysis

### Project Structure

```text
.
├── index.html                                  # Frontend chat UI
├── server.py                                   # Local Python backend server
├── start_app.sh                                # Start script
├── stop_app.sh                                 # Stop script
├── save_minimax_key.sh                         # Save MiniMax key to macOS Keychain
├── .env.local.example                          # Environment variable example, no real key
├── .gitignore                                  # Ignore local secrets and runtime logs
├── PRD.md                                      # Product requirements document
├── ads_auto_commercial_mock_20260101_20260531.csv
└── *.md                                        # Dataset design and mock data documents
```

### Quick Start

#### 1. Save MiniMax API Key

Use macOS Keychain to store the API key without writing it into project files:

```bash
./save_minimax_key.sh
```

Enter your MiniMax API key when prompted.

> Do not commit real API keys to GitHub.

#### 2. Start the app

```bash
./start_app.sh
```

Then open:

```text
http://127.0.0.1:8000
```

#### 3. Stop the app

```bash
./stop_app.sh
```

### Start with temporary environment variable

If you do not want to use Keychain:

```bash
MINIMAX_API_KEY="your_api_key" ./start_app.sh
```

### Configuration

Default configuration is shown in `.env.local.example`:

```bash
MINIMAX_API_URL="https://api.minimaxi.com/v1/chat/completions"
MINIMAX_MODEL="MiniMax-M2"
```

To customize it:

```bash
cp .env.local.example .env.local
```

`.env.local` is ignored by Git.

### API

#### Health Check

```http
GET /api/health
```

Example response:

```json
{
  "ok": true,
  "table": "ads_auto_commercial_daily_wide",
  "columns": 81,
  "minimaxConfigured": true,
  "model": "MiniMax-M2"
}
```

#### Chat Query

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Which customers are suitable for additional budget?",
  "history": []
}
```

Response fields:

- `answer`: AI-generated sales analysis
- `sql`: SQL executed by the backend
- `reason`: Explanation of the query logic
- `columns`: Result columns
- `rows`: Result rows

### SQL Safety

The backend applies basic SQL safety checks:

- Only `SELECT` is allowed
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, etc. are blocked
- Multiple statements are blocked
- Query must reference `ads_auto_commercial_daily_wide`
- `LIMIT` is automatically appended

### Security Notes

- Never commit real API keys
- `.env.local`, `server.log`, and `server.pid` are ignored by Git
- Use `save_minimax_key.sh` to store the key in macOS Keychain
- Rotate your MiniMax API key immediately if it has ever been exposed

### Current Limitations

This is a local demo, not a production-grade system:

- No login or permission system
- No conversation persistence
- SQLite runs in memory and reloads CSV on restart
- No multi-user concurrency optimization
- No production database or BI integration
- Frontend is not built with a modern framework

### Future Improvements

- Upgrade frontend to React / Vue / Next.js
- Upgrade backend to FastAPI / Node.js
- Upgrade data layer to PostgreSQL / DuckDB / ClickHouse
- Add a semantic metrics layer
- Add sales org and customer-level permissions
- Integrate CRM, BI, and advertising platforms
- Add report export and task push capabilities
