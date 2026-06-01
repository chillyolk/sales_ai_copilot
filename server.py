#!/usr/bin/env python3
import csv
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ads_auto_commercial_mock_20260101_20260531.csv"
INDEX_PATH = BASE_DIR / "index.html"
TABLE_NAME = "ads_auto_commercial_daily_wide"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_API_URL = os.getenv("MINIMAX_API_URL", "")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "minimax2.7")

NUMERIC_COLUMNS = {
    "recharge_amount", "cash_recharge_amount", "grant_recharge_amount", "refund_amount",
    "net_recharge_amount", "cost_amount", "cash_cost_amount", "grant_cost_amount",
    "pending_cost_amount", "opening_balance_amount", "closing_balance_amount", "frozen_amount",
    "available_balance_amount", "confirmed_revenue_amount", "unconfirmed_revenue_amount",
    "invoice_amount", "contract_amount", "new_contract_amount", "renewal_contract_amount",
    "receivable_amount", "received_amount", "overdue_receivable_amount", "impression_cnt",
    "click_cnt", "valid_click_cnt", "ctr", "cpc", "cpm", "lead_cnt", "valid_lead_cnt",
    "phone_lead_cnt", "form_lead_cnt", "im_lead_cnt", "test_drive_lead_cnt",
    "lead_conversion_rate", "cost_per_lead", "arrival_cnt", "test_drive_cnt", "order_cnt",
    "vehicle_sales_cnt", "gmv_amount", "cost_per_order", "roi", "active_campaign_cnt",
    "active_customer_cnt",
}

FIELD_DESCRIPTIONS = {
    "stat_date": "统计日期", "stat_month": "统计月份", "province_name": "省份",
    "city_name": "城市", "city_tier": "城市线级", "region_name": "大区",
    "business_line": "业务线", "industry_name": "行业", "sub_industry_name": "细分行业",
    "customer_account_id": "客户资金账户ID", "customer_account_name": "客户资金账户名称",
    "customer_id": "客户ID", "customer_name": "客户名称", "customer_type": "客户类型",
    "customer_level": "客户等级", "brand_name": "汽车品牌", "vehicle_series_name": "车系",
    "vehicle_energy_type": "能源类型", "vehicle_price_range": "价格带",
    "ad_product_name": "广告产品名称", "ad_product_type": "广告产品类型",
    "sales_channel": "销售渠道", "agent_name": "代理商名称", "sales_name": "销售姓名",
    "sales_department_name": "销售部门", "sales_role": "销售角色",
    "cost_amount": "广告消耗金额", "recharge_amount": "充值金额",
    "confirmed_revenue_amount": "确认收入", "contract_amount": "合同金额",
    "receivable_amount": "应收金额", "received_amount": "回款金额",
    "overdue_receivable_amount": "逾期应收", "impression_cnt": "曝光量",
    "click_cnt": "点击量", "valid_click_cnt": "有效点击量", "ctr": "点击率",
    "cpc": "点击成本", "cpm": "千次曝光成本", "lead_cnt": "线索量",
    "valid_lead_cnt": "有效线索量", "arrival_cnt": "到店量", "test_drive_cnt": "试驾量",
    "order_cnt": "订单量", "vehicle_sales_cnt": "成交车辆数", "gmv_amount": "GMV",
    "cost_per_lead": "单线索成本", "cost_per_order": "单订单成本", "roi": "ROI",
    "available_balance_amount": "可用余额", "active_campaign_cnt": "活跃计划数",
}

DB = sqlite3.connect(":memory:", check_same_thread=False)
DB.row_factory = sqlite3.Row


def load_csv_to_sqlite() -> list[str]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"缺少数据文件：{CSV_PATH}")

    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError("CSV 表头为空")

        definitions = []
        for col in columns:
            col_type = "REAL" if col in NUMERIC_COLUMNS else "TEXT"
            definitions.append(f'"{col}" {col_type}')

        DB.execute(f'DROP TABLE IF EXISTS "{TABLE_NAME}"')
        DB.execute(f'CREATE TABLE "{TABLE_NAME}" ({", ".join(definitions)})')

        placeholders = ", ".join(["?"] * len(columns))
        quoted_cols = ", ".join(f'"{col}"' for col in columns)
        insert_sql = f'INSERT INTO "{TABLE_NAME}" ({quoted_cols}) VALUES ({placeholders})'

        batch = []
        for row in reader:
            values = []
            for col in columns:
                raw = row.get(col, "")
                if col in NUMERIC_COLUMNS:
                    values.append(float(raw) if raw not in ("", None) else 0.0)
                else:
                    values.append(raw)
            batch.append(values)
            if len(batch) >= 1000:
                DB.executemany(insert_sql, batch)
                batch = []
        if batch:
            DB.executemany(insert_sql, batch)

    for idx_col in ["stat_date", "stat_month", "sales_name", "customer_account_id", "customer_account_name", "brand_name", "region_name", "ad_product_name"]:
        if idx_col in columns:
            DB.execute(f'CREATE INDEX IF NOT EXISTS "idx_{idx_col}" ON "{TABLE_NAME}" ("{idx_col}")')
    DB.commit()
    return columns


COLUMNS = load_csv_to_sqlite()


def schema_text() -> str:
    lines = [f"表名：{TABLE_NAME}", "字段："]
    for col in COLUMNS:
        col_type = "数值" if col in NUMERIC_COLUMNS else "文本/维度"
        desc = FIELD_DESCRIPTIONS.get(col, "")
        lines.append(f"- {col}（{col_type}{'，' + desc if desc else ''}）")
    lines.append("重要口径：聚合 CTR/CPL/ROI 等比率时，不要直接 AVG 原始比率，应尽量使用聚合后的分子分母重算。")
    lines.append("常用计算：CTR=sum(click_cnt)/sum(impression_cnt)，CPL=sum(cost_amount)/sum(lead_cnt)，ROI=sum(gmv_amount)/sum(cost_amount)。")
    lines.append("默认时间：如果用户没有指定时间，使用全量数据；如果说本月，可按最大 stat_month 处理。")
    return "\n".join(lines)


def minimax_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    if not MINIMAX_API_KEY or not MINIMAX_API_URL:
        raise RuntimeError("请先设置环境变量 MINIMAX_API_KEY 和 MINIMAX_API_URL")

    payload = {
        "model": MINIMAX_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MINIMAX_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiniMax API 请求失败：HTTP {e.code} {detail}") from e

    if isinstance(data, dict):
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
        reply = data.get("reply") or data.get("text") or data.get("output")
        if isinstance(reply, str):
            return reply
    raise RuntimeError(f"无法解析 MiniMax API 返回：{json.dumps(data, ensure_ascii=False)[:500]}")


def extract_json(text: str) -> dict[str, Any]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return json.loads(fenced.group(1))

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise json.JSONDecodeError("No JSON object found", text, 0)


def is_safe_select(sql: str) -> bool:
    normalized = re.sub(r"\s+", " ", sql.strip()).lower()
    if not normalized.startswith("select "):
        return False
    forbidden = [" insert ", " update ", " delete ", " drop ", " alter ", " create ", " attach ", " detach ", " pragma ", " vacuum ", " replace "]
    padded = f" {normalized} "
    if any(word in padded for word in forbidden):
        return False
    if ";" in normalized.rstrip(";"):
        return False
    return TABLE_NAME.lower() in normalized


def add_limit(sql: str, limit: int = 100) -> str:
    stripped = sql.strip().rstrip(";")
    if re.search(r"\blimit\s+\d+\b", stripped, re.I):
        return stripped
    return f"{stripped} LIMIT {limit}"


def execute_sql(sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    if not is_safe_select(sql):
        raise ValueError("模型生成的 SQL 不安全或不是 SELECT 查询")
    sql = add_limit(sql)
    cur = DB.execute(sql)
    rows = [dict(row) for row in cur.fetchall()]
    columns = [desc[0] for desc in cur.description or []]
    return columns, rows


def generate_sql(question: str, history: list[dict[str, str]]) -> dict[str, str]:
    system = f"""
你是汽车商业化广告销售数据分析专家。你的任务是把用户中文问题转换成 SQLite SELECT 查询。
只能查询已有表，不能修改数据。只返回 JSON，不要返回 Markdown。
JSON 格式：{{"sql":"SELECT ...", "reason":"一句话说明查询逻辑"}}
{schema_text()}
""".strip()
    recent = history[-6:] if history else []
    messages = [{"role": "system", "content": system}]
    messages.extend(recent)
    messages.append({"role": "user", "content": question})
    content = minimax_chat(messages, temperature=0.1)
    parsed = extract_json(content)
    sql = str(parsed.get("sql", "")).strip()
    reason = str(parsed.get("reason", "")).strip()
    if not sql:
        raise ValueError("模型未生成 SQL")
    return {"sql": sql, "reason": reason}


def summarize(question: str, sql: str, reason: str, rows: list[dict[str, Any]]) -> str:
    preview = rows[:80]
    system = """
你是销售经营 AI Copilot。请基于 SQL 查询结果回答销售的问题。
要求：先给结论；再给关键数据；最后给销售下一步建议。
如果结果为空，说明没有查到符合条件的数据，并建议用户换条件。
不要编造查询结果之外的数据。
""".strip()
    user = f"""
用户问题：{question}
SQL：{sql}
查询逻辑：{reason}
查询结果 JSON：{json.dumps(preview, ensure_ascii=False)}
请用中文输出，适合销售阅读。
""".strip()
    answer = minimax_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.3)
    return re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()


def local_fallback(question: str) -> dict[str, Any]:
    q = question
    if "余额" in q and ("快没" in q or "不足" in q or "断投" in q):
        sql = f'''
        SELECT customer_account_id, customer_account_name, sales_name,
               ROUND(SUM(available_balance_amount), 2) AS available_balance_amount,
               ROUND(SUM(cost_amount) / COUNT(DISTINCT stat_date), 2) AS avg_daily_cost,
               ROUND(SUM(available_balance_amount) / NULLIF(SUM(cost_amount) / COUNT(DISTINCT stat_date), 0), 2) AS estimated_days
        FROM {TABLE_NAME}
        GROUP BY customer_account_id, customer_account_name, sales_name
        HAVING avg_daily_cost > 0 AND estimated_days < 3
        ORDER BY estimated_days ASC, avg_daily_cost DESC
        LIMIT 20
        '''
        reason = "按客户聚合可用余额和日均消耗，筛选预计可投天数小于 3 天的客户。"
    elif "逾期" in q or "欠款" in q or "回款" in q:
        sql = f'''
        SELECT customer_account_id, customer_account_name, sales_name, customer_level,
               ROUND(SUM(receivable_amount), 2) AS receivable_amount,
               ROUND(SUM(received_amount), 2) AS received_amount,
               ROUND(SUM(overdue_receivable_amount), 2) AS overdue_receivable_amount
        FROM {TABLE_NAME}
        GROUP BY customer_account_id, customer_account_name, sales_name, customer_level
        HAVING overdue_receivable_amount > 0
        ORDER BY overdue_receivable_amount DESC
        LIMIT 20
        '''
        reason = "按客户聚合应收、回款和逾期应收，找出欠款风险最高的客户。"
    elif "产品" in q or "线索通" in q or "信息流" in q:
        sql = f'''
        SELECT ad_product_type, ad_product_name,
               ROUND(SUM(cost_amount), 2) AS cost_amount,
               CAST(SUM(lead_cnt) AS INTEGER) AS lead_cnt,
               CAST(SUM(order_cnt) AS INTEGER) AS order_cnt,
               ROUND(SUM(gmv_amount), 2) AS gmv_amount,
               ROUND(SUM(cost_amount) / NULLIF(SUM(lead_cnt), 0), 2) AS cpl,
               ROUND(SUM(gmv_amount) / NULLIF(SUM(cost_amount), 0), 2) AS roi
        FROM {TABLE_NAME}
        GROUP BY ad_product_type, ad_product_name
        ORDER BY roi DESC
        LIMIT 20
        '''
        reason = "按广告产品聚合消耗、线索、订单、GMV，并计算 CPL 和 ROI。"
    elif "销售" in q:
        sql = f'''
        SELECT sales_department_name, sales_name,
               ROUND(SUM(cost_amount), 2) AS cost_amount,
               ROUND(SUM(confirmed_revenue_amount), 2) AS confirmed_revenue_amount,
               ROUND(SUM(recharge_amount), 2) AS recharge_amount,
               CAST(SUM(lead_cnt) AS INTEGER) AS lead_cnt,
               CAST(SUM(order_cnt) AS INTEGER) AS order_cnt,
               ROUND(SUM(gmv_amount), 2) AS gmv_amount,
               ROUND(SUM(overdue_receivable_amount), 2) AS overdue_receivable_amount
        FROM {TABLE_NAME}
        GROUP BY sales_department_name, sales_name
        ORDER BY cost_amount DESC
        LIMIT 20
        '''
        reason = "按销售聚合核心经营指标并按消耗排序。"
    else:
        sql = f'''
        SELECT customer_account_id, customer_account_name, sales_name, customer_level,
               ROUND(SUM(cost_amount), 2) AS cost_amount,
               ROUND(SUM(recharge_amount), 2) AS recharge_amount,
               CAST(SUM(lead_cnt) AS INTEGER) AS lead_cnt,
               CAST(SUM(order_cnt) AS INTEGER) AS order_cnt,
               ROUND(SUM(gmv_amount), 2) AS gmv_amount,
               ROUND(SUM(gmv_amount) / NULLIF(SUM(cost_amount), 0), 2) AS roi
        FROM {TABLE_NAME}
        GROUP BY customer_account_id, customer_account_name, sales_name, customer_level
        ORDER BY cost_amount DESC
        LIMIT 20
        '''
        reason = "默认按客户聚合消耗、充值、线索、订单、GMV 和 ROI，展示消耗最高客户。"
    columns, rows = execute_sql(sql)
    answer = build_local_answer(question, reason, rows)
    return {"answer": answer, "sql": add_limit(sql), "reason": reason, "columns": columns, "rows": rows, "fallback": True}


def build_local_answer(question: str, reason: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"## 结论\n没有查到符合条件的数据。\n\n## 查询逻辑\n{reason}\n\n## 建议动作\n可以放宽时间、客户等级、区域或金额阈值后再查询。"
    first = rows[0]
    keys = list(first.keys())[:6]
    summary = "，".join(f"{k}={first[k]}" for k in keys)
    return f"## 结论\n已查询到 {len(rows)} 条结果。排名第一记录为：{summary}。\n\n## 查询逻辑\n{reason}\n\n## 建议动作\n建议优先查看排名靠前客户，结合消耗、ROI、余额和逾期应收判断是否需要跟进、复盘或推荐追加预算。"


def handle_chat(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    if not question:
        raise ValueError("请输入问题")
    if not MINIMAX_API_KEY or not MINIMAX_API_URL:
        return local_fallback(question)
    plan = generate_sql(question, history if isinstance(history, list) else [])
    columns, rows = execute_sql(plan["sql"])
    answer = summarize(question, add_limit(plan["sql"]), plan["reason"], rows)
    return {"answer": answer, "sql": add_limit(plan["sql"]), "reason": plan["reason"], "columns": columns, "rows": rows, "fallback": False}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = INDEX_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/health":
            self.send_json(200, {
                "ok": True,
                "table": TABLE_NAME,
                "columns": len(COLUMNS),
                "minimaxConfigured": bool(MINIMAX_API_KEY and MINIMAX_API_URL),
                "model": MINIMAX_MODEL,
            })
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(200, handle_chat(payload))
        except Exception as e:
            self.send_json(400, {"error": str(e)})


def main() -> None:
    print(f"已加载 {CSV_PATH.name} 到 SQLite 表 {TABLE_NAME}，字段数 {len(COLUMNS)}")
    print("MiniMax 配置：", "已配置" if MINIMAX_API_KEY and MINIMAX_API_URL else "未配置，将使用本地规则兜底")
    print(f"服务地址：http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
