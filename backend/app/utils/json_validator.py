"""JSON validation for LLM responses.

Provides a shared helper that every evaluator uses to parse and validate
JSON output from LLMs, with retry and fallback logic.
"""

from __future__ import annotations

import json
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

    # Normalize score to float in [0, 1]
    try:
        score = float(data["score"])
        if score < 0:
            score = 0.0
        elif score > 1:
            # Handle 0–10 or 0–100 scales
            if score <= 10:
                score = score / 10.0
            elif score <= 100:
                score = score / 100.0
            else:
                score = 1.0
        data["score"] = round(score, 4)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid score value '%s' for %s", data.get("score"), metric_name
        )
        return None

    # Ensure list fields are lists
    for field in ("evidence", "strengths", "weaknesses", "suggestions"):
        val = data.get(field)
        if val is None:
            data[field] = []
        elif isinstance(val, str):
            data[field] = [val] if val.strip() else []
        elif not isinstance(val, list):
            data[field] = []

    # Ensure reason is a string
    if not isinstance(data.get("reason"), str):
        data["reason"] = str(data.get("reason", ""))

    return data
