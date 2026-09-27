"""Named Entity Recognition fallback using regex patterns.

Extracts numbers, dates, percentages, currencies, and capitalized
noun phrases without requiring spaCy or other NLP libraries.
"""

from __future__ import annotations

import re
from collections import defaultdict

from app.utils.logging import get_logger

logger = get_logger(__name__)


class NERExtractor:
    """Regex-based Named Entity Recognition.

    Extracts structured entities from text for fact-checking:
    numbers, dates, percentages, currencies, and proper nouns.
    """

    # Compiled regex patterns for entity types
    _patterns: dict[str, re.Pattern] = {
        "number": re.compile(
            r'\b\d[\d,]*\.?\d*\b'
        ),
        "date": re.compile(
            r'\b(?:'
            r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'
            r'|(?:January|February|March|April|May|June|July|August|'
            r'September|October|November|December|'
            r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
            r'\.?\s+\d{1,2},?\s*\d{2,4}'
            r'|\d{4}'
            r')\b',
            re.IGNORECASE,
        ),
        "percentage": re.compile(
            r'\b\d+\.?\d*\s*%'
        ),
        "currency": re.compile(
            r'(?:\$|€|£|¥)\s*\d[\d,]*\.?\d*'
            r'|\b\d[\d,]*\.?\d*\s*(?:dollars|euros|pounds|yen|USD|EUR|GBP)\b',
            re.IGNORECASE,
        ),
        "proper_noun": re.compile(
            r'\b(?:[A-Z][a-z]+(?:\s+(?:of|the|and|for|de|van|von|al|bin)\s+)?){1,5}[A-Z][a-z]+\b'
        ),
    }

    # Stop words that shouldn't be treated as proper nouns even when capitalized
    _stop_phrases: set[str] = {
        "The", "This", "That", "These", "Those", "There",
        "Here", "However", "Moreover", "Furthermore", "Therefore",
        "Although", "Because", "Since", "While", "Where",
        "When", "What", "Which", "How", "Why", "Also",
        "Then", "Thus", "Hence", "Indeed", "Instead",
    }

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract all entity types from text.

        Args:
            text: Input text to extract entities from.

        Returns:
            Dict mapping entity type names to lists of extracted strings.
        """
        entities: dict[str, list[str]] = defaultdict(list)

        for ent_type, pattern in self._patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                match = match.strip()
                if ent_type == "proper_noun" and match in self._stop_phrases:
                    continue
                if match and match not in entities[ent_type]:
                    entities[ent_type].append(match)

        # Additional: extract capitalized sequences at sentence starts differently
        # to avoid false positives
        entities["proper_noun"] = self._filter_proper_nouns(
            entities["proper_noun"], text
        )

        return dict(entities)

    def _filter_proper_nouns(
        self, nouns: list[str], original_text: str
    ) -> list[str]:
        """Filter out false-positive proper nouns.

        Removes words that are only capitalized because they start a
        sentence, and common stop phrases.

        Args:
            nouns: Candidate proper nouns.
            original_text: Original text for context.

        Returns:
            Filtered list of proper nouns.
        """
        filtered: list[str] = []
        for noun in nouns:
            # Skip single-word nouns that might just be sentence starters
            words = noun.split()
            if len(words) == 1:
                continue
            # Skip if it's a stop phrase
            if noun in self._stop_phrases:
                continue
            filtered.append(noun)
        return filtered

    @staticmethod
    def entity_overlap(
        entities_a: dict[str, list[str]],
        entities_b: dict[str, list[str]],
    ) -> float:
        """Compute overlap ratio between two entity sets.

        Args:
            entities_a: Entities from text A.
            entities_b: Entities from text B.

        Returns:
            Overlap ratio in [0, 1]. Returns 0.0 if both sets are empty.
        """
        all_types = set(entities_a.keys()) | set(entities_b.keys())
        if not all_types:
            return 0.0

        total_overlap = 0
        total_count = 0

        for ent_type in all_types:
            set_a = set(e.lower() for e in entities_a.get(ent_type, []))
            set_b = set(e.lower() for e in entities_b.get(ent_type, []))

            if not set_a and not set_b:
                continue

            union = set_a | set_b
            intersection = set_a & set_b

            total_overlap += len(intersection)
            total_count += len(union)

        if total_count == 0:
            return 0.0

        return total_overlap / total_count

    @staticmethod
    def number_match(
        numbers_a: list[str], numbers_b: list[str]
    ) -> float:
        """Compare numerical values between two sets.

        Handles formatted numbers (commas, decimals) and returns
        the fraction of numbers that match.

        Args:
            numbers_a: Numbers extracted from text A.
            numbers_b: Numbers extracted from text B.

        Returns:
            Match ratio in [0, 1].
        """
        if not numbers_a and not numbers_b:
            return 1.0  # No numbers to compare
        if not numbers_a or not numbers_b:
            return 0.0

        def normalize_num(s: str) -> float | None:
            try:
                return float(s.replace(",", ""))
            except ValueError:
                return None

        nums_a = {normalize_num(n) for n in numbers_a}
        nums_b = {normalize_num(n) for n in numbers_b}
        nums_a.discard(None)
        nums_b.discard(None)

        if not nums_a and not nums_b:
            return 1.0
        if not nums_a or not nums_b:
            return 0.0

        matches = nums_a & nums_b
        total = nums_a | nums_b

        return len(matches) / len(total) if total else 0.0
