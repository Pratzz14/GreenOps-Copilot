"""Generate and cache advisory review tags for a published recommendation catalog."""

import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.analysis_ai import settings
from src.gold_baseline import key_for

TagDecision = Literal["eligible", "human_review"]
logger = logging.getLogger(__name__)


class ReviewTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: TagDecision
    reason: Literal["dependency", "schedule", "contract", "estimate_coverage", "rule_eligibility"]
    evidence_id: str
    explanation: str | None = None


class GeneratedReviewTag(ReviewTag):
    explanation: str


class TagResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tags: list[GeneratedReviewTag] = Field(max_length=12)


def facts_for(item):
    measure = item["estimate"]
    facts = {"rule": {"category": item["category"], "status": item["rule_status"]}}
    if item["protection_evidence_ids"]:
        facts["protection"] = {"applicable_protections": len(item["protection_evidence_ids"])}
    if measure and any(any(row[field] is None for field in ("net_chf", "savings_kwh", "savings_location_kg"))
                       for row in measure["estimates"] if row["horizon"] == "steady_state"):
        facts["estimate"] = {"incomplete_savings": True}
    if measure and measure["notice_deadline"] is not None:
        days = (measure["notice_deadline"] - item["decision_as_of"]).days
        if 0 <= days <= 30:
            facts["notice"] = {"notice_days_remaining": days}
    facts["recurrence"] = {"observed": item["observed"], "qualifying": item["qualifying"],
                           "persistent_unused": item["persistent_unused"]}
    return {f"{item['id']}.{name}": value for name, value in facts.items()}


def evidence_version(item):
    return key_for("recommendation-tags-v1", facts_for(item), item["evidence"], item["next_check"])


def cache_path(output, run):
    return output / "recommendation-tags" / f"{run}.json"


def read_tags(output, run):
    try:
        data = json.loads(cache_path(output, run).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def verify_tag(item, tag):
    fact = facts_for(item).get(tag.evidence_id, {})
    if tag.decision == "eligible":
        return tag.reason == "rule_eligibility" and fact.get("status") == "eligible"
    if tag.reason == "estimate_coverage":
        return fact.get("incomplete_savings") is True
    if tag.reason == "contract" and "notice_days_remaining" in fact:
        return True
    if tag.reason in {"schedule", "dependency"} and "applicable_protections" in fact:
        return True
    expected = {"Licence": "contract", "Server": "dependency", "Data cluster": "schedule"}
    return fact.get("status") in {"human_review", "blocked"} and tag.reason == expected[item["category"]]


def cached_tag(item, saved):
    entry = saved.get(item["id"])
    if not isinstance(entry, dict) or entry.get("version") != evidence_version(item):
        return None
    try:
        tag = ReviewTag.model_validate(entry.get("tag"))
    except ValidationError:
        return None
    return tag if verify_tag(item, tag) else None


def final_status(rule, tag):
    if rule == "blocked":
        return rule
    return "human_review" if tag and tag.decision == "human_review" else rule


def request_tags(key, model, items):
    payload = [facts_for(item) for item in items]
    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {key}"},
        timeout=httpx.Timeout(30, connect=5),
        json={"model": model, "store": False, "input": json.dumps(payload),
              "instructions": (
                  "Return one review tag per item. Cite one exact evidence identifier from that item. "
                  "Include an explanation in one plain-English sentence of at most 200 characters. "
                  "Explain why the action merits consideration or needs review using only that item's facts. "
                  "Use recurring underuse or unused seats when relevant. Do not invent savings, protections, or deadlines. "
                  "Use human_review with estimate_coverage for incomplete_savings, or schedule/dependency for "
                  "applicable protections. Use human_review with contract if a notice deadline is within 30 days. "
                  "For a rule status of human_review or blocked, use contract for a "
                  "Licence, dependency for a Server, schedule for a Data cluster. Only use eligible with "
                  "rule_eligibility when the cited rule status is eligible and no concern is evidenced."
              ),
              "text": {"format": {"type": "json_schema", "name": "recommendation_tags", "strict": True,
                                  "schema": TagResponse.model_json_schema()}}},
    )
    response.raise_for_status()
    body = response.json()
    for message in body.get("output", []):
        for part in message.get("content", []):
            if part.get("type") == "output_text":
                return TagResponse.model_validate_json(part["text"]).tags
    return []


def enrich(output: Path, run: str, recommendations):
    key, default_model = settings()
    if not key:
        logger.warning("Recommendation tags unavailable because the OpenAI key is missing.")
        return 0
    model = os.environ.get("OPENAI_RECOMMENDATION_MODEL") or default_model
    path = cache_path(output, run)
    saved = read_tags(output, run)
    pending = []
    existing = {}
    for item in recommendations:
        tag = cached_tag(item, saved)
        if tag is None or not tag.explanation:
            pending.append(item)
            existing[item["id"]] = tag
    written = 0
    for offset in range(0, len(pending), 12):
        batch = {item["id"]: item for item in pending[offset:offset + 12]}
        try:
            tags = request_tags(key, model, list(batch.values()))
        except httpx.HTTPStatusError as error:
            logger.warning("Recommendation tagging stopped after OpenAI returned HTTP %d.", error.response.status_code)
            break
        except httpx.RequestError:
            logger.warning("Recommendation tagging stopped because OpenAI was unreachable.")
            break
        except (ValueError, KeyError, TypeError):
            logger.warning("Recommendation tagging stopped after an invalid OpenAI response.")
            break
        for tag in tags:
            identifier = tag.evidence_id.partition(".")[0]
            item = batch.get(identifier)
            if item and verify_tag(item, tag):
                explanation = tag.explanation.strip()
                if not explanation or len(explanation) > 200 or len(explanation.splitlines()) != 1:
                    if existing[identifier] is not None:
                        continue
                    explanation = None
                saved[identifier] = {"version": evidence_version(item),
                                     "tag": {**tag.model_dump(), "explanation": explanation}}
                written += 1
    if written:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({**read_tags(output, run), **saved}, handle)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return written
