"""Extract explicit requirements without inventing extra tasks from reference facts."""
from __future__ import annotations
import re


class ConceptExtractor:
    def extract_requirements(self, question: str, reference: str | None = None) -> list[dict]:
        # Split questions and independent instructions, not noun pairs such as
        # "lists and tuples". Reference facts never create new requirements.
        question = re.sub(r"(?:^|\s)\d+[.)]\s+", "\n", question)
        clauses = re.split(
            r"[?;\n]+|(?:^|\s)\d+[.)]\s+|\.\s+(?:also,?\s*)?"
            r"|\b(?:and|also)\s+(?=(?:who|what|when|where|why|how|explain|"
            r"describe|compare|give|provide|list|name|identify)\b)",
            question.strip(), flags=re.IGNORECASE,
        )
        requirements = []
        for clause in clauses:
            clause = clause.strip(" ,.?\t")
            if not clause:
                continue
            pair = re.search(r"\b(advantages|pros|benefits)\s+and\s+(disadvantages|cons|drawbacks)\b", clause, re.I)
            if pair:
                for aspect in pair.groups():
                    requirements.append({"text": clause[:pair.start()] + aspect + clause[pair.end():], "type": "sub_question"})
            else:
                requirements.append({"text": clause, "type": "sub_question"})
        seen = set()
        unique = []
        for req in requirements:
            key = req["text"].casefold()
            if key not in seen:
                seen.add(key)
                unique.append(req)
        return unique
