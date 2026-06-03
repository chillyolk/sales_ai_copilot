# AGENTS.md

This file provides guidance to Genius Code (ByteCloud) when working with code in this repository.

## Common commands

Start the local app:

```bash
./start_app.sh
```

Stop the local app:

```bash
./stop_app.sh
```

Save MiniMax API Key to macOS Keychain:

```bash
./save_minimax_key.sh
```

Start with a temporary API key instead of Keychain:

```bash
MINIMAX_API_KEY="your_api_key" ./start_app.sh
```

Health check:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

Check Python syntax:

```bash
python3 -m py_compile server.py
```

Check frontend HTML and inline JavaScript syntax:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
HTMLParser().feed(Path('index.html').read_text(encoding='utf-8'))
print('html_ok')
PY

node -e "const fs=require('fs'); const html=fs.readFileSync('index.html','utf8'); const script=html.match(/<script>([\\s\\S]*)<\\/script>/)[1]; new Function(script); console.log('js_parse_ok')"
```

Run unittest discovery, even though there is currently no real test suite:

```bash
python3 -m unittest discover -s . -p 'test*.py'
```

Example `/api/chat` smoke test:

```bash
python3 - <<'PY'
import json, urllib.request
payload = json.dumps({
    'message': '哪些客户余额快没了？',
    'history': [],
    'skill': 'sql_query'
}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=payload,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
print(urllib.request.urlopen(req, timeout=120).read().decode('utf-8')[:1000])
PY
```

Push to GitHub using the configured SSH key if normal `git push` fails in this harness:

```bash
GIT_SSH_COMMAND='ssh -i /Users/bytedance/.ssh/id_ed25519 -o UserKnownHostsFile=/Users/bytedance/.ssh/known_hosts -o StrictHostKeyChecking=yes' git push
```

## Architecture overview

This is a lightweight local demo app for automotive advertising sales analytics.

High-level request flow:

```text
Browser frontend
  -> POST /api/chat
Python stdlib backend in server.py
  -> intent/skill routing
  -> optional SQLite query against CSV-loaded table
  -> optional MiniMax summary/report generation
  -> structured blocks returned to frontend
  -> index.html renders BI-like chat cards
```

Main runtime files:

- `index.html`: single-page frontend, CSS, inline JavaScript, chat UI, skill selector, multi-session localStorage state, mobile drawer, BI block renderer, report download UI.
- `server.py`: Python stdlib HTTP server, CSV-to-SQLite loader, MiniMax client, `/api/health`, `/api/chat`, intent routing, skill implementations, SQL safety checks.
- `ads_auto_commercial_mock_20260101_20260531.csv`: current data source loaded into in-memory SQLite table `ads_auto_commercial_daily_wide` at server startup.
- `skills/sales_weekly_report/`: standard skill package for sales weekly reports, with manifest, prompts, SQL templates, metrics, block layout, and examples.
- `README.md`: bilingual product and runbook documentation.
- `PRD.md`: product requirements.
- `PROJECT_STATUS.md`: current project status and recovery notes.
- `INTENT_ROUTING.md`: intent routing and skill behavior details.

## Backend details

`server.py` loads the CSV into an in-memory SQLite database on import/startup. It exposes:

- `GET /` and `GET /index.html`: serve the frontend.
- `GET /api/health`: returns table/model configuration status.
- `POST /api/chat`: primary chat endpoint.

The chat endpoint expects JSON like:

```json
{
  "message": "哪些客户适合追加预算？",
  "history": [],
  "skill": "auto"
}
```

Skill routing:

- `auto`: uses `detect_intent()`.
- `general_chat`: sales coaching / wording advice, no SQL.
- `sql_query`: data query path.
- `attribution_analysis`: fixed month-over-month consumption decline diagnosis workflow.
- `sales_weekly_report`: standard weekly report skill backed by files in `skills/sales_weekly_report/`.

Existing backend helpers worth reusing:

- MiniMax and JSON parsing: `minimax_chat()`, `extract_json()`, `clean_model_text()`.
- Schema description: `schema_text()`.
- SQL safety/execution: `is_safe_select()`, `add_limit()`, `execute_sql()`.
- Response format: `block_response()`, `table_block()`.
- Formatting/helpers: `format_amount()`, `format_number()`, `format_pct()`, `safe_divide()`, `pct_change()`.

SQL safety currently relies on read-only checks in `is_safe_select()` and destructive/write-intent filtering before query handling. Keep user-provided values parameterized when adding fixed SQL workflows.

## Frontend details

`index.html` is intentionally framework-free. Important frontend areas:

- `skillOptions`: controls the input-box skill selector.
- `appState` with `xiaoshutong_sessions_v1`: localStorage-backed multi-session state.
- `sendMessage()`: sends the current session's `history` and selected `skill` to `/api/chat`.
- `appendMessage()`: renders user/assistant bubbles.
- `renderBlocks()` / `renderBlock()`: renders structured response blocks.
- `renderChartBlock()`: supports simple `bar` and `line` chart blocks.
- `renderAssistantBlocks()`: wraps downloadable report blocks in a report container.
- `downloadReportImage()`: report image download path, with html2canvas support if present and SVG/canvas fallback.

Supported block types:

- `summary`
- `kpi_cards`
- `tags`
- `insights`
- `chart`
- `table`
- `actions`
- `followups`

The UI is responsive. Desktop uses a persistent left sidebar. Mobile uses a hidden drawer controlled by `sidebarToggleBtn` and `sidebarOverlay`.

## Skill package notes

The sales weekly report skill lives under:

```text
skills/sales_weekly_report/
```

Key files:

- `skill.json`: skill manifest and routing metadata.
- `metrics.json`: metric definitions and display labels.
- `blocks.json`: intended report block layout.
- `prompts/summary.md` and `prompts/actions.md`: LLM prompts for report text.
- `queries/*.sql`: fixed SQL templates for overview, comparison, trends, top customers/products, risks, and opportunities.
- `examples/*.json`: request/response examples.

When adding new standard skills, follow this package style rather than hard-coding all skill details directly in `server.py`. `server.py` may still need a thin adapter function to execute the skill.

## Data model notes

The current table is:

```text
ads_auto_commercial_daily_wide
```

Important dimensions include:

- Time: `stat_date`, `stat_month`
- Customer: `customer_account_id`, `customer_account_name`, `customer_id`, `customer_name`, `customer_type`, `customer_level`
- Sales org: `sales_id`, `sales_name`, `sales_department_name`, `sales_role`
- Geography: `province_name`, `city_name`, `city_tier`, `region_name`
- Product/brand: `brand_name`, `vehicle_series_name`, `ad_product_name`, `ad_product_type`

Important metrics include:

- Commercial: `recharge_amount`, `cost_amount`, `confirmed_revenue_amount`, `contract_amount`, `received_amount`, `overdue_receivable_amount`
- Funnel: `impression_cnt`, `click_cnt`, `lead_cnt`, `valid_lead_cnt`, `arrival_cnt`, `test_drive_cnt`, `order_cnt`, `vehicle_sales_cnt`
- Outcome: `gmv_amount`, `roi`, `cost_per_lead`, `cost_per_order`

For ratio metrics, compute from aggregated numerators and denominators rather than averaging row-level ratio fields.

## Local files and secrets

`.gitignore` excludes local runtime and secret files:

```text
.env.local
server.log
server.pid
__pycache__/
*.pyc
```

The project expects MiniMax configuration from environment variables or macOS Keychain via `start_app.sh`. The frontend should not receive API keys or Authorization headers.

## Current known context

The latest stable direction is to keep the app lightweight and local. A recent broad `data_analysis` query-planning refactor was reverted because it caused widespread query instability. If reattempting a generalized data-analysis pipeline, do it behind isolated paths and preserve stable existing skill behavior.