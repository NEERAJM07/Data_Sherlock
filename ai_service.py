"""
ai_service.py

Generates AI-powered insights about an uploaded dataset using Google's
Gemini API (google-genai SDK). Given the profiling / validation output
already computed elsewhere in the app, it asks Gemini for:

  1. A short plain-English summary of the dataset
  2. The key data quality issues worth calling out
  3. Concrete recommendations to fix / improve the data

The API key is read from (in priority order):
  1. An explicit `api_key` argument (e.g. from a Streamlit sidebar input)
  2. The GEMINI_API_KEY environment variable, loaded from a local .env
     file via python-dotenv -- this works even on machines where you
     can't set system-wide environment variables, since python-dotenv
     just reads a text file in the project folder.

No API key -> functions raise AIServiceError with a clear message, so
the UI layer can show it instead of crashing.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Loads variables from a .env file placed in the project root, if present.
# This does NOT touch system/OS environment variables, so it works even
# on machines where you can't change env vars (e.g. a locked-down office
# laptop) -- you just create a .env file in the project folder instead.
#
# We point load_dotenv() at an explicit path (the folder this file lives
# in) rather than calling load_dotenv() with no arguments. The no-argument
# form searches for .env by walking up from the caller's stack frame, and
# that search can fail under Streamlit -- Streamlit runs app.py through
# its own internal exec()-based runner rather than a normal script
# invocation, which throws off dotenv's automatic detection even when
# .env is sitting right there in the project root.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

DEFAULT_MODEL = "gemini-3.5-flash"


class AIServiceError(Exception):
    """Raised when AI insight generation can't be completed."""


@dataclass
class AIInsights:
    summary: str = ""
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_text: str = ""


def _get_api_key(api_key: str | None = None) -> str:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise AIServiceError(
            "No Gemini API key found. Set GEMINI_API_KEY in a .env file "
            "in the project root, or enter a key in the sidebar."
        )
    return key


def _get_client(api_key: str | None = None):
    try:
        from google import genai
    except ImportError as exc:
        raise AIServiceError(
            "The 'google-genai' package isn't installed. Run: "
            "pip install google-genai"
        ) from exc

    return genai.Client(api_key=_get_api_key(api_key))


def _build_prompt(
    df: pd.DataFrame,
    metrics: dict,
    profile_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> str:
    """Builds a compact, token-efficient prompt from already-computed
    profiling/validation output rather than dumping the raw dataframe,
    which keeps the request small and cheap even for large datasets."""

    column_lines = []
    for _, row in profile_df.iterrows():
        column_lines.append(
            f"- {row['Column']} ({row['Datatype']}): "
            f"{row['Null %']}% null, {row['Unique Values']} unique values"
        )
    column_summary = "\n".join(column_lines)

    if not validation_df.empty:
        validation_lines = [
            f"- [{row['Status']}] {row['Rule']} on {row['Column']}: "
            f"{row['Description']}"
            for _, row in validation_df.iterrows()
        ]
    else:
        validation_lines = ["- No validation results available"]
    validation_summary = "\n".join(validation_lines)

    return f"""You are a senior data engineer reviewing a dataset that a
user just uploaded to a data quality tool. Based only on the metadata
below (not the raw data), respond in EXACTLY this format with no extra
commentary:

SUMMARY:
<2-3 sentences describing what this dataset likely represents and its
overall shape/quality>

ISSUES:
- <issue 1>
- <issue 2>
(one bullet per notable issue, most important first; omit section if none)

RECOMMENDATIONS:
- <recommendation 1>
- <recommendation 2>
(one bullet per actionable recommendation; omit section if none)

DATASET METADATA
Rows: {metrics['rows']}
Columns: {metrics['columns']}
Total null cells: {metrics['nulls']}
Duplicate rows: {metrics['duplicates']}
Quality score: {metrics['quality_score']}%

COLUMN PROFILE
{column_summary}

VALIDATION RESULTS
{validation_summary}
"""


def _parse_response(text: str) -> AIInsights:
    """Parses the SUMMARY / ISSUES / RECOMMENDATIONS sections out of the
    model's plain-text response. Falls back gracefully if the model
    doesn't follow the format exactly."""

    def _section(name: str, stop_names: list[str]) -> str:
        stop_pattern = "|".join(stop_names)
        pattern = rf"{name}:\s*(.*?)(?=(?:{stop_pattern}):|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    summary_text = _section("SUMMARY", ["ISSUES", "RECOMMENDATIONS"])
    issues_text = _section("ISSUES", ["RECOMMENDATIONS", "SUMMARY"])
    recommendations_text = _section("RECOMMENDATIONS", ["SUMMARY", "ISSUES"])

    def _bullets(block: str) -> list[str]:
        lines = []
        for line in block.splitlines():
            line = line.strip().lstrip("-•").strip()
            if line:
                lines.append(line)
        return lines

    summary = summary_text if summary_text else text.strip()

    return AIInsights(
        summary=summary,
        issues=_bullets(issues_text),
        recommendations=_bullets(recommendations_text),
        raw_text=text,
    )


def generate_ai_insights(
    df: pd.DataFrame,
    metrics: dict,
    profile_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> AIInsights:
    """Main entry point used by app.py. Raises AIServiceError on any
    failure (missing key, missing package, API error) with a message
    that's safe to show directly in the Streamlit UI."""

    client = _get_client(api_key)
    prompt = _build_prompt(df, metrics, profile_df, validation_df)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except Exception as exc:  # noqa: BLE001 - surface any API error to the UI
        raise AIServiceError(f"Gemini request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise AIServiceError("Gemini returned an empty response.")

    return _parse_response(text)