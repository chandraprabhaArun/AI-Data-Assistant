import re

FORBIDDEN = (r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|"
             r"pragma|call|install|load|set|truncate|replace|vacuum|checkpoint|"
             r"read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|glob|"
             r"information_schema|duckdb_\w+|pragma_\w+|sqlite_\w+)\b")
BLOCKED_COLS = r"\b(phone|email)\b"


def validate(sql: str) -> str:
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise ValueError("Only a single statement is allowed.")
    low = s.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise ValueError("Only SELECT queries are allowed.")
    if re.search(FORBIDDEN, low):
        raise ValueError("Query contains a forbidden keyword.")
    if re.search(BLOCKED_COLS, low):
        raise ValueError("Personal data columns are not available.")
    return s