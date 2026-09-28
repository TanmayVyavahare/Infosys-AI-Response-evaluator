"""JSON validation for LLM responses.

Provides a shared helper that every evaluator uses to parse and validate
JSON output from LLMs, with retry and fallback logic.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Required fields in every evaluator JSON response
REQUIRED_FIELDS = {"score", "reason"}
OPTIONAL_FIELDS = {"evidence", "strengths", "weaknesses", "suggestions", "claims", "requirements"}


def extract_json_from_text(text: str) -> Optional[str]:
    """Extract JSON content from LLM response text.

    Handles cases where the LLM wraps JSON in markdown code blocks
    or includes extra text before/after the JSON object.

    Args:
        text: Raw LLM output text.

    Returns:
        Extracted JSON string, or None if no JSON found.
    """
    # Try to find JSON in markdown code blocks first
    code_block_match = re.search(
        r'```(?:json)?\s*\n?(.*?)\n?\s*```',
        text,
        re.DOTALL,
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try to find a JSON object directly
    # Look for the outermost { ... }
    brace_start = text.find("{")
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    for i in range(brace_start, len(text)):
        char = text[i]
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : i + 1]

    return None


def validate_llm_response(
    raw_text: str,
    metric_name: str,
) -> Optional[dict[str, Any]]:
    """Validate and parse LLM JSON response.

    Extracts JSON from the raw text, validates required fields,
    and normalizes the result. Returns None if parsing fails.

    Args:
        raw_text: Raw LLM output string.
        metric_name: Name of the metric (for logging).

    Returns:
        Parsed and validated dictionary, or None on failure.
    """
    if not isinstance(raw_text, str):
        return None
    json_str = extract_json_from_text(raw_text)
    if not json_str:
        logger.warning(
            "No JSON found in LLM response for %s", metric_name
        )
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning(
            "JSON parse error for %s: %s", metric_name, exc
        )
        return None

    if not isinstance(data, dict):
        logger.warning(
            "LLM response for %s is not a JSON object", metric_name
        )
        return None

    # Check required fields
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        logger.warning(
            "Missing required fields %s in LLM response for %s",
            missing,
            metric_name,
        )
        return None

    # Reject ambiguous scales/non-finite values instead of quietly changing them.
    score = data["score"]
    if score is None:
        if metric_name not in ("accuracy", "groundedness", "completeness"):
            return None
    elif isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
        logger.warning("Invalid 0-1 score for %s", metric_name)
        return None
    else:
        data["score"] = round(score, 4)

    if not isinstance(data["reason"], str) or not data["reason"].strip():
        return None
    for field in ("evidence", "strengths", "weaknesses", "suggestions"):
        val = data.get(field, [])
        if val is None:
            val = []
        elif isinstance(val, str):
            val = [val]
        if not isinstance(val, list) or any(not isinstance(item, str) for item in val):
            return None
        data[field] = [item.strip() for item in val if item.strip() and item.strip().lower().rstrip('.') not in ("none", "n/a", "no issues", "none needed")]

    verdicts = {
        "accuracy": {"CORRECT", "INCORRECT", "UNVERIFIABLE", "CONFLICTING"},
        "groundedness": {"SUPPORTED", "UNSUPPORTED", "CONTRADICTED"},
    }
    if metric_name in verdicts:
        claims = data.get("claims")
        if not isinstance(claims, list):
            return None
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
                return None
            verdict = claim.get("verdict")
            if not isinstance(verdict, str) or verdict.upper() not in verdicts[metric_name]:
                return None
            evidence = claim.get("evidence")
            if evidence is not None and not isinstance(evidence, str):
                return None
            if verdict.upper() in ("CORRECT", "INCORRECT", "SUPPORTED", "CONTRADICTED", "CONFLICTING") and (not evidence or not evidence.strip()):
                return None
            if metric_name == "accuracy" and verdict.upper() == "INCORRECT":
                quote = claim.get("contradicting_quote")
                if not isinstance(quote, str) or not quote.strip():
                    return None
        data["claims"] = claims
    else:
        data["claims"] = []

    if metric_name == "completeness":
        requirements = data.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            return None
        for requirement in requirements:
            if not isinstance(requirement, dict) or not isinstance(requirement.get("requirement"), str) or not requirement["requirement"].strip():
                return None
            status = requirement.get("status")
            if not isinstance(status, str) or status.lower() not in ("covered", "partial", "missing"):
                return None
            if requirement.get("evidence") is not None and not isinstance(requirement["evidence"], str):
                return None
        data["requirements"] = requirements
    else:
        data["requirements"] = []

    return data
