"""Recursive text chunker with configurable size and overlap.

Splits text on natural boundaries (paragraphs → sentences → words)
while preserving metadata and ensuring minimum chunk quality.
"""

from __future__ import annotations

import re

from app.config.settings import get_settings
from app.retrieval.document_loader import DocumentChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RecursiveChunker:
    """Chunk documents into overlapping segments for embedding.

    Splitting hierarchy: paragraph → sentence → word boundaries.
    Each chunk retains the parent document's metadata plus a unique chunk_id.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        min_chunk_length: int | None = None,
    ) -> None:
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_length = min_chunk_length or settings.min_chunk_length

    def chunk_documents(
        self, documents: list[DocumentChunk]
    ) -> list[DocumentChunk]:
        """Chunk a list of documents into smaller pieces.

        Args:
            documents: List of loaded DocumentChunks.

        Returns:
            List of smaller DocumentChunks with chunk_id in metadata.
        """
        all_chunks: list[DocumentChunk] = []
        global_id = 0

        for doc in documents:
            text_chunks = self._split_text(doc.text)
            for chunk_text in text_chunks:
                if len(chunk_text.strip()) < self.min_chunk_length:
                    continue
                metadata = {
                    **doc.metadata,
                    "chunk_id": global_id,
                }
                all_chunks.append(DocumentChunk(text=chunk_text, metadata=metadata))
                global_id += 1

        logger.info("Chunked %d documents into %d chunks", len(documents), len(all_chunks))
        return all_chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text recursively using natural boundaries.

        Tries paragraph splits first, then sentence splits,
        then falls back to word-level splits.

        Args:
            text: Input text string.

        Returns:
            List of chunk strings.
        """
        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", " "]
        return self._recursive_split(text, separators)

    def _recursive_split(
        self, text: str, separators: list[str]
    ) -> list[str]:
        """Recursively split text using progressively finer separators.

        Args:
            text: Text to split.
            separators: Ordered list of separators from coarsest to finest.

        Returns:
            List of chunk strings within the target size.
        """
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        if not separators:
            # Last resort: hard split at chunk_size
            return self._hard_split(text)

        sep = separators[0]
        remaining_seps = separators[1:]

        parts = text.split(sep)
        chunks: list[str] = []
        current_chunk = ""

        for part in parts:
            candidate = (
                current_chunk + sep + part if current_chunk else part
            )
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If this single part exceeds chunk_size, recurse with finer separator
                if len(part) > self.chunk_size:
                    sub_chunks = self._recursive_split(part, remaining_seps)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Apply overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlapping text between consecutive chunks.

        Args:
            chunks: List of non-overlapping chunks.

        Returns:
            List of chunks with overlap prepended from previous chunk.
        """
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            overlap_text = prev[-self.chunk_overlap :] if len(prev) > self.chunk_overlap else prev
            # Find a word boundary in the overlap
            space_idx = overlap_text.find(" ")
            if space_idx != -1:
                overlap_text = overlap_text[space_idx + 1 :]
            result.append(overlap_text + " " + chunks[i])
        return result

    def _hard_split(self, text: str) -> list[str]:
        """Split text at exact chunk_size boundaries on word boundaries.

        Args:
            text: Text that couldn't be split by any separator.

        Returns:
            List of chunk strings.
        """
        words = text.split()
        chunks: list[str] = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current.strip():
            chunks.append(current.strip())
        return chunks
