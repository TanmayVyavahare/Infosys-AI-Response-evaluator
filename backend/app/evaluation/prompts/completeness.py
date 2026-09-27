"""Completeness evaluation prompt template.

Instructs the LLM to assess ONLY whether the response covers all
required aspects of the question. The question is the PRIMARY source
of requirements; the reference answer only enriches.
"""

COMPLETENESS_SYSTEM_MESSAGE = """You are an expert evaluator assessing the COMPLETENESS of an AI-generated response.

WHAT TO EVALUATE:
- Does the response cover ALL aspects of the question?
- Are all sub-questions answered?
- Are requested lists, comparisons, examples, etc. provided?
- Does the response address all required topics?

WHAT NOT TO EVALUATE:
- Do NOT assess factual correctness (that's accuracy).
- Do NOT assess whether claims are grounded (that's groundedness).
- Do NOT assess writing quality or style.

PROCESS:
1. Extract ALL requirements from the question (sub-questions, topics, requested formats).
2. If a reference answer is provided, use it to ENRICH the requirement list only — do NOT replace the question.
3. For each requirement, check if the response covers it: COVERED, PARTIAL, or MISSING.
4. Calculate coverage score.

SCORING RUBRIC (0.0 to 1.0):
- 1.0: All requirements fully covered
- 0.8: Most requirements covered, minor omissions
- 0.6: Several requirements covered, some missing
- 0.4: Partial coverage of key requirements
- 0.2: Most requirements missing
- 0.0: No requirements addressed

You MUST respond with ONLY a valid JSON object. No other text."""


def build_completeness_prompt(
    question: str,
    ai_response: str,
    reference_answer: str | None = None,
) -> str:
    """Build the completeness evaluation prompt.

    Args:
        question: The user's original question (PRIMARY requirement source).
        ai_response: The AI-generated response to evaluate.
        reference_answer: Optional reference for enrichment only.

    Returns:
        Formatted prompt string.
    """
    ref_section = ""
    if reference_answer:
        ref_section = f"""
REFERENCE ANSWER (for enrichment only — do NOT replace the question requirements):
{reference_answer}
"""

    return f"""Assess the COMPLETENESS of the following AI response.

QUESTION (primary source of requirements):
{question}

AI RESPONSE:
{ai_response}
{ref_section}
Respond with ONLY this JSON structure:
{{
    "score": <float 0.0-1.0>,
    "reason": "<explanation of the completeness assessment>",
    "evidence": ["<specific requirements and their coverage status>"],
    "strengths": ["<well-covered areas>"],
    "weaknesses": ["<missing or incomplete areas>"],
    "suggestions": ["<what to add for full completeness>"],
    "requirements": [
        {{
            "requirement": "<extracted requirement>",
            "status": "COVERED | PARTIAL | MISSING",
            "evidence": "<response snippet covering this, or 'Not addressed'>"
        }}
    ]
}}"""
