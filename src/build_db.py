import duckdb, os

if os.path.exists("safe.duckdb"):
    os.remove("safe.duckdb")
con = duckdb.connect("safe.duckdb")

# Personal data (phone, email) is dropped here, so it does not exist for the assistant.
con.execute("""CREATE TABLE players AS
    SELECT * EXCLUDE (phone, email) FROM read_csv_auto('data/players.csv')""")
for t in ["deposits", "withdrawals", "bet_sessions", "logins"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")

print(con.sql("DESCRIBE players").df()[["column_name"]].T.to_string())
for t in ["players", "deposits", "withdrawals", "bet_sessions", "logins"]:
    print(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
con.close()
print("safe.duckdb built (no phone/email)")
