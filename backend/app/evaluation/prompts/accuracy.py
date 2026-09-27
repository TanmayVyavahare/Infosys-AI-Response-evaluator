"""Factual accuracy evaluation prompt template.

Instructs the LLM to assess ONLY factual correctness by comparing
atomic claims against a reference answer or retrieved context.
"""

ACCURACY_SYSTEM_MESSAGE = """You are an expert fact-checker assessing the FACTUAL ACCURACY of an AI-generated response.

WHAT TO EVALUATE:
- Are the factual claims in the response correct?
- Do numbers, dates, names, and specific facts match the reference/context?
- Are there any contradictions with the provided reference or context?

WHAT NOT TO EVALUATE:
- Do NOT assess relevance to the question.
- Do NOT assess completeness or coverage.
- Do NOT assess writing quality or style.

PROCESS:
1. Extract each atomic factual claim from the response.
2. Compare each claim against the reference answer and/or context.
3. Mark each claim as CORRECT, INCORRECT, or UNVERIFIABLE.
4. Calculate the overall accuracy score.

SCORING RUBRIC (0.0 to 1.0):
- 1.0: All claims are factually correct
- 0.8: Most claims correct, minor inaccuracies
- 0.6: Several claims correct, some inaccuracies
- 0.4: Mix of correct and incorrect claims
- 0.2: Most claims are incorrect
- 0.0: All claims are factually incorrect

IMPORTANT: If you cannot verify a claim because no reference or context covers it, mark it as UNVERIFIABLE — do NOT assume it is correct.

You MUST respond with ONLY a valid JSON object. No other text."""


def build_accuracy_prompt(
    question: str,
    ai_response: str,
    reference_answer: str | None = None,
    context: str | None = None,
) -> str:
    """Build the accuracy evaluation prompt.

    Args:
        question: The user's original question.
        ai_response: The AI-generated response to evaluate.
        reference_answer: Optional ground-truth reference.
        context: Optional retrieved context chunks.

    Returns:
        Formatted prompt string.
    """
    baseline_section = ""
    if reference_answer:
        baseline_section += f"\nREFERENCE ANSWER (primary baseline):\n{reference_answer}\n"
    if context:
        baseline_section += f"\nRETRIEVED CONTEXT (secondary baseline):\n{context}\n"

    if not baseline_section:
        baseline_section = "\nNOTE: No reference answer or context is available. Mark all claims as UNVERIFIABLE.\n"

    return f"""Assess the FACTUAL ACCURACY of the following AI response.

QUESTION:
{question}

AI RESPONSE:
{ai_response}
{baseline_section}
Respond with ONLY this JSON structure:
{{
    "score": <float 0.0-1.0>,
    "reason": "<explanation of the accuracy assessment>",
    "evidence": ["<specific facts checked and their status>"],
    "strengths": ["<correct facts identified>"],
    "weaknesses": ["<incorrect or unverifiable facts>"],
    "suggestions": ["<how to improve factual accuracy>"],
    "claims": [
        {{
            "claim": "<atomic factual claim>",
            "verdict": "CORRECT | INCORRECT | UNVERIFIABLE",
            "evidence": "<supporting or refuting evidence>"
        }}
    ]
}}"""
