\# Risk flag logic



Source: raw CSVs (October 2026, Dubai time). Scripts: `risk\_flags.py`. Outputs in `outputs/`.



\## Rule A: shared IP

\- Group October logins by `ip\_address`; flag IPs used by 3 or more distinct `player\_id`.

\- Result: 6 IPs, 25 players (largest: 7 players on one IP).

\- Files: `rule\_a\_shared\_ip\_summary.csv` (one row per IP), `rule\_a\_flagged\_players.csv` (player to IP).

\- Caveat: shared IPs can be legitimate (family, office, mobile carrier NAT). Flags are for review, not proof of fraud.



\## Rule B: deposit and withdraw without playing

\- For each deposit with `status = approved`, find withdrawal requests by the same player with

&#x20; `requested\_at` from the deposit time up to 60 minutes later (inclusive).

\- Exclude the pair if any betting session overlaps the window: `start\_time <= withdrawal time`

&#x20; and `end\_time >= deposit time`. A session already running when the deposit happened therefore

&#x20; counts as betting activity.

\- Withdrawals of any status are included, because the rule says withdrawal request.

\- One deposit followed by several withdrawals yields several rows (one per pair).

\- Result: 109 pairs across 107 players (649 pairs fall in the 60-minute window before the betting check).

\- File: `rule\_b\_deposit\_withdraw\_no\_play.csv`.

\- Assumptions: timestamps are minute-level; a session starting in the same minute as the

&#x20; withdrawal counts as activity.



\## Verification

\- Rule A re-checked with a separate query (same 6 IPs).

\- Rule B spot-checked on individual player timelines (deposits, withdrawals, sessions side by side).

