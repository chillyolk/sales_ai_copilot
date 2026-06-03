#!/usr/bin/env python3
import csv
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ads_auto_commercial_mock_20260101_20260531.csv"
INDEX_PATH = BASE_DIR / "index.html"
TABLE_NAME = "ads_auto_commercial_daily_wide"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_API_URL = os.getenv("MINIMAX_API_URL", "")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2")

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
DB_LOCK = threading.RLock()
CHAT_CACHE_LOCK = threading.RLock()
CHAT_CACHE: dict[str, dict[str, Any]] = {}


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
    with DB_LOCK:
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


def clean_model_text(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def block_response(
    *,
    intent: str,
    skill: str,
    answer: str,
    blocks: list[dict[str, Any]],
    debug: Optional[dict[str, Any]] = None,
    sql: str = "",
    reason: str = "",
    columns: Optional[list[str]] = None,
    rows: Optional[list[dict[str, Any]]] = None,
    fallback: bool = False,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "skill": skill,
        "answer": answer,
        "blocks": blocks,
        "debug": debug or {},
        "sql": sql,
        "reason": reason,
        "columns": columns or [],
        "rows": rows or [],
        "fallback": fallback,
    }


SUPPORTED_SKILLS = {"general_chat", "sql_query", "attribution_analysis", "sales_weekly_report"}


def detect_intent(question: str) -> dict[str, Any]:
    q = question.lower()
    diagnosis_keywords = ["归因", "诊断", "原因", "为什么", "环比", "同比", "下降", "下滑", "波动", "拆解"]
    report_keywords = ["周报", "周总结", "本周复盘", "上周复盘", "经营周报", "销售周报", "生成看板"]
    chat_keywords = ["话术", "怎么说", "怎么聊", "拜访", "沟通", "客户异议", "开场白", "邀约", "谈判", "说服"]
    query_keywords = ["哪些", "top", "排名", "多少", "查询", "筛选", "余额", "逾期", "回款", "消耗", "roi", "cpl", "线索", "订单"]

    if any(k in question for k in diagnosis_keywords) and any(k in question for k in ["客户", "消耗", "线索", "订单", "roi", "cpl"]):
        return {"intent": "attribution_analysis", "skill": "attribution_analysis", "requires_data": True, "confidence": 0.9}
    if any(k in question for k in report_keywords):
        return {"intent": "sales_weekly_report", "skill": "sales_weekly_report", "requires_data": True, "confidence": 0.88}
    if any(k in question for k in chat_keywords):
        return {"intent": "general_chat", "skill": "general_chat", "requires_data": False, "confidence": 0.85}
    if any(k in q for k in query_keywords):
        return {"intent": "data_query", "skill": "sql_query", "requires_data": True, "confidence": 0.8}
    return {"intent": "general_chat", "skill": "general_chat", "requires_data": False, "confidence": 0.55}


def general_chat_skill(question: str, history: list[dict[str, str]]) -> dict[str, Any]:
    if not MINIMAX_API_KEY or not MINIMAX_API_URL:
        answer = "## 拜访话术建议\n- 先确认客户近期经营目标：本月更关注线索、到店还是成交？\n- 用数据切入：我想帮您复盘最近投放效果，看看哪些预算能带来更高转化。\n- 提出下一步：如果您方便，我可以准备一份客户诊断和优化建议。"
    else:
        system = """
你是汽车广告销售教练，负责帮助销售准备客户拜访、沟通话术、异议处理和行动建议。
如果用户没有要求查具体数据，不要编造数据；直接给可落地的话术和沟通框架。
输出要简洁，适合销售直接复制使用。
""".strip()
        messages = [{"role": "system", "content": system}]
        messages.extend(history[-6:] if isinstance(history, list) else [])
        messages.append({"role": "user", "content": question})
        answer = clean_model_text(minimax_chat(messages, temperature=0.5))
    blocks = [
        {"type": "summary", "title": "销售沟通建议", "content": answer},
        {"type": "tags", "items": ["不需要查数", "销售话术", "客户沟通"]},
        {"type": "followups", "items": ["帮我生成一版更强势的商务话术", "如果客户说预算不够，我该怎么回应？", "帮我结合客户投放数据做拜访简报"]},
    ]
    return block_response(intent="general_chat", skill="general_chat", answer=answer, blocks=blocks)


def table_block(title: str, columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "table", "title": title, "columns": columns, "rows": rows}


def is_destructive_or_write_request(question: str) -> bool:
    q = question.lower()
    dangerous_terms = [
        "drop", "delete", "update", "insert", "alter", "create", "truncate", "replace", "清空", "删除",
        "删掉", "移除", "更新", "修改", "写入", "插入", "新增", "创建", "建表", "删表", "清除",
        "改余额", "修改余额", "更新余额", "调整余额", "改数据", "修改数据", "写数据",
    ]
    return any(term in q or term in question for term in dangerous_terms)


def chat_cache_key(skill: str, question: str, history: list[dict[str, str]]) -> str:
    recent = history[-6:] if isinstance(history, list) else []
    return json.dumps({"skill": skill, "question": question, "history": recent}, ensure_ascii=False, sort_keys=True)


def clone_response(response: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(response, ensure_ascii=False))


def extract_context_customer_and_month(context: Optional[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    if not context:
        return None, None
    rows = context.get("rows") or []
    customer = None
    month = None
    for row in rows:
        if not customer:
            customer = row.get("客户名称") or row.get("customer_name") or row.get("customer_account_name")
        if not month:
            date_value = row.get("统计日期") or row.get("stat_date")
            month_value = row.get("统计月份") or row.get("stat_month")
            if month_value:
                month = str(month_value)
            elif date_value:
                month = str(date_value)[:7]
        if customer and month:
            break
    debug = context.get("debug") or {}
    reason = context.get("reason") or debug.get("reason") or ""
    if not customer:
        match = re.search(r"客户名称[“\"]?([^，。\s“”\"]+)", reason)
        if match:
            customer = match.group(1)
    if not month:
        match = re.search(r"(20\d{2}-\d{2})", reason)
        if match:
            month = match.group(1)
    return customer, month


def latest_year_month_from_data(month: int) -> str:
    if month < 1 or month > 12:
        return ""
    with DB_LOCK:
        row = DB.execute(f'SELECT MAX(stat_date) AS max_date FROM "{TABLE_NAME}"').fetchone()
    year = datetime.strptime(row["max_date"], "%Y-%m-%d").year
    return f"{year}-{month:02d}"


def extract_month_from_text(text: str) -> Optional[str]:
    match = re.search(r"(20\d{2})[-年](\d{1,2})月?", text)
    if match:
        month = int(match.group(2))
        return f"{int(match.group(1)):04d}-{month:02d}" if 1 <= month <= 12 else None
    match = re.search(r"(\d{1,2})\s*月份?|([一二三四五六七八九十])月", text)
    if match:
        if match.group(1):
            month = int(match.group(1))
        else:
            month_map = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
            month = month_map.get(match.group(2), 0)
        return latest_year_month_from_data(month)
    return None


def extract_customer_name_from_text(text: str) -> Optional[str]:
    patterns = [
        r"客户名称(?:为|是|=)(.+?)(?:的|，|,|。|$)",
        r"客户(?:为|是|=)(.+?)(?:的|，|,|。|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip(" ，,。？?\"'")
            if name:
                return name
    return None


def extract_context_from_history(history: list[dict[str, str]]) -> tuple[Optional[str], Optional[str]]:
    customer = None
    month = None
    for message in reversed(history[-8:] if isinstance(history, list) else []):
        content = message.get("content", "") if isinstance(message, dict) else ""
        if not customer:
            customer = extract_customer_name_from_text(content)
        if not month:
            month = extract_month_from_text(content)
        if customer and month:
            break
    return customer, month


def resolve_followup_question(question: str, context: Optional[dict[str, Any]], history: list[dict[str, str]]) -> str:
    customer, month = extract_context_customer_and_month(context) if context else (None, None)
    history_customer, history_month = extract_context_from_history(history)
    customer = customer or history_customer
    month = month or history_month
    resolved = question
    if customer and any(token in question for token in ["这个客户", "该客户", "这个", "它"]):
        resolved = resolved.replace("这个客户", f"客户名称为{customer}").replace("该客户", f"客户名称为{customer}")
    if customer and "客户" not in resolved and any(metric in question for metric in ["充值", "消耗", "线索", "订单", "ROI", "roi"]):
        resolved = f"客户名称为{customer}，{resolved}"
    if month and not re.search(r"\d{1,2}\s*月份?|20\d{2}[-年]\d{1,2}", resolved):
        resolved = f"统计周期为{month}，{resolved}"
    return resolved


def sql_query_skill(question: str, history: list[dict[str, str]], context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if is_destructive_or_write_request(question):
        raise ValueError("当前应用仅支持只读数据查询和分析，不支持修改、写入或删除数据。")
    question = resolve_followup_question(question, context, history)
    key = chat_cache_key("sql_query", question, history)
    with CHAT_CACHE_LOCK:
        cached = CHAT_CACHE.get(key)
        if cached is not None:
            return clone_response(cached)

        if not MINIMAX_API_KEY or not MINIMAX_API_URL:
            result = local_fallback(question)
            result.setdefault("intent", "data_query")
            result.setdefault("skill", "sql_query")
            result.setdefault("blocks", [
                {"type": "summary", "title": "查询结论", "content": result.get("answer", "")},
                table_block("查询结果", result.get("columns", []), result.get("rows", [])),
            ])
            result.setdefault("debug", {"sql": result.get("sql", ""), "reason": result.get("reason", "")})
            CHAT_CACHE[key] = clone_response(result)
            return result

        plan = generate_sql(question, history if isinstance(history, list) else [])
        sql = add_limit(plan["sql"])
        columns, rows = execute_sql(sql)
        answer = summarize(question, sql, plan["reason"], rows)
        blocks = [
            {"type": "summary", "title": "查询结论", "content": answer},
            table_block("查询结果", columns, rows[:100]),
            {"type": "followups", "items": ["继续分析这些客户的风险", "帮我按销售负责人汇总", "把结果整理成客户跟进清单"]},
        ]
        result = block_response(
            intent="data_query",
            skill="sql_query",
            answer=answer,
            blocks=blocks,
            debug={"sql": sql, "reason": plan["reason"]},
            sql=sql,
            reason=plan["reason"],
            columns=columns,
            rows=rows,
        )
        CHAT_CACHE[key] = clone_response(result)
        return result


def load_skill_file(skill_name: str, relative_path: str) -> str:
    return (BASE_DIR / "skills" / skill_name / relative_path).read_text(encoding="utf-8")


def load_skill_json(skill_name: str, relative_path: str) -> dict[str, Any]:
    return json.loads(load_skill_file(skill_name, relative_path))


def resolve_week_range(question: str) -> dict[str, str]:
    with DB_LOCK:
        row = DB.execute(f'SELECT MAX(stat_date) AS max_date FROM "{TABLE_NAME}"').fetchone()
    latest = datetime.strptime(row["max_date"], "%Y-%m-%d")
    this_week_start = latest - timedelta(days=latest.weekday())
    if "本周" in question:
        start = this_week_start
        end = latest
    else:
        start = this_week_start - timedelta(days=7)
        end = this_week_start - timedelta(days=1)
    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)
    trend_start = start - timedelta(days=28)
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "prev_start_date": prev_start.strftime("%Y-%m-%d"),
        "prev_end_date": prev_end.strftime("%Y-%m-%d"),
        "trend_start_date": trend_start.strftime("%Y-%m-%d"),
    }


def parse_report_scope(question: str) -> dict[str, Optional[str]]:
    with DB_LOCK:
        sales_names = [row[0] for row in DB.execute(f'SELECT DISTINCT sales_name FROM "{TABLE_NAME}" WHERE sales_name != ""').fetchall()]
        departments = [row[0] for row in DB.execute(f'SELECT DISTINCT sales_department_name FROM "{TABLE_NAME}" WHERE sales_department_name != ""').fetchall()]
    for name in sales_names:
        if name and name in question:
            return {"scope_type": "sales", "scope_name": name, "sales_name": name, "department_name": None}
    for department in departments:
        if department and department in question:
            return {"scope_type": "department", "scope_name": department, "sales_name": None, "department_name": department}
    return {"scope_type": "all", "scope_name": "全量销售", "sales_name": None, "department_name": None}


def safe_divide(numerator: float, denominator: float) -> Optional[float]:
    return None if not denominator else numerator / denominator


def format_amount(value: float) -> str:
    value = float(value or 0)
    if abs(value) >= 100000000:
        return f"{value / 100000000:.2f}亿"
    if abs(value) >= 10000:
        return f"{value / 10000:.2f}万"
    return f"{value:.0f}"


def format_number(value: float) -> str:
    return f"{int(value or 0):,}"


def add_ratio_fields(row: dict[str, Any]) -> dict[str, Any]:
    cost = float(row.get("cost_amount") or 0)
    valid_leads = float(row.get("valid_lead_cnt") or 0)
    gmv = float(row.get("gmv_amount") or 0)
    impressions = float(row.get("impression_cnt") or 0)
    clicks = float(row.get("click_cnt") or 0)
    row["cpl"] = safe_divide(cost, valid_leads)
    row["roi"] = safe_divide(gmv, cost)
    row["ctr"] = safe_divide(clicks, impressions)
    return row


def run_skill_query(query_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    sql = load_skill_file("sales_weekly_report", f"queries/{query_name}.sql")
    with DB_LOCK:
        return [dict(row) for row in DB.execute(sql, params).fetchall()]


def sales_weekly_report_skill(question: str, history: list[dict[str, str]]) -> dict[str, Any]:
    manifest = load_skill_json("sales_weekly_report", "skill.json")
    period = resolve_week_range(question)
    scope = parse_report_scope(question)
    top_n = 10
    params = {
        **period,
        "sales_name": scope["sales_name"],
        "department_name": scope["department_name"],
        "top_n": top_n,
    }

    overview = add_ratio_fields((run_skill_query("weekly_overview", params) or [{}])[0])
    compare = add_ratio_fields((run_skill_query("weekly_compare", params) or [{}])[0])
    trend_rows = [add_ratio_fields(row) for row in run_skill_query("weekly_trend", params)]
    top_customers = [add_ratio_fields(row) for row in run_skill_query("top_customers", params)]
    top_products = [add_ratio_fields(row) for row in run_skill_query("top_products", params)]
    risks = [add_ratio_fields(row) for row in run_skill_query("risk_customers", {**params, "top_n": 5})]
    opportunities = [add_ratio_fields(row) for row in run_skill_query("opportunity_customers", {**params, "top_n": 5})]

    def metric_change(metric: str) -> Optional[float]:
        return pct_change(float(overview.get(metric) or 0), float(compare.get(metric) or 0))

    kpis = [
        {"label": "消耗", "value": f"{format_amount(overview.get('cost_amount', 0))} | {format_pct(metric_change('cost_amount'))}"},
        {"label": "确认收入", "value": f"{format_amount(overview.get('confirmed_revenue_amount', 0))} | {format_pct(metric_change('confirmed_revenue_amount'))}"},
        {"label": "回款", "value": f"{format_amount(overview.get('received_amount', 0))} | {format_pct(metric_change('received_amount'))}"},
        {"label": "合同金额", "value": f"{format_amount(overview.get('contract_amount', 0))} | {format_pct(metric_change('contract_amount'))}"},
        {"label": "有效线索", "value": f"{format_number(overview.get('valid_lead_cnt', 0))} | {format_pct(metric_change('valid_lead_cnt'))}"},
        {"label": "订单", "value": f"{format_number(overview.get('order_cnt', 0))} | {format_pct(metric_change('order_cnt'))}"},
        {"label": "GMV", "value": f"{format_amount(overview.get('gmv_amount', 0))} | {format_pct(metric_change('gmv_amount'))}"},
        {"label": "ROI", "value": f"{(overview.get('roi') or 0):.2f} | {format_pct(pct_change(overview.get('roi') or 0, compare.get('roi') or 0))}"},
    ]

    customer_table = [{
        "客户": row.get("customer_account_name"),
        "销售": row.get("sales_name"),
        "客户等级": row.get("customer_level"),
        "消耗": format_amount(row.get("cost_amount", 0)),
        "有效线索": format_number(row.get("valid_lead_cnt", 0)),
        "订单": format_number(row.get("order_cnt", 0)),
        "GMV": format_amount(row.get("gmv_amount", 0)),
        "ROI": f"{(row.get('roi') or 0):.2f}",
    } for row in top_customers]

    product_table = [{
        "产品类型": row.get("ad_product_type"),
        "广告产品": row.get("ad_product_name"),
        "消耗": format_amount(row.get("cost_amount", 0)),
        "有效线索": format_number(row.get("valid_lead_cnt", 0)),
        "订单": format_number(row.get("order_cnt", 0)),
        "ROI": f"{(row.get('roi') or 0):.2f}",
        "CPL": format_amount(row.get("cpl") or 0),
    } for row in top_products]

    risk_table = [{
        "客户": row.get("customer_account_name"),
        "销售": row.get("sales_name"),
        "风险": "逾期/余额/转化风险",
        "证据": f"逾期{format_amount(row.get('overdue_receivable_amount', 0))}，余额{format_amount(row.get('available_balance_amount', 0))}，订单{format_number(row.get('order_cnt', 0))}",
        "建议动作": "优先确认预算、余额和回款状态",
    } for row in risks]

    opportunity_table = [{
        "客户": row.get("customer_account_name"),
        "销售": row.get("sales_name"),
        "机会": "高 ROI 可扩量",
        "ROI": f"{(row.get('roi') or 0):.2f}",
        "CPL": format_amount(row.get("cpl") or 0),
        "建议动作": "沟通追加预算或扩大高效产品投放",
    } for row in opportunities]

    evidence = {
        "scope": scope,
        "period": period,
        "overview": overview,
        "top_customers": customer_table[:5],
        "top_products": product_table[:5],
        "risks": risk_table,
        "opportunities": opportunity_table,
    }
    if MINIMAX_API_KEY and MINIMAX_API_URL:
        summary_prompt = load_skill_file("sales_weekly_report", "prompts/summary.md")
        actions_prompt = load_skill_file("sales_weekly_report", "prompts/actions.md")
        answer = clean_model_text(minimax_chat([
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ], temperature=0.25))
        actions_text = clean_model_text(minimax_chat([
            {"role": "system", "content": actions_prompt},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ], temperature=0.25))
    else:
        answer = f"{scope['scope_name']}在 {period['start_date']} 至 {period['end_date']} 的周报已生成。"
        actions_text = "- 优先跟进风险客户\n- 推动高 ROI 客户追加预算\n- 复盘低转化产品"

    trend_items = [{"label": row.get("stat_month") or row.get("end_date"), "value": round(float(row.get("cost_amount") or 0), 2)} for row in trend_rows]
    customer_chart_items = [{"label": (row.get("customer_account_name") or "")[:12], "value": round(float(row.get("cost_amount") or 0), 2)} for row in top_customers[:5]]
    action_items = [line.strip("- ").strip() for line in actions_text.splitlines() if line.strip()][:5]
    if not action_items:
        action_items = ["优先跟进风险客户", "推动高 ROI 客户追加预算", "复盘低转化产品"]

    title = f"{scope['scope_name']}销售周报"
    filename = f"销售周报_{period['start_date']}_{period['end_date']}.png"
    blocks = [
        {"type": "summary", "title": title, "content": f"**周期：**{period['start_date']} 至 {period['end_date']}\n\n{answer}"},
        {"type": "kpi_cards", "items": kpis},
        {"type": "tags", "items": ["销售周报", scope["scope_type"], "上周", "可下载图片"]},
        {"type": "chart", "title": "近 4 周消耗趋势", "chartType": "bar", "data": {"items": trend_items}},
        {"type": "chart", "title": "客户贡献 Top5", "chartType": "bar", "data": {"items": customer_chart_items}},
        table_block("客户贡献明细", list(customer_table[0].keys()) if customer_table else [], customer_table),
        table_block("产品表现明细", list(product_table[0].keys()) if product_table else [], product_table),
        table_block("风险客户", list(risk_table[0].keys()) if risk_table else [], risk_table),
        table_block("机会客户", list(opportunity_table[0].keys()) if opportunity_table else [], opportunity_table),
        {"type": "actions", "title": "下周建议动作", "items": action_items},
        {"type": "followups", "items": ["继续分析风险客户", "把周报按销售拆分", "生成本周周报"]},
    ]
    result = block_response(
        intent="sales_weekly_report",
        skill="sales_weekly_report",
        answer=answer,
        blocks=blocks,
        debug={"period": period, "scope": scope, "source": manifest.get("name")},
    )
    result["report"] = {"type": "weekly_report", "downloadable": True, "filename": filename, "width": 1200}
    return result


def get_latest_months() -> tuple[str, str]:
    with DB_LOCK:
        rows = DB.execute(f'SELECT DISTINCT stat_month FROM "{TABLE_NAME}" ORDER BY stat_month DESC LIMIT 2').fetchall()
    if len(rows) < 2:
        raise ValueError("数据不足，无法做月环比分析")
    return rows[0][0], rows[1][0]


def pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return (current - previous) / previous


def format_pct(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def infer_causes(row: dict[str, Any]) -> list[str]:
    causes = []
    checks = [
        ("曝光下滑", row.get("impression_change")),
        ("点击下滑", row.get("click_change")),
        ("线索下滑", row.get("lead_change")),
        ("订单下滑", row.get("order_change")),
        ("GMV 下滑", row.get("gmv_change")),
    ]
    for label, value in checks:
        if isinstance(value, (int, float)) and value <= -0.2:
            causes.append(f"{label} {format_pct(value)}")
    if isinstance(row.get("cpl_change"), (int, float)) and row["cpl_change"] >= 0.2:
        causes.append(f"CPL 上升 {format_pct(row['cpl_change'])}")
    if isinstance(row.get("roi_change"), (int, float)) and row["roi_change"] <= -0.2:
        causes.append(f"ROI 下降 {format_pct(row['roi_change'])}")
    return causes[:3] or ["消耗下降明显，建议进一步查看产品结构和客户预算变化"]


def attribution_analysis_skill(question: str, history: list[dict[str, str]]) -> dict[str, Any]:
    current_month, previous_month = get_latest_months()
    sql = f'''
    WITH monthly AS (
      SELECT customer_account_id, customer_account_name, sales_name, customer_level, stat_month,
             SUM(cost_amount) AS cost_amount,
             SUM(impression_cnt) AS impression_cnt,
             SUM(click_cnt) AS click_cnt,
             SUM(lead_cnt) AS lead_cnt,
             SUM(valid_lead_cnt) AS valid_lead_cnt,
             SUM(order_cnt) AS order_cnt,
             SUM(gmv_amount) AS gmv_amount
      FROM "{TABLE_NAME}"
      WHERE stat_month IN (?, ?)
      GROUP BY customer_account_id, customer_account_name, sales_name, customer_level, stat_month
    )
    SELECT cur.customer_account_id, cur.customer_account_name, cur.sales_name, cur.customer_level,
           ROUND(prev.cost_amount, 2) AS previous_cost,
           ROUND(cur.cost_amount, 2) AS current_cost,
           ROUND(cur.cost_amount - prev.cost_amount, 2) AS cost_delta,
           ROUND((cur.cost_amount - prev.cost_amount) / NULLIF(prev.cost_amount, 0), 4) AS cost_change,
           prev.impression_cnt AS previous_impressions, cur.impression_cnt AS current_impressions,
           prev.click_cnt AS previous_clicks, cur.click_cnt AS current_clicks,
           prev.lead_cnt AS previous_leads, cur.lead_cnt AS current_leads,
           prev.valid_lead_cnt AS previous_valid_leads, cur.valid_lead_cnt AS current_valid_leads,
           prev.order_cnt AS previous_orders, cur.order_cnt AS current_orders,
           ROUND(prev.gmv_amount, 2) AS previous_gmv, ROUND(cur.gmv_amount, 2) AS current_gmv,
           ROUND(prev.cost_amount / NULLIF(prev.lead_cnt, 0), 2) AS previous_cpl,
           ROUND(cur.cost_amount / NULLIF(cur.lead_cnt, 0), 2) AS current_cpl,
           ROUND(prev.gmv_amount / NULLIF(prev.cost_amount, 0), 2) AS previous_roi,
           ROUND(cur.gmv_amount / NULLIF(cur.cost_amount, 0), 2) AS current_roi
    FROM monthly cur
    JOIN monthly prev ON cur.customer_account_id = prev.customer_account_id
    WHERE cur.stat_month = ? AND prev.stat_month = ?
      AND prev.cost_amount > 0
      AND (cur.cost_amount - prev.cost_amount) / prev.cost_amount <= -0.2
    ORDER BY cost_delta ASC
    LIMIT 30
    '''
    with DB_LOCK:
        rows = [dict(row) for row in DB.execute(sql, (current_month, previous_month, current_month, previous_month)).fetchall()]
    columns = list(rows[0].keys()) if rows else []

    enriched = []
    for row in rows:
        row["impression_change"] = pct_change(float(row["current_impressions"] or 0), float(row["previous_impressions"] or 0))
        row["click_change"] = pct_change(float(row["current_clicks"] or 0), float(row["previous_clicks"] or 0))
        row["lead_change"] = pct_change(float(row["current_leads"] or 0), float(row["previous_leads"] or 0))
        row["order_change"] = pct_change(float(row["current_orders"] or 0), float(row["previous_orders"] or 0))
        row["gmv_change"] = pct_change(float(row["current_gmv"] or 0), float(row["previous_gmv"] or 0))
        row["cpl_change"] = pct_change(float(row["current_cpl"] or 0), float(row["previous_cpl"] or 0)) if row.get("previous_cpl") else None
        row["roi_change"] = pct_change(float(row["current_roi"] or 0), float(row["previous_roi"] or 0)) if row.get("previous_roi") else None
        row["main_causes"] = "；".join(infer_causes(row))
        enriched.append(row)

    affected_count = len(enriched)
    total_decline = sum(abs(float(row["cost_delta"])) for row in enriched)
    avg_decline = sum(float(row["cost_change"]) for row in enriched) / affected_count if affected_count else 0
    lead_drop_count = sum(1 for row in enriched if isinstance(row.get("lead_change"), float) and row["lead_change"] <= -0.2)
    order_drop_count = sum(1 for row in enriched if isinstance(row.get("order_change"), float) and row["order_change"] <= -0.2)
    cpl_up_count = sum(1 for row in enriched if isinstance(row.get("cpl_change"), float) and row["cpl_change"] >= 0.2)

    table_rows = []
    for row in enriched[:20]:
        table_rows.append({
            "客户": row["customer_account_name"],
            "销售": row["sales_name"],
            "客户等级": row["customer_level"],
            "上月消耗": row["previous_cost"],
            "本月消耗": row["current_cost"],
            "消耗变化": format_pct(row["cost_change"]),
            "线索变化": format_pct(row["lead_change"]),
            "订单变化": format_pct(row["order_change"]),
            "ROI变化": format_pct(row["roi_change"]),
            "主要原因": row["main_causes"],
        })

    insights = [
        f"共发现 {affected_count} 个客户本月较上月消耗下降超过 20%。",
        f"这些客户合计消耗减少约 {total_decline:,.0f} 元，平均降幅 {format_pct(avg_decline)}。",
    ]
    if lead_drop_count:
        insights.append(f"其中 {lead_drop_count} 个客户同时出现线索下滑，优先排查流量承接和线索质量。")
    if order_drop_count:
        insights.append(f"其中 {order_drop_count} 个客户订单下滑，建议复盘到店、试驾和销售跟进链路。")
    if cpl_up_count:
        insights.append(f"其中 {cpl_up_count} 个客户 CPL 上升，可能存在点击成本抬升或转化率下降。")

    chart_items = [
        {"label": row["customer_account_name"][:12], "value": round(abs(float(row["cost_delta"])), 2)}
        for row in enriched[:8]
    ]

    evidence = {
        "current_month": current_month,
        "previous_month": previous_month,
        "affected_count": affected_count,
        "total_decline": round(total_decline, 2),
        "avg_decline": round(avg_decline, 4),
        "top_customers": table_rows[:8],
        "insights": insights,
    }
    if MINIMAX_API_KEY and MINIMAX_API_URL:
        system = """
你是销售经营分析专家。请基于给定证据生成归因诊断报告，不要编造证据之外的数据。
输出要包括：结论、主要原因、重点客户、销售动作建议。
""".strip()
        answer = clean_model_text(minimax_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ], temperature=0.3))
    else:
        answer = "\n".join(["## 归因诊断结论", *[f"- {item}" for item in insights]])

    blocks = [
        {"type": "summary", "title": "归因诊断结论", "content": answer},
        {"type": "kpi_cards", "items": [
            {"label": "分析月份", "value": f"{previous_month} → {current_month}"},
            {"label": "下降客户数", "value": affected_count},
            {"label": "消耗减少", "value": f"{total_decline:,.0f}"},
            {"label": "平均降幅", "value": format_pct(avg_decline)},
        ]},
        {"type": "tags", "items": ["消耗下降≥20%", "月环比", "归因诊断", "需优先跟进"]},
        {"type": "insights", "items": insights},
        {"type": "chart", "title": "消耗下降 Top 客户", "chartType": "bar", "data": {"items": chart_items}},
        table_block("客户归因明细", list(table_rows[0].keys()) if table_rows else [], table_rows),
        {"type": "actions", "items": [
            "优先联系消耗下降金额最大的客户，确认预算、投放节奏或合作状态是否变化。",
            "对线索同步下滑客户，拆解曝光、点击和线索转化链路，判断是流量不足还是承接不足。",
            "对 CPL 上升客户，复盘产品结构和点击成本，考虑迁移部分预算到更高 ROI 产品。",
            "对订单下滑客户，联动门店排查到店、试驾和销售跟进质量。",
        ]},
        {"type": "followups", "items": ["把这些客户按销售负责人分组", "帮我生成客户跟进话术", "继续分析下降客户的产品结构变化"]},
    ]
    return block_response(
        intent="attribution_analysis",
        skill="attribution_analysis",
        answer=answer,
        blocks=blocks,
        debug={"sql": sql, "reason": "筛选本月较上月消耗下降超过 20% 的客户，并拆解流量、线索、转化、效果指标变化。"},
        sql=sql,
        reason="筛选本月较上月消耗下降超过 20% 的客户，并拆解流量、线索、转化、效果指标变化。",
        columns=columns,
        rows=enriched,
    )


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
    requested_skill = str(payload.get("skill", "auto") or "auto").strip()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else None
    if not question:
        raise ValueError("请输入问题")

    if requested_skill in ("", "auto"):
        route = detect_intent(question)
    elif requested_skill in SUPPORTED_SKILLS:
        route = {
            "intent": "manual_select",
            "skill": requested_skill,
            "requires_data": requested_skill != "general_chat",
            "confidence": 1.0,
            "forced": True,
        }
    else:
        raise ValueError(f"不支持的技能：{requested_skill}")

    skill = route["skill"]
    if skill == "general_chat":
        result = general_chat_skill(question, history if isinstance(history, list) else [])
    elif skill == "attribution_analysis":
        result = attribution_analysis_skill(question, history if isinstance(history, list) else [])
    elif skill == "sales_weekly_report":
        result = sales_weekly_report_skill(question, history if isinstance(history, list) else [])
    else:
        result = sql_query_skill(question, history if isinstance(history, list) else [], context)
    result["intent"] = route["intent"]
    result["skill"] = skill
    result["route"] = route
    return result


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
