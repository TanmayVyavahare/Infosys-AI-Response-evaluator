"""Semantic similarity fallback using sentence embeddings.

Provides cosine-similarity–based scoring without requiring an LLM.
Used as the primary fallback for all evaluators.
"""

from __future__ import annotations

import numpy as np

from app.retrieval.embedder import Embedder
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SemanticFallback:
    """Compute semantic similarity using sentence embeddings."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or Embedder()

    def text_similarity(self, text_a: str, text_b: str) -> float:
        """Compute semantic similarity between two texts.

        Args:
            text_a: First text string.
            text_b: Second text string.

        Returns:
            Cosine similarity score clamped to [0, 1].
        """
        if not text_a.strip() or not text_b.strip():
            return 0.0
        score = self.embedder.semantic_similarity(text_a, text_b)
        return max(0.0, min(1.0, score))

    def best_chunk_similarity(
        self, query: str, chunks: list[str]
    ) -> tuple[float, str]:
        """Find the chunk most similar to the query.

        Args:
            query: Query text.
            chunks: List of candidate text chunks.

        Returns:
            Tuple of (best_score, best_chunk_text).
        """
        if not chunks:
            return 0.0, ""

        query_emb = self.embedder.embed_text(query)
        chunk_embs = self.embedder.embed_batch(chunks)

        best_score = 0.0
        best_chunk = ""
        for chunk, chunk_emb in zip(chunks, chunk_embs):
            score = self.embedder.cosine_similarity(query_emb, chunk_emb)
            score = max(0.0, score)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        return best_score, best_chunk

    def multi_similarity(
        self, query: str, candidates: list[str]
    ) -> list[tuple[float, str]]:
        """Score all candidates against the query, sorted by similarity.

        Args:
            query: Query text.
            candidates: List of candidate texts.

        Returns:
            List of (score, text) tuples, highest score first.
        """
        if not candidates:
            return []

        query_emb = self.embedder.embed_text(query)
        cand_embs = self.embedder.embed_batch(candidates)

        results = []
        for cand, cand_emb in zip(candidates, cand_embs):
            score = max(0.0, self.embedder.cosine_similarity(query_emb, cand_emb))
            results.append((score, cand))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def topic_similarity(self, text_a: str, text_b: str) -> float:
        """Coarser topic-level similarity using mean embeddings.

        Embeds sentences of each text separately and compares their
        mean vectors. More robust to length differences than full-text
        comparison.

        Args:
            text_a: First text.
            text_b: Second text.

        Returns:
            Topic similarity score in [0, 1].
        """
        from app.utils.text_processing import split_into_sentences

        sents_a = split_into_sentences(text_a)
        sents_b = split_into_sentences(text_b)

        if not sents_a or not sents_b:
            return self.text_similarity(text_a, text_b)

        embs_a = self.embedder.embed_batch(sents_a)
        embs_b = self.embedder.embed_batch(sents_b)

        mean_a = np.mean(embs_a, axis=0)
        mean_b = np.mean(embs_b, axis=0)

        score = self.embedder.cosine_similarity(mean_a, mean_b)
        return max(0.0, min(1.0, score))
