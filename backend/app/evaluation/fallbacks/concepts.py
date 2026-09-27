"""Concept and requirement extraction for completeness evaluation.

Extracts the key requirements, subquestions, and expected content
from a question to assess whether a response covers everything.
"""

from __future__ import annotations

import re

from app.utils.text_processing import split_into_sentences
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConceptExtractor:
    """Extract requirements and expected content from questions.

    Detects question patterns (list, compare, explain, etc.) and
    extracts the specific sub-requirements that a complete answer
    should address.
    """

    # Question type indicators and their expected content
    _list_patterns = re.compile(
        r'\b(?:list|enumerate|name|identify|mention|state)\b',
        re.IGNORECASE,
    )
    _compare_patterns = re.compile(
        r'\b(?:compare|contrast|difference|differ|vs\.?|versus|similarities)\b',
        re.IGNORECASE,
    )
    _explain_patterns = re.compile(
        r'\b(?:explain|describe|elaborate|discuss|detail|analyze|examine)\b',
        re.IGNORECASE,
    )
    _advantage_patterns = re.compile(
        r'\b(?:advantage|disadvantage|pro|con|benefit|drawback|strength|weakness)\b',
        re.IGNORECASE,
    )
    _example_patterns = re.compile(
        r'\b(?:example|instance|illustration|demonstrate|show)\b',
        re.IGNORECASE,
    )
    _how_patterns = re.compile(
        r'\b(?:how\s+(?:does|do|can|to|is|are|would|should))\b',
        re.IGNORECASE,
    )
    _multi_part = re.compile(
        r'(?:\d+[\.\)]\s*|\b(?:first|second|third|also|additionally|finally)\b)',
        re.IGNORECASE,
    )

    def extract_requirements(
        self,
        question: str,
        reference: str | None = None,
    ) -> list[dict]:
        """Extract requirements from a question.

        The question is the PRIMARY source. The reference answer only
        enriches the list — it never replaces the question.

        Args:
            question: The user's question.
            reference: Optional reference answer for enrichment.

        Returns:
            List of requirement dicts with 'text' and 'type' keys.
        """
        requirements: list[dict] = []

        # 1. Extract explicit sub-questions
        sub_questions = self._extract_sub_questions(question)
        for sq in sub_questions:
            requirements.append({"text": sq, "type": "sub_question"})

        # 2. Detect question type and add implicit requirements
        type_reqs = self._extract_type_requirements(question)
        requirements.extend(type_reqs)

        # 3. Extract specific entities/concepts mentioned in the question
        concept_reqs = self._extract_concept_requirements(question)
        requirements.extend(concept_reqs)

        # 4. If we found nothing, treat the whole question as one requirement
        if not requirements:
            requirements.append({
                "text": question.strip().rstrip("?").strip(),
                "type": "main_question",
            })

        # 5. Enrich with reference (add, not replace)
        if reference:
            enriched = self._enrich_from_reference(requirements, reference)
            requirements.extend(enriched)

        # Deduplicate
        requirements = self._deduplicate(requirements)

        logger.info(
            "Extracted %d requirements from question (%d chars)",
            len(requirements),
            len(question),
        )
        return requirements

    def _extract_sub_questions(self, question: str) -> list[str]:
        """Extract sub-questions from compound questions.

        Args:
            question: The full question text.

        Returns:
            List of sub-question strings.
        """
        sub_qs: list[str] = []

        # Split on question marks for multiple questions
        parts = question.split("?")
        if len(parts) > 2:  # Multiple questions
            for part in parts[:-1]:  # Last part is empty or trailing text
                part = part.strip()
                if len(part.split()) >= 3:
                    sub_qs.append(part + "?")

        # Split on numbered items (1. ... 2. ... or a) ... b) ...)
        numbered = re.findall(
            r'(?:\d+[\.\)]\s*|[a-e][\.\)]\s*)([^.\d][^?]*\??)',
            question,
        )
        sub_qs.extend([n.strip() for n in numbered if len(n.split()) >= 3])

        # Split on "and" between question phrases
        if not sub_qs:
            and_parts = re.split(r'\band\b', question)
            if len(and_parts) >= 2:
                for part in and_parts:
                    part = part.strip().strip("?").strip()
                    if len(part.split()) >= 3:
                        sub_qs.append(part)

        return sub_qs

    def _extract_type_requirements(self, question: str) -> list[dict]:
        """Extract implicit requirements based on question type.

        Args:
            question: The question text.

        Returns:
            List of requirement dicts for expected content types.
        """
        reqs: list[dict] = []

        if self._list_patterns.search(question):
            reqs.append({
                "text": "Provide a list or enumeration",
                "type": "list_items",
            })

        if self._compare_patterns.search(question):
            reqs.append({
                "text": "Provide comparison or contrast",
                "type": "comparison",
            })
            reqs.append({
                "text": "Address similarities and differences",
                "type": "comparison_detail",
            })

        if self._advantage_patterns.search(question):
            reqs.append({
                "text": "Discuss advantages/pros",
                "type": "advantages",
            })
            reqs.append({
                "text": "Discuss disadvantages/cons",
                "type": "disadvantages",
            })

        if self._example_patterns.search(question):
            reqs.append({
                "text": "Provide examples",
                "type": "examples",
            })

        if self._explain_patterns.search(question):
            reqs.append({
                "text": "Provide detailed explanation",
                "type": "explanation",
            })

        if self._how_patterns.search(question):
            reqs.append({
                "text": "Explain the process or mechanism",
                "type": "process",
            })

        return reqs

    def _extract_concept_requirements(self, question: str) -> list[dict]:
        """Extract specific concepts/topics mentioned in the question.

        Args:
            question: The question text.

        Returns:
            List of concept requirement dicts.
        """
        reqs: list[dict] = []

        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', question)
        for q in quoted:
            reqs.append({"text": f"Address: {q}", "type": "concept"})

        # Extract key terms in capitalized sequences
        proper_nouns = re.findall(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', question
        )
        stop_words = {"What Is", "How Does", "Why Is", "Can You", "Do You", "Would You"}
        for noun in proper_nouns:
            if noun not in stop_words:
                reqs.append({"text": f"Address: {noun}", "type": "concept"})

        return reqs

    def _enrich_from_reference(
        self,
        existing: list[dict],
        reference: str,
    ) -> list[dict]:
        """Add requirements from reference that aren't in existing list.

        The reference only enriches — it never replaces question-derived
        requirements.

        Args:
            existing: Requirements already extracted from question.
            reference: Reference answer text.

        Returns:
            List of NEW requirements found in reference.
        """
        new_reqs: list[dict] = []
        existing_texts = {r["text"].lower() for r in existing}

        # Extract key points from reference
        ref_sentences = split_into_sentences(reference)
        for sent in ref_sentences:
            # Look for definitional or enumerative sentences
            if any(
                marker in sent.lower()
                for marker in ("is defined as", "refers to", "includes", "consists of")
            ):
                text = f"Cover: {sent[:100]}"
                if text.lower() not in existing_texts:
                    new_reqs.append({"text": text, "type": "reference_enrichment"})

        return new_reqs[:5]  # Limit enrichment additions

    @staticmethod
    def _deduplicate(requirements: list[dict]) -> list[dict]:
        """Remove duplicate requirements based on normalized text.

        Args:
            requirements: List of requirement dicts.

        Returns:
            Deduplicated list preserving order.
        """
        seen: set[str] = set()
        unique: list[dict] = []
        for req in requirements:
            key = req["text"].lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(req)
        return unique
