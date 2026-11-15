import duckdb

con = duckdb.connect()
for t in ["deposits", "withdrawals", "bet_sessions", "logins"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")

# Rule A: IP used by 3+ different players in October
con.execute("""
    CREATE TABLE rule_a_ips AS
    SELECT ip_address,
           COUNT(DISTINCT player_id) AS distinct_players,
           COUNT(*) AS login_count,
           string_agg(DISTINCT player_id, ';' ORDER BY player_id) AS players
    FROM logins
    WHERE login_time >= '2026-10-01' AND login_time < '2026-11-01'
    GROUP BY ip_address
    HAVING COUNT(DISTINCT player_id) >= 3
    ORDER BY distinct_players DESC, ip_address
""")
con.execute("COPY rule_a_ips TO 'outputs/rule_a_shared_ip_summary.csv' (HEADER, DELIMITER ',')")

con.execute("""
    COPY (
        SELECT DISTINCT l.player_id, l.ip_address, r.distinct_players
        FROM logins l JOIN rule_a_ips r USING (ip_address)
        WHERE l.login_time >= '2026-10-01' AND l.login_time < '2026-11-01'
        ORDER BY r.distinct_players DESC, l.ip_address, l.player_id
    ) TO 'outputs/rule_a_flagged_players.csv' (HEADER, DELIMITER ',')
""")

# Rule B: approved deposit followed by a withdrawal request within 60 minutes,
# with no betting session overlapping the window [deposit time, withdrawal request time]
con.execute("""
    CREATE TABLE rule_b AS
    SELECT d.player_id, d.deposit_id, d.created_at AS deposit_time, d.amount_inr AS deposit_amount,
           w.withdrawal_id, w.requested_at AS withdrawal_time, w.amount_inr AS withdrawal_amount,
           w.status AS withdrawal_status,
           date_diff('minute', d.created_at, w.requested_at) AS minutes_gap
    FROM deposits d
    JOIN withdrawals w
      ON w.player_id = d.player_id
     AND w.requested_at >= d.created_at
     AND w.requested_at <= d.created_at + INTERVAL 60 MINUTE
    WHERE d.status = 'approved'
      AND NOT EXISTS (
          SELECT 1 FROM bet_sessions b
          WHERE b.player_id = d.player_id
            AND b.start_time <= w.requested_at
            AND b.end_time >= d.created_at
      )
    ORDER BY d.player_id, d.created_at
""")
con.execute("COPY rule_b TO 'outputs/rule_b_deposit_withdraw_no_play.csv' (HEADER, DELIMITER ',')")

print("Rule A: IPs flagged:", con.execute("SELECT COUNT(*) FROM rule_a_ips").fetchall()[0][0])
print("Rule A: players flagged:", con.execute(
    "SELECT COUNT(DISTINCT player_id) FROM read_csv_auto('outputs/rule_a_flagged_players.csv')").fetchall()[0][0])
print("Rule B: flagged deposit-withdrawal pairs:", con.execute("SELECT COUNT(*) FROM rule_b").fetchall()[0][0])
print("Rule B: distinct players:", con.execute("SELECT COUNT(DISTINCT player_id) FROM rule_b").fetchall()[0][0])
print(con.sql("SELECT * FROM rule_b LIMIT 5").df().to_string())
