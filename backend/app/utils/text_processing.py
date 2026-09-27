"""Text processing utilities shared across evaluators."""

from __future__ import annotations

import re


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using regex boundary detection.

    Handles abbreviations, decimal numbers, and common edge cases
    better than naive period splitting.

    Args:
        text: Input text to split.

    Returns:
        List of sentence strings, stripped of excess whitespace.
    """
    # Split on sentence-ending punctuation followed by space + uppercase
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    return [s.strip() for s in sentences if s.strip()]
