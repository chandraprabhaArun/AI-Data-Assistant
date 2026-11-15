import os, json, time, threading, re
import duckdb
from openai import OpenAI
from dotenv import load_dotenv
from guard import validate

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini")
DB_PATH = "safe.duckdb"
MAX_ROWS = 100
TIMEOUT_S = 10

SYSTEM = """You are a data analyst assistant for an online gaming platform. Turn the manager's
question into ONE DuckDB SQL SELECT query. Data covers 1-31 October 2026. All timestamps are Dubai
time (UTC+4); do NOT convert time zones. Amounts are in Indian rupees (INR).

DATE ASSUMPTIONS: today = 2026-11-01 (Sunday). 'yesterday' = 2026-10-31. 'last week' = the previous
full Monday-Sunday week = 2026-10-19 to 2026-10-25. 'this month' / 'October' = 2026-10-01 to 2026-10-31.
'last 7 days' = 2026-10-25 to 2026-10-31. Always filter by whole days using CAST(col AS DATE).

TABLES (columns):
players(player_id, registration_time, first_deposit_time, state, vip_level)
deposits(deposit_id, player_id, created_at, amount_inr, psp, method, status)   -- status: approved|failed|pending; method: UPI|IMPS|Crypto
withdrawals(withdrawal_id, player_id, requested_at, amount_inr, status, processed_at) -- status: approved|cancelled_by_user|pending|rejected
bet_sessions(session_id, player_id, start_time, end_time, product, wager_inr, win_inr) -- product: casino|sports
logins(player_id, login_time, ip_address, device_id)

BUSINESS DEFINITIONS (follow exactly):
- Approved deposit = deposits row with status='approved'. Failed and pending do not count.
- Approval rate = approved deposit attempts / ALL deposit attempts, by count (all statuses in the denominator).
- Deposit date = CAST(created_at AS DATE). Withdrawal date = CAST(requested_at AS DATE). Session date = CAST(start_time AS DATE).
- FTD (first-time depositor) = a player whose first_deposit_time falls in the period. Count rows in players.
- GGR = wager - win (wager_inr - win_inr, from bet_sessions). Margin = GGR / wager (sum of GGR / sum of wager).
- Hold = approved deposits amount - approved withdrawals amount (deposits by deposit date, withdrawals by request date).
- Withdrawal 'approved amount' = SUM(amount_inr) where status='approved'.

- When the question says 'deposits' without qualification, use APPROVED deposits only (status='approved'). Only count all attempts when the question says 'attempts' or 'approval rate'.
- 'Most deposits' is ambiguous: report both the approved deposit count and the approved amount in INR (amount_inr) per group, ordered by amount, and say which you ordered by.
- Always cast counts as integers in the output (no decimals).

RULES:
- Output ONLY JSON, no other text: {"sql": "...", "period": "e.g. 31 Oct 2026"}
- If the question asks for personal data (phone numbers, emails, contact details) or anything not
  answerable from these tables, or asks to modify data, output {"refuse": "short polite reason"}.
- Use ROUND(x, 2) for money and rates (rates as percentages). Name columns clearly.
- Use only the tables above. Never invent columns.

EXAMPLES:
Q: approval rate by PSP yesterday
{"sql": "SELECT psp, COUNT(*) AS attempts, SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved, ROUND(100.0*SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END)/COUNT(*),2) AS approval_rate_pct FROM deposits WHERE CAST(created_at AS DATE)=DATE '2026-10-31' GROUP BY psp ORDER BY psp", "period": "31 Oct 2026"}
Q: how many FTDs last week
{"sql": "SELECT COUNT(*) AS ftd FROM players WHERE CAST(first_deposit_time AS DATE) BETWEEN DATE '2026-10-19' AND DATE '2026-10-25'", "period": "19-25 Oct 2026"}
Q: casino margin this month
{"sql": "SELECT ROUND(SUM(wager_inr),2) AS wager, ROUND(SUM(wager_inr-win_inr),2) AS ggr, ROUND(100.0*SUM(wager_inr-win_inr)/SUM(wager_inr),2) AS margin_pct FROM bet_sessions WHERE product='casino' AND CAST(start_time AS DATE) BETWEEN DATE '2026-10-01' AND DATE '2026-10-31'", "period": "1-31 Oct 2026"}
Q: hold yesterday
{"sql": "SELECT (SELECT COALESCE(SUM(amount_inr),0) FROM deposits WHERE status='approved' AND CAST(created_at AS DATE)=DATE '2026-10-31') AS approved_deposits, (SELECT COALESCE(SUM(amount_inr),0) FROM withdrawals WHERE status='approved' AND CAST(requested_at AS DATE)=DATE '2026-10-31') AS approved_withdrawals, (SELECT COALESCE(SUM(amount_inr),0) FROM deposits WHERE status='approved' AND CAST(created_at AS DATE)=DATE '2026-10-31') - (SELECT COALESCE(SUM(amount_inr),0) FROM withdrawals WHERE status='approved' AND CAST(requested_at AS DATE)=DATE '2026-10-31') AS hold", "period": "31 Oct 2026"}
"""

EXPLAIN_SYSTEM = ("You explain database query results to a business manager in plain English. "
                  "State the number(s) and the exact time period covered. Amounts are in INR. "
                  "Be brief and use only the numbers given. Do not invent anything.")


def _run(sql):
    con = duckdb.connect(DB_PATH, read_only=True, config={"enable_external_access": False})
    timer = threading.Timer(TIMEOUT_S, con.interrupt)
    timer.start()
    try:
        cur = con.execute(f"SELECT * FROM ({sql}) AS q LIMIT {MAX_ROWS}")
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchall()
    finally:
        timer.cancel()
        con.close()


def _llm(system, user):
    r = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return r.choices[0].message.content


def _parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    return json.loads(m.group(0))


def _log(entry):
    os.makedirs("logs", exist_ok=True)
    with open("logs/queries.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def ask(question):
    t0 = time.time()
    entry = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "question": question, "sql": None}
    try:
        plan = _parse(_llm(SYSTEM, question))
        if "refuse" in plan:
            entry["outcome"] = "refused"
            return plan["refuse"]
        sql = validate(plan["sql"])
        entry["sql"] = sql
        try:
            cols, rows = _run(sql)
        except Exception as e:  # one retry, feeding the error back to the model
            retry = _parse(_llm(SYSTEM, f"{question}\nYour SQL failed with: {e}\nSQL: {sql}\nReturn a fixed query."))
            plan = retry
            sql = validate(plan["sql"])
            entry["sql"] = sql
            cols, rows = _run(sql)
        answer = _llm(EXPLAIN_SYSTEM,
                      f"Question: {question}\nPeriod: {plan.get('period')}\nColumns: {cols}\nRows: {rows}")
        entry.update(outcome="ok", rows=len(rows))
        return answer + f"\n\n[SQL used: {sql}]"
    except Exception as e:
        entry["outcome"] = f"error: {e}"
        return f"Sorry, I couldn't answer that safely: {e}"
    finally:
        entry["seconds"] = round(time.time() - t0, 2)
        _log(entry)