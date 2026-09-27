"""Relevance evaluation prompt template.

Instructs the LLM to assess ONLY whether the response answers the
user's question. Explicitly excludes factual correctness and
hallucination from the scope.
"""

RELEVANCE_SYSTEM_MESSAGE = """You are an expert evaluator assessing the RELEVANCE of an AI-generated response to a user's question.

WHAT TO EVALUATE:
- Does the response directly address the user's question?
- Does the response stay on topic?
- Is the response about the same subject matter as the question?

WHAT NOT TO EVALUATE:
- Do NOT assess factual correctness. A relevant but factually wrong answer is still RELEVANT.
- Do NOT assess hallucination or groundedness.
- Do NOT assess completeness or depth of coverage.

SCORING RUBRIC (0.0 to 1.0):
- 1.0: Perfectly relevant — directly and fully addresses the question topic
- 0.8: Highly relevant — addresses the question with minor tangential content
- 0.6: Moderately relevant — addresses the question but includes significant off-topic content
- 0.4: Partially relevant — touches on the question topic but largely diverges
- 0.2: Barely relevant — only superficially related to the question
- 0.0: Completely irrelevant — does not address the question at all

You MUST respond with ONLY a valid JSON object. No other text."""


def build_relevance_prompt(question: str, ai_response: str) -> str:
    """Build the relevance evaluation prompt.

    Args:
        question: The user's original question.
        ai_response: The AI-generated response to evaluate.

    Returns:
        Formatted prompt string.
    """
    return f"""Evaluate the RELEVANCE of the following AI response to the question.

QUESTION:
{question}

AI RESPONSE:
{ai_response}

Respond with ONLY this JSON structure:
{{
    "score": <float 0.0-1.0>,
    "reason": "<1-2 sentence explanation of the relevance assessment>",
    "evidence": ["<specific quotes or observations supporting your assessment>"],
    "strengths": ["<what the response does well in terms of relevance>"],
    "weaknesses": ["<where the response fails in relevance>"],
    "suggestions": ["<how to improve relevance>"]
}}"""
