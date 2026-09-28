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
2. Use the reference only to interpret explicitly requested requirements. Never add requirements merely because the reference contains extra facts. Use source context to determine whether a source-only question is answerable.
3. For each requirement, check if the response covers it: COVERED, PARTIAL, or MISSING.
4. Split independently requested items into separate requirements (price, project limit, support and trial = four). Calculate score = (COVERED count + 0.5 * PARTIAL count) / requirement count. Answering one of four is 0.25, never 0.8. A justified abstention can fully address an unanswerable source-only question; a bare refusal of an answerable question does not cover it.

SCORING RUBRIC (0.0 to 1.0):
- 1.0: All requirements fully covered
- 0.8: Most requirements covered, minor omissions
- 0.6: Several requirements covered, some missing
- 0.4: Partial coverage of key requirements
- 0.2: Most requirements missing
- 0.0: No requirements addressed

BOUNDARY EXAMPLES:
- If asked for a launch year and the answer supplies a year, the year requirement is COVERED even if the year is false or not verifiable. Accuracy and source support handle that separately.
- If asked for a price and the answer states the wrong price, completeness is still 1.0. Do not add an 'accurate price' requirement that duplicates fact checking.
- If a source-only question cannot be answered from the supplied material, an explicit explanation of that absence can be COVERED. This does not mean a bare refusal covers an answerable question.
- Extra reference details that were not requested do not become requirements.
Before returning, check that no requirement is marked missing solely because its stated answer is unsupported or incorrect.

You MUST respond with ONLY a valid JSON object. No other text."""


def build_completeness_prompt(
    question: str,
    ai_response: str,
    reference_answer: str | None = None,
    context: str | None = None,
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
REFERENCE ANSWER (interpret explicitly requested requirements only; do NOT add requirements):
{reference_answer}
"""
    if context:
        ref_section += f"\nSOURCE CONTEXT (check answerability; do NOT add requirements):\n{context}\n"

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
