"""FAISS-based retriever with disk caching.

Builds and caches a FAISS index from document chunks. Supports
similarity search with score thresholding. Index is rebuilt only
when the document content hash changes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

import numpy as np

from app.config.settings import get_settings
from app.retrieval.chunker import RecursiveChunker
from app.retrieval.document_loader import DocumentChunk, DocumentLoaderFactory
from app.retrieval.embedder import Embedder
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FAISSRetriever:
    """Retrieve relevant context chunks from documents using FAISS.

    Manages the full pipeline: load → chunk → embed → index → search.
    Caches the FAISS index to disk to avoid rebuilding per request.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        chunker: RecursiveChunker | None = None,
    ) -> None:
        self.embedder = embedder or Embedder()
        self.chunker = chunker or RecursiveChunker()
        self.settings = get_settings()
        self._index = None
        self._chunks: list[DocumentChunk] = []
        self._current_hash: str | None = None

    def retrieve_from_text(
        self,
        query: str,
        document_text: str,
        top_k: int | None = None,
    ) -> list[dict]:
        """Retrieve relevant chunks from raw document text.

        Args:
            query: Search query (typically the user's question).
            document_text: Raw source document text.
            top_k: Number of results to return.

        Returns:
            List of dicts with 'text', 'score', and 'metadata' keys.
        """
        doc_hash = self._compute_hash(document_text)
        if doc_hash != self._current_hash:
            self._build_index_from_text(document_text, doc_hash)
        return self._search(query, top_k)

    def _build_index_from_text(self, text: str, doc_hash: str) -> None:
        """Build FAISS index from raw text.

        Checks for cached index on disk first. If not found or hash
        differs, builds a new index and caches it.

        Args:
            text: Document text to index.
            doc_hash: Hash of the document content.
        """
        import faiss

        cache_path = self.settings.faiss_cache_dir / f"{doc_hash}.index"
        meta_path = self.settings.faiss_cache_dir / f"{doc_hash}.meta.json"

        # Try loading from cache
        if cache_path.exists() and meta_path.exists():
            try:
                self._index = faiss.read_index(str(cache_path))
                with open(meta_path, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)
                self._chunks = [
                    DocumentChunk(text=c["text"], metadata=c["metadata"])
                    for c in chunks_data
                ]
                self._current_hash = doc_hash
                logger.info("Loaded FAISS index from cache: %s", cache_path.name)
                return
            except Exception as exc:
                logger.warning("Failed to load cached index: %s", exc)

        # Build new index
        logger.info("Building new FAISS index (hash: %s)", doc_hash[:12])

        # Create document chunks from raw text
        raw_doc = DocumentChunk(
            text=text,
            metadata={"source": "user_input", "page": 1, "type": "text"},
        )
        self._chunks = self.chunker.chunk_documents([raw_doc])

        if not self._chunks:
            logger.warning("No chunks produced from document text")
            self._index = None
            self._current_hash = doc_hash
            return

        # Embed all chunks
        texts = [c.text for c in self._chunks]
        embeddings = self.embedder.embed_batch(texts)
        embedding_matrix = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity (use inner product on normalized vectors)
        faiss.normalize_L2(embedding_matrix)

        # Build FAISS index
        dim = embedding_matrix.shape[1]
        self._index = faiss.IndexFlatIP(dim)  # Inner product = cosine on normalized vectors
        self._index.add(embedding_matrix)

        # Cache to disk
        try:
            faiss.write_index(self._index, str(cache_path))
            chunks_data = [
                {"text": c.text, "metadata": c.metadata}
                for c in self._chunks
            ]
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, ensure_ascii=False)
            logger.info("Cached FAISS index to: %s", cache_path.name)
        except Exception as exc:
            logger.warning("Failed to cache index: %s", exc)

        self._current_hash = doc_hash

    def _search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict]:
        """Search the FAISS index for relevant chunks.

        Args:
            query: Search query text.
            top_k: Number of results to return.

        Returns:
            List of result dicts sorted by relevance score.
        """
        import faiss

        if self._index is None or not self._chunks:
            return []

        top_k = min(top_k or self.settings.retrieval_top_k, len(self._chunks))

        # Embed and normalize query
        query_embedding = self.embedder.embed_text(query)
        query_vector = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vector)

        # Search
        scores, indices = self._index.search(query_vector, top_k)

        results: list[dict] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < self.settings.retrieval_score_threshold:
                continue
            chunk = self._chunks[idx]
            results.append(
                {
                    "text": chunk.text,
                    "score": float(score),
                    "metadata": chunk.metadata,
                }
            )

        logger.info(
            "Retrieved %d chunks (top_k=%d, threshold=%.2f)",
            len(results),
            top_k,
            self.settings.retrieval_score_threshold,
        )
        return results

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Compute SHA-256 hash of text for cache keying.

        Args:
            text: Input text.

        Returns:
            Hex digest string.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
