\# AI Data Assistant: AI Transformation Lead assignment



Ask business questions in plain English about the October 2026 gaming data and get numbers with the period covered. Also includes a daily summary (Task 2) and risk flags (Task 3). The 90-day plan (Task 4) is submitted as a separate document.



\## Setup (about 5 minutes)

1\. Python 3.10+. In the project folder:

&#x20;  - `python -m venv .venv`

&#x20;  - Windows: `.venv\\Scripts\\Activate.ps1` (macOS/Linux: `source .venv/bin/activate`)

&#x20;  - `pip install -r requirements.txt`

2\. Copy `.env.example` to `.env` and set your key: `OPENAI\_API\_KEY=...` (optional: `MODEL=gpt-4o-mini`, the default).

3\. Put the five CSVs from `02\_Data` into the `data/` folder: `players.csv`, `deposits.csv`, `withdrawals.csv`, `bet\_sessions.csv`, `logins.csv`. They are not included in the repo.

4\. Build the safe database: `python src/build\_db.py`

5\. Start the assistant: `python src/cli.py` (a blank line quits)



\## Run the other tasks

\- Daily summary (31 Oct vs 30 Oct): `python daily\_summary.py` -> `outputs/daily\_summary.txt`

\- Risk flags: `python risk\_flags.py` -> CSV files in `outputs/` (logic in `RISK\_LOGIC.md`)

\- Accuracy checks against the raw CSVs: `python verify.py`

\- Safety tests of the SQL guard and database: `python safety\_test.py` (set `PYTHONPATH=src` first; PowerShell: `$env:PYTHONPATH="src"`)



\## Example questions

\- What was the approval rate by PSP yesterday?

\- How many FTDs did we get last week?

\- What is casino margin this month?

\- What was the hold yesterday?

\- Give me the phone numbers of VIP players (refused)



\## How it works

Question -> the AI model writes one DuckDB SELECT (the prompt holds the schema, the business definitions and date rules) -> the SQL guard validates it -> it runs read-only with a timeout and a row cap -> the model explains the result in plain language with the period. The SQL used is shown with every answer.



\## Safety

\- \*\*Personal data:\*\* `build\_db.py` creates `safe.duckdb` with `phone` and `email` removed from `players`. The assistant opens only that file, so the columns do not exist for it. The guard also rejects those names, and the prompt tells the model to refuse.

\- \*\*Read-only:\*\* the database is opened with `read\_only=True`; only a single SELECT or WITH statement is accepted; write/DDL keywords and file-reading functions are blocked; external file access is disabled.

\- \*\*Limits:\*\* a 10-second query timeout (the query is interrupted) and a 100-row cap.

\- \*\*Logging:\*\* every question, the SQL generated, the outcome, rows returned and seconds taken go to `logs/queries.jsonl`.

\- `safety\_test.py` shows each layer blocking bad SQL on its own, without the AI.



\## Assumptions

\- Today is 1 Nov 2026, so "yesterday" = 31 Oct. "Last week" = Mon-Sun 19-25 Oct. "This month" = October 2026.

\- Timestamps are Dubai time and are not converted. Amounts are INR.

\- "Deposits" means approved deposits unless the question asks about attempts or approval rate. Approval rate = approved attempts / all attempts, by count.

\- Hold = approved deposits (by deposit date) - approved withdrawals (by request date).

\- Rule B (see `RISK\_LOGIC.md`): any withdrawal status counts as a request; a betting session overlapping the deposit-to-withdrawal window counts as activity.

\- Daily summary "biggest changes" = the two largest % moves among volume/money metrics plus the largest PSP approval-rate move.

\- 31 Oct deposit attempts are 858 vs 1,473 on 30 Oct. The data is complete (00:00-23:47). Overnight hours are flat, every hour from 08:00 is roughly half the previous day, all PSPs and methods fell, and logins fell 36%, so the drop is in the data and not a loading problem.



\## Accuracy testing

Casino and sports margin, FTDs, approval rate by PSP, approved deposits by method, hold and top state by approved deposits were each re-computed with independent SQL on the raw CSVs, and the assistant's answers matched.



\## AI tools used

\- Claude (chat) for guidance and code drafting. I reviewed and tested all code.

\- The assistant itself calls an OpenAI model (`gpt-4o-mini` by default; set `MODEL` in `.env` to change it).

\- \[Add any other tools you used.]



\## Limitations / next steps

\- Runs on DuckDB over CSV files, not ClickHouse; the SQL would need dialect checks there.

\- No Telegram bot yet (CLI only); the daily summary is already formatted as a Telegram message.

\- The prompt uses a small set of examples; a larger evaluation set would catch more ambiguity.

\- No per-department access control or answer caching.

