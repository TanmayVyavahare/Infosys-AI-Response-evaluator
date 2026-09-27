"""Base evaluator abstract class.

Defines the interface and shared logic for all evaluation agents.
Each concrete evaluator implements LLM-based evaluation and a
local NLP fallback path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.config.settings import get_settings
from app.core.exceptions import EvaluationError
from app.retrieval.embedder import Embedder
from app.schemas.common import MetricResult
from app.services.llm_provider import LLMProvider
from app.utils.json_validator import validate_llm_response
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationPackage:
    """Immutable data package passed to every evaluator.

    No evaluator should directly communicate with another.
    Each receives the same package and operates independently.
    """

    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    retrieved_context: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def context_text(self) -> str:
        """Concatenated text of all retrieved context chunks."""
        if not self.retrieved_context:
            return ""
        return "\n\n---\n\n".join(
            chunk.get("text", "") for chunk in self.retrieved_context
        )

    @property
    def has_context(self) -> bool:
        """Whether any retrieved context is available."""
        return bool(self.retrieved_context)

    @property
    def has_reference(self) -> bool:
        """Whether a reference answer is available."""
        return bool(self.reference_answer and self.reference_answer.strip())


class BaseEvaluator(ABC):
    """Abstract base class for all evaluation agents.

    Implements the Template Method pattern:
    1. Try LLM-based evaluation
    2. Validate LLM output
    3. On failure, fall back to local NLP evaluation

    Subclasses implement ``_evaluate_with_llm()`` and
    ``_evaluate_with_fallback()``.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        embedder: Optional[Embedder] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.embedder = embedder or Embedder()
        self.settings = get_settings()

    @property
    @abstractmethod
    def metric_name(self) -> str:
        """Return the name of this evaluation metric."""
        ...

    async def evaluate(self, package: EvaluationPackage) -> MetricResult:
        """Evaluate an AI response using LLM with fallback.

        First attempts LLM-based evaluation. If that fails (provider
        unavailable, malformed response, timeout), falls back to local
        NLP-based evaluation.

        Args:
            package: EvaluationPackage with all inputs.

        Returns:
            MetricResult with score, reason, evidence, etc.
        """
        # Try LLM path first
        if self.llm_provider is not None:
            try:
                result = await self._try_llm_evaluation(package)
                if result is not None:
                    return result
                logger.info(
                    "%s: LLM evaluation returned invalid result, falling back",
                    self.metric_name,
                )
            except Exception as exc:
                logger.warning(
                    "%s: LLM evaluation failed (%s), falling back",
                    self.metric_name,
                    exc,
                )

        # Fallback to local NLP
        try:
            result = self._evaluate_with_fallback(package)
            return result
        except Exception as exc:
            logger.error(
                "%s: Fallback evaluation also failed: %s",
                self.metric_name,
                exc,
            )
            return self._error_result(str(exc))

    async def _try_llm_evaluation(
        self, package: EvaluationPackage
    ) -> Optional[MetricResult]:
        """Attempt LLM-based evaluation with JSON validation and retry.

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult if successful, None if validation fails.
        """
        prompt, system_message = self._build_llm_prompt(package)

        for attempt in range(self.settings.max_json_retries + 1):
            raw_response = await self.llm_provider.generate(
                prompt=prompt,
                system_message=system_message,
            )

            validated = validate_llm_response(raw_response, self.metric_name)
            if validated is not None:
                return self._build_result_from_llm(validated)

            if attempt < self.settings.max_json_retries:
                logger.info(
                    "%s: Retrying LLM call (attempt %d)",
                    self.metric_name,
                    attempt + 2,
                )
                # Add retry instruction to prompt
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Please respond with ONLY a valid JSON object.\n\n"
                    + prompt
                )

        return None

    @abstractmethod
    def _build_llm_prompt(
        self, package: EvaluationPackage
    ) -> tuple[str, str]:
        """Build the LLM prompt and system message for this evaluator.

        Args:
            package: EvaluationPackage.

        Returns:
            Tuple of (prompt, system_message).
        """
        ...

    @abstractmethod
    def _evaluate_with_fallback(
        self, package: EvaluationPackage
    ) -> MetricResult:
        """Evaluate using local NLP only (no LLM).

        Args:
            package: EvaluationPackage.

        Returns:
            MetricResult computed via embeddings and heuristics.
        """
        ...

    def _build_result_from_llm(self, data: dict) -> MetricResult:
        """Convert validated LLM JSON into MetricResult.

        Args:
            data: Validated dictionary from LLM response.

        Returns:
            MetricResult instance.
        """
        from app.schemas.common import ClaimDetail, RequirementCoverage

        claims = []
        for c in data.get("claims", []):
            if isinstance(c, dict):
                claims.append(
                    ClaimDetail(
                        claim=c.get("claim", ""),
                        supported=c.get("verdict", "").upper() in ("CORRECT", "SUPPORTED"),
                        evidence=c.get("evidence"),
                    )
                )

        requirements = []
        for r in data.get("requirements", []):
            if isinstance(r, dict):
                requirements.append(
                    RequirementCoverage(
                        requirement=r.get("requirement", ""),
                        status=r.get("status", "missing").lower(),
                        evidence=r.get("evidence"),
                    )
                )

        return MetricResult(
            metric_name=self.metric_name,
            score=data["score"],
            reason=data["reason"],
            evidence=data.get("evidence", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestions=data.get("suggestions", []),
            claims=claims,
            requirements=requirements,
            evaluated_with="llm",
        )

    def _error_result(self, error_message: str) -> MetricResult:
        """Create an error MetricResult when evaluation fails.

        Args:
            error_message: Description of the failure.

        Returns:
            MetricResult with None score and error reason.
        """
        return MetricResult(
            metric_name=self.metric_name,
            score=None,
            reason=f"Evaluation failed: {error_message}",
            weaknesses=[f"Could not evaluate: {error_message}"],
            evaluated_with="error",
        )
