"""Sentence-transformer embedding service.

Wraps the ``all-MiniLM-L6-v2`` model with singleton loading,
batch embedding, and cosine similarity computation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from app.config.settings import get_settings
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)

# Module-level singleton
_model: "SentenceTransformer | None" = None


def _get_model() -> "SentenceTransformer":
    """Load and cache the sentence-transformer model (singleton).

    Returns:
        Loaded SentenceTransformer model instance.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        logger.info("Loading embedding model: %s", settings.embedding_model_name)
        # Reuse an installed model without repeated network metadata checks.
        # A first installation still downloads the public model normally.
        try:
            _model = SentenceTransformer(settings.embedding_model_name, local_files_only=True)
        except OSError:
            _model = SentenceTransformer(settings.embedding_model_name)
        logger.info("Embedding model loaded successfully")
    return _model


class Embedder:
    """Embedding service using sentence-transformers.

    Provides text-to-vector conversion and similarity computation.
    The underlying model is loaded lazily and shared across instances.
    """

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text into a dense vector.

        Args:
            text: Input text string.

        Returns:
            Numpy array of shape ``(embedding_dim,)``.
        """
        model = _get_model()
        embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a batch of texts.

        Args:
            texts: List of input text strings.

        Returns:
            List of numpy arrays, each of shape ``(embedding_dim,)``.
        """
        if not texts:
            return []
        model = _get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return list(embeddings)

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec_a: First embedding vector.
            vec_b: Second embedding vector.

        Returns:
            Cosine similarity in range [-1, 1].
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def semantic_similarity(self, text_a: str, text_b: str) -> float:
        """Compute semantic similarity between two texts.

        Args:
            text_a: First text.
            text_b: Second text.

        Returns:
            Cosine similarity score in range [-1, 1].
        """
        emb_a = self.embed_text(text_a)
        emb_b = self.embed_text(text_b)
        return self.cosine_similarity(emb_a, emb_b)
