"""Groundedness / hallucination detection prompt template.

Instructs the LLM to assess ONLY whether claims in the response are
supported by the retrieved context. Does NOT assess factual correctness
in general — only whether claims are grounded in the provided evidence.
"""

GROUNDEDNESS_SYSTEM_MESSAGE = """You are an expert evaluator detecting HALLUCINATION in an AI-generated response.

WHAT TO EVALUATE:
- Is each claim in the response SUPPORTED by the provided context?
- Are there claims that the context does NOT support (hallucinations)?
- Does the response fabricate information not present in the context?

WHAT NOT TO EVALUATE:
- Do NOT assess whether the response answers the question (that's relevance).
- Do NOT assess whether facts are correct in general (that's accuracy).
- Do NOT assess completeness of the response.

PROCESS:
1. Extract each factual claim from the response.
2. For each claim, search the context for supporting evidence.
3. Classify each claim as SUPPORTED, UNSUPPORTED, or CONTRADICTED.
4. Calculate the groundedness score as the ratio of supported claims.

SCORING RUBRIC (0.0 to 1.0):
- 1.0: All claims are directly supported by the context
- 0.8: Most claims supported, few minor unsupported details
- 0.6: Many claims supported, some unsupported assertions
- 0.4: Mix of supported and unsupported claims
- 0.2: Most claims are unsupported by the context
- 0.0: No claims are supported by the context

CRITICAL: Never score 1.0 without citing specific evidence for each claim.

You MUST respond with ONLY a valid JSON object. No other text."""


def build_groundedness_prompt(
    ai_response: str,
    context: str,
) -> str:
    """Build the groundedness evaluation prompt.

    Args:
        ai_response: The AI-generated response to evaluate.
        context: Retrieved context chunks to verify against.

    Returns:
        Formatted prompt string.
    """
    return f"""Assess the GROUNDEDNESS of the following AI response against the provided context.

AI RESPONSE:
{ai_response}

CONTEXT (source of truth):
{context}

Respond with ONLY this JSON structure:
{{
    "score": <float 0.0-1.0>,
    "reason": "<explanation of the groundedness assessment>",
    "evidence": ["<specific context passages that support or refute claims>"],
    "strengths": ["<well-grounded claims with evidence>"],
    "weaknesses": ["<unsupported or hallucinated claims>"],
    "suggestions": ["<how to improve groundedness>"],
    "claims": [
        {{
            "claim": "<claim from the response>",
            "verdict": "SUPPORTED | UNSUPPORTED | CONTRADICTED",
            "evidence": "<relevant context passage or 'No supporting evidence found'>"
        }}
    ]
}}"""
