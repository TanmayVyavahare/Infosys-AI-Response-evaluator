"""Atomic claim extraction for accuracy and groundedness evaluation.

Splits AI responses into independent, verifiable factual claims
without using an LLM. Each claim is a self-contained assertion.
"""

from __future__ import annotations

import re

from app.utils.text_processing import split_into_sentences
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ClaimExtractor:
    """Extract atomic factual claims from text.

    Splits compound sentences, filters non-assertive content
    (questions, filler phrases, opinions), and produces
    independently verifiable claim strings.
    """

    # Phrases that indicate non-factual/subjective content
    _opinion_markers: set[str] = {
        "i think", "i believe", "in my opinion", "arguably",
        "it seems", "it appears", "perhaps", "maybe", "might",
        "could be", "probably", "possibly", "generally speaking",
    }

    # Conjunctions used to split compound claims
    _split_conjunctions = re.compile(
        r'\s*(?:;\s*|,\s+and\s+|,\s+but\s+|,\s+however\s*,?\s*|'
        r'\.\s+(?:Also|Additionally|Furthermore|Moreover|However|But)\s*,?\s*)',
        re.IGNORECASE,
    )

    def extract_claims(self, text: str) -> list[str]:
        """Extract atomic claims from text.

        Args:
            text: Input text (typically an AI response).

        Returns:
            List of atomic claim strings. Each is a self-contained
            factual assertion suitable for verification.
        """
        if not text or not text.strip():
            return []

        sentences = split_into_sentences(text)
        claims: list[str] = []

        for sentence in sentences:
            sentence = sentence.strip()

            # Skip questions
            if sentence.endswith("?"):
                continue

            # Skip very short fragments
            if len(sentence.split()) < 3:
                continue

            # Skip pure opinion markers
            if self._is_opinion(sentence):
                continue

            # Split compound sentences into atomic claims
            sub_claims = self._split_compound(sentence)

            for claim in sub_claims:
                claim = self._clean_claim(claim)
                if self._is_valid_claim(claim):
                    claims.append(claim)

        logger.info("Extracted %d claims from text (%d chars)", len(claims), len(text))
        return claims

    def _split_compound(self, sentence: str) -> list[str]:
        """Split a compound sentence into atomic parts.

        Args:
            sentence: A single sentence.

        Returns:
            List of sub-sentence claim strings.
        """
        parts = self._split_conjunctions.split(sentence)
        return [p.strip() for p in parts if p.strip()]

    def _is_opinion(self, text: str) -> bool:
        """Check if text is primarily an opinion statement.

        Args:
            text: Text to check.

        Returns:
            True if the text contains opinion markers.
        """
        text_lower = text.lower()
        return any(marker in text_lower for marker in self._opinion_markers)

    def _is_valid_claim(self, claim: str) -> bool:
        """Validate that a claim is suitable for verification.

        Args:
            claim: Candidate claim string.

        Returns:
            True if the claim is a valid verifiable assertion.
        """
        if not claim:
            return False
        words = claim.split()
        if len(words) < 3:
            return False
        # Must contain at least one word that's not a stop word
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "in", "it", "for"}
        content_words = [w for w in words if w.lower() not in stop_words]
        return len(content_words) >= 2

    @staticmethod
    def _clean_claim(claim: str) -> str:
        """Clean and normalize a claim string.

        Args:
            claim: Raw claim text.

        Returns:
            Cleaned claim with proper punctuation.
        """
        claim = claim.strip()
        # Remove leading conjunctions
        claim = re.sub(
            r'^(?:and|but|or|also|additionally|furthermore|moreover|however)\s+',
            '',
            claim,
            flags=re.IGNORECASE,
        )
        claim = claim.strip()
        # Capitalize first letter
        if claim and claim[0].islower():
            claim = claim[0].upper() + claim[1:]
        # Ensure ends with period
        if claim and not claim.endswith((".", "!", "?")):
            claim += "."
        return claim
