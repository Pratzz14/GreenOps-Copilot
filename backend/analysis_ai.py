"""Generate a SQL draft from the selected schema and a natural-language question."""
import json
import os
from pathlib import Path

import httpx
from dotenv import dotenv_values
from pydantic import BaseModel, Field

from backend.analysis_engine import SCALARS

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
KEY_REQUIRED = "Add OPENAI_API_KEY to the project’s .env file or set it in the backend environment."


class DraftError(ValueError):
    pass


class Draft(BaseModel):
    dataset: str | None = Field(max_length=100)
    sql: str | None = Field(max_length=30_000)
    explanation: str = Field(max_length=1500)


def settings():
    local = dotenv_values(ENV_FILE, interpolate=False)
    key = os.environ.get("OPENAI_API_KEY") or local.get("OPENAI_API_KEY") or ""
    model = os.environ.get("OPENAI_ANALYSIS_MODEL") or local.get("OPENAI_ANALYSIS_MODEL") or "gpt-4.1-mini"
    return key.strip(), model.strip()


def configured():
    return bool(settings()[0])


def generate_draft(question, datasets, scope):
    key, model = settings()
    if not key:
        raise DraftError(KEY_REQUIRED)

    context = json.dumps({"datasets": datasets, "scope": scope, "question": question}, ensure_ascii=False)
    instructions = (
        "Choose the single Silver dataset that best answers the analyst's question and return its exact name. Use only its listed fields. Prefer prepared datasets for questions that need their verified joins. Use cost_facts for overall cost to avoid double counting. Draft read-only DuckDB SQL. "
        "Allow one SELECT with non-recursive CTEs or subqueries. Never use joins, UNION, window functions, "
        "file readers, table functions, system tables, or additional statements. "
        f"The approved functions are {', '.join(sorted(SCALARS))}. SQL aggregate FILTER is also supported. "
        "Use explicit result columns and readable formatting. Apply the metadata's row grain, units, and limitations. "
        "The API already applies the requested period, disposition, and financial scope before the query. "
        "Do not add predicates that restate this scope unless the question asks for a narrower subset. "
        "Preserve complete overlapping baseline weeks. Keep missing costs NULL; when relevant expose missing-cost "
        "coverage alongside CHF totals. Use NULLIF for division. If no listed dataset can answer the question, "
        "return null dataset and SQL and explain what information is needed. Otherwise briefly explain what the SQL measures."
    )
    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}"},
            timeout=httpx.Timeout(30, connect=5),
            json={
                "model": model,
                "instructions": instructions,
                "input": context,
                "store": False,
                "max_output_tokens": 1500,
                "text": {"format": {
                    "type": "json_schema", "name": "silver_sql_draft", "strict": True,
                    "schema": {
                        "type": "object", "additionalProperties": False, "required": ["dataset", "sql", "explanation"],
                        "properties": {"dataset": {"type": ["string", "null"]}, "sql": {"type": ["string", "null"]}, "explanation": {"type": "string"}},
                    },
                }},
            },
        )
    except httpx.RequestError as error:
        raise DraftError("Could not reach OpenAI. Check the backend connection and try again.") from error
    if response.status_code in (401, 403):
        raise DraftError("OpenAI rejected the credentials or model access. Check the backend configuration.")
    if response.status_code == 429:
        raise DraftError("OpenAI reported a rate or quota limit. Check the project usage or try again later.")
    if response.is_error:
        raise DraftError(f"OpenAI could not draft the query (HTTP {response.status_code}). Check the configured model and try again.")
    try:
        body = response.json()
        if body.get("status") != "completed":
            raise DraftError("OpenAI did not complete the draft. Try a narrower question.")
        for item in body["output"]:
            if item.get("type") != "message":
                continue
            for part in item["content"]:
                if part.get("type") == "refusal":
                    raise DraftError("OpenAI declined to draft this query. Try rephrasing the question.")
                if part.get("type") == "output_text":
                    return Draft.model_validate_json(part["text"])
    except DraftError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError) as error:
        raise DraftError("OpenAI returned an unreadable draft. Try again.") from error
    raise DraftError("OpenAI returned no draft. Try rephrasing the question.")
