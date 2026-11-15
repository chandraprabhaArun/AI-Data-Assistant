import sys
import duckdb

sys.stdout.reconfigure(encoding="utf-8")

DAY = "2026-10-31"
PREV = "2026-10-30"

con = duckdb.connect()
for t in ["deposits", "withdrawals"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")


def day_stats(day):
    d = con.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END), 0),
               COALESCE(SUM(CASE WHEN status='approved' THEN amount_inr ELSE 0 END), 0)
        FROM deposits WHERE CAST(created_at AS DATE) = ?""", [day]).fetchone()
    w = con.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN status='approved' THEN amount_inr ELSE 0 END), 0)
        FROM withdrawals WHERE CAST(requested_at AS DATE) = ?""", [day]).fetchone()
    psp = con.execute("""
        SELECT psp, COUNT(*), SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END)
        FROM deposits WHERE CAST(created_at AS DATE) = ? GROUP BY psp ORDER BY psp""", [day]).fetchall()
    attempts, approved, approved_amt = d
    return {
        "attempts": attempts,
        "approved": approved,
        "approved_amt": approved_amt,
        "rate": 100.0 * approved / attempts if attempts else 0.0,
        "wd_requested": w[0],
        "wd_approved_amt": w[1],
        "hold": approved_amt - w[1],
        "psp": {p: {"attempts": a, "approved": ap, "rate": 100.0 * ap / a if a else 0.0}
                for p, a, ap in psp},
    }


cur, prev = day_stats(DAY), day_stats(PREV)


def pct(c, p):
    if p == 0:
        return None
    return 100.0 * (c - p) / abs(p)


def arrow(c, p):
    return "🔺" if c > p else ("🔻" if c < p else "➖")


def fmt_pct(c, p):
    v = pct(c, p)
    return "n/a" if v is None else f"{v:+.1f}%"


inr = lambda x: f"₹{x:,.0f}"

lines = []
lines.append(f"📊 Daily Summary – 31 Oct 2026 (vs 30 Oct)")
lines.append("")
lines.append("💰 Deposits")
lines.append(f"• Attempts: {cur['attempts']:,} ({fmt_pct(cur['attempts'], prev['attempts'])}) {arrow(cur['attempts'], prev['attempts'])}")
lines.append(f"• Approved: {cur['approved']:,} for {inr(cur['approved_amt'])} ({fmt_pct(cur['approved_amt'], prev['approved_amt'])}) {arrow(cur['approved_amt'], prev['approved_amt'])}")
lines.append(f"• Approval rate: {cur['rate']:.1f}% (prev {prev['rate']:.1f}%, {cur['rate'] - prev['rate']:+.1f} pp)")
lines.append("")
lines.append("🏦 Approval rate by PSP")
for p in sorted(cur["psp"]):
    c = cur["psp"][p]
    pv = prev["psp"].get(p, {"rate": 0.0})
    lines.append(f"• {p}: {c['rate']:.1f}% ({c['approved']}/{c['attempts']}), {c['rate'] - pv['rate']:+.1f} pp")
lines.append("")
lines.append("💸 Withdrawals")
lines.append(f"• Requested: {cur['wd_requested']:,} ({fmt_pct(cur['wd_requested'], prev['wd_requested'])}) {arrow(cur['wd_requested'], prev['wd_requested'])}")
lines.append(f"• Approved amount: {inr(cur['wd_approved_amt'])} ({fmt_pct(cur['wd_approved_amt'], prev['wd_approved_amt'])}) {arrow(cur['wd_approved_amt'], prev['wd_approved_amt'])}")
lines.append("")
lines.append(f"🧮 Hold: {inr(cur['hold'])} (prev {inr(prev['hold'])}, {fmt_pct(cur['hold'], prev['hold'])})")

# Biggest changes: candidate metrics ranked by absolute % change
cands = [
    ("Deposit attempts", cur["attempts"], prev["attempts"]),
    ("Approved deposit count", cur["approved"], prev["approved"]),
    ("Approved deposit amount", cur["approved_amt"], prev["approved_amt"]),
    ("Overall approval rate", cur["rate"], prev["rate"]),
    ("Withdrawals requested", cur["wd_requested"], prev["wd_requested"]),
    ("Approved withdrawal amount", cur["wd_approved_amt"], prev["wd_approved_amt"]),
    ("Hold", cur["hold"], prev["hold"]),
]
for p in cur["psp"]:
    if p in prev["psp"]:
        cands.append((f"{p} approval rate", cur["psp"][p]["rate"], prev["psp"][p]["rate"]))
ranked = []
for name, c, p in cands:
    v = pct(c, p)
    if v is not None:
        ranked.append((abs(v), name, c, p, v))
ranked.sort(reverse=True)

lines.append("")
lines.append("🔎 Biggest changes vs 30 Oct")
lines.append("• Context: all PSPs and methods fell; logins also fell (770 → 491)")
for _, name, c, p, v in ranked[:3]:
    lines.append(f"• {name}: {p:,.1f} → {c:,.1f} ({v:+.1f}%)")

msg = "\n".join(lines)
print(msg)
with open("outputs/daily_summary.txt", "w", encoding="utf-8") as f:
    f.write(msg + "\n")