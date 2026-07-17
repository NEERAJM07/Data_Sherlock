"""
sql_engine.py

Sprint 5 - Natural Language -> SQL.

Takes a plain-English question about the currently loaded dataset,
asks Gemini to translate it into a single DuckDB SQL query against a
table called `df`, then executes that query with DuckDB directly on
the in-memory pandas DataFrame (no separate database needed) and
returns both the generated SQL and the result as a DataFrame.

Safety: only SELECT / WITH (CTE) statements are executed. Anything
that looks like it would mutate data (INSERT/UPDATE/DELETE/DROP/
ALTER/CREATE/ATTACH/COPY/PRAGMA etc.) is rejected before it ever
reaches DuckDB, since the SQL text comes from an LLM and is
effectively untrusted input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from ai_service import _get_client, AIServiceError, DEFAULT_MODEL

# Statement types we refuse to run, since the SQL is LLM-generated and
# this tool should only ever be able to read the uploaded data, never
# modify it or touch the filesystem / other databases.
_BLOCKED_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "ATTACH", "DETACH", "COPY", "PRAGMA", "EXPORT", "IMPORT",
    "INSTALL", "LOAD", "CALL", "VACUUM", "TRUNCATE",
)


class SQLEngineError(Exception):
    """Raised when a natural-language question can't be turned into a
    safe, runnable SQL query, or when running it fails."""


@dataclass
class SQLQueryResult:
    sql: str
    result: pd.DataFrame


def _schema_description(df: pd.DataFrame) -> str:
    lines = [f"- {col} ({str(dtype)})" for col, dtype in df.dtypes.items()]
    return "\n".join(lines)


def _build_prompt(nl_query: str, df: pd.DataFrame) -> str:
    return f"""You are a SQL generator for DuckDB. The user has a table
named `df` with this schema:

{_schema_description(df)}

Write a single DuckDB SQL SELECT statement that answers the following
question. Respond with ONLY the raw SQL, no explanation, no markdown
code fences, no trailing semicolon commentary. The query must be a
read-only SELECT (or a WITH ... SELECT), must reference the table as
`df`, and must not modify any data.

Question: {nl_query}
"""


def _clean_sql(raw_text: str) -> str:
    """Strips markdown code fences and surrounding whitespace/semicolons
    that models commonly add even when told not to."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text)
    return text.strip().rstrip(";").strip()


def _validate_sql(sql: str) -> None:
    if not sql:
        raise SQLEngineError("Gemini returned an empty SQL query.")

    first_word = sql.strip().split(None, 1)[0].upper()
    if first_word not in ("SELECT", "WITH"):
        raise SQLEngineError(
            "Generated query isn't a SELECT/WITH statement, so it was "
            "blocked for safety. Try rephrasing your question."
        )

    upper_sql = sql.upper()
    for keyword in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise SQLEngineError(
                f"Generated query contains a blocked keyword ({keyword}) "
                "and was not executed for safety. Try rephrasing your "
                "question."
            )


def generate_sql(
    nl_query: str,
    df: pd.DataFrame,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Asks Gemini to translate a natural-language question into a
    DuckDB SQL query against a table called `df`. Returns cleaned SQL
    text. Raises SQLEngineError if generation fails or the result
    doesn't look like a safe read-only query."""

    client = _get_client(api_key)
    prompt = _build_prompt(nl_query, df)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except Exception as exc:  # noqa: BLE001 - surface any API error to the UI
        raise SQLEngineError(f"Gemini request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise SQLEngineError("Gemini returned an empty response.")

    sql = _clean_sql(text)
    _validate_sql(sql)
    return sql


def run_sql(sql: str, df: pd.DataFrame) -> pd.DataFrame:
    """Executes a validated SQL query with DuckDB directly against the
    given DataFrame (registered as `df`). Raises SQLEngineError on any
    execution failure (bad column name, syntax issue, etc.)."""

    try:
        import duckdb
    except ImportError as exc:
        raise SQLEngineError(
            "The 'duckdb' package isn't installed. Run: pip install duckdb"
        ) from exc

    _validate_sql(sql)

    try:
        con = duckdb.connect(database=":memory:")
        con.register("df", df)
        result = con.execute(sql).df()
        con.close()
        return result
    except Exception as exc:  # noqa: BLE001 - surface any DuckDB error to the UI
        raise SQLEngineError(f"DuckDB couldn't run that query: {exc}") from exc


def ask_dataset(
    nl_query: str,
    df: pd.DataFrame,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> SQLQueryResult:
    """Main entry point used by app.py: natural language in, generated
    SQL + result DataFrame out."""

    sql = generate_sql(nl_query, df, api_key=api_key, model=model)
    result = run_sql(sql, df)
    return SQLQueryResult(sql=sql, result=result)
