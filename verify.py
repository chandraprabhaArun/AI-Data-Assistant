import duckdb

con = duckdb.connect()
for t in ["players", "deposits", "withdrawals", "bet_sessions", "logins"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")

print("1) Casino margin, October")
print(con.sql("""
    SELECT SUM(wager_inr) AS wager,
           SUM(wager_inr - win_inr) AS ggr,
           ROUND(100.0 * SUM(wager_inr - win_inr) / SUM(wager_inr), 2) AS margin_pct
    FROM bet_sessions
    WHERE product = 'casino'
""").df().to_string())

print("\n2) FTDs, 19-25 Oct")
print(con.sql("""
    SELECT COUNT(*) AS ftd
    FROM players
    WHERE first_deposit_time >= '2026-10-19' AND first_deposit_time < '2026-10-26'
""").df().to_string())

print("\n3) Approval rate by PSP, 31 Oct")
print(con.sql("""
    SELECT psp,
           COUNT(*) AS attempts,
           SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
           ROUND(100.0 * SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rate_pct
    FROM deposits
    WHERE created_at >= '2026-10-31' AND created_at < '2026-11-01'
    GROUP BY psp ORDER BY psp
""").df().to_string())