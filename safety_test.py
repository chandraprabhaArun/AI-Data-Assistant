import duckdb
from guard import validate

print("--- Guard tests (should all be blocked) ---")
for q in ["DROP TABLE deposits", "DELETE FROM deposits", "SELECT phone FROM players",
          "SELECT 1; DROP TABLE players", "SELECT * FROM read_csv_auto('data/players.csv')"]:
    try:
        validate(q)
        print("NOT BLOCKED:", q)
    except ValueError as e:
        print("blocked:", q, "->", e)

print("\n--- Database tests ---")
con = duckdb.connect("safe.duckdb", read_only=True, config={"enable_external_access": False})
print("players columns:", [c[0] for c in con.execute("DESCRIBE players").fetchall()])
for q in ["DELETE FROM deposits", "SELECT phone FROM players",
          "SELECT * FROM read_csv_auto('data/players.csv')"]:
    try:
        con.execute(q)
        print("NOT BLOCKED:", q)
    except Exception as e:
        print("blocked:", q, "->", str(e)[:80])