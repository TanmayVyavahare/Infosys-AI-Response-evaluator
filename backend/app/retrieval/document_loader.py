"""Document loaders for PDF, TXT, and DOCX files.

Each loader extracts text with metadata (filename, page number)
and returns a list of document chunks ready for further processing.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Protocol

from app.core.exceptions import DocumentLoadError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentChunk:
    """A chunk of text extracted from a document with metadata."""

    __slots__ = ("text", "metadata")

    def __init__(self, text: str, metadata: dict) -> None:
        self.text = text
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"DocumentChunk(len={len(self.text)}, source={self.metadata.get('source', '?')})"


class DocumentLoader(Protocol):
    """Protocol for document loaders."""

    def load(self, content: str | bytes, filename: str) -> list[DocumentChunk]:
        """Load document and return text chunks with metadata."""
        ...


class TextLoader:
    """Loader for plain text files."""

    def load(self, content: str | bytes, filename: str) -> list[DocumentChunk]:
        """Load plain text content.

        Args:
            content: File content as string or bytes.
            filename: Original filename for metadata.

        Returns:
            Single DocumentChunk containing the full text.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return [
            DocumentChunk(
                text=content,
                metadata={"source": filename, "page": 1, "type": "txt"},
            )
        ]


class PDFLoader:
    """Loader for PDF files using PyPDF2."""

    def load(self, content: str | bytes, filename: str) -> list[DocumentChunk]:
        """Load PDF and extract text page by page.

        Args:
            content: PDF file content as bytes.
            filename: Original filename for metadata.

        Returns:
            List of DocumentChunks, one per page.
        """
        try:
            import PyPDF2
        except ImportError:
            raise DocumentLoadError(
                "PyPDF2 is required for PDF support. Install it with: pip install PyPDF2"
            )

        if isinstance(content, str):
            content = content.encode("utf-8")

        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            chunks: list[DocumentChunk] = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    chunks.append(
                        DocumentChunk(
                            text=text.strip(),
                            metadata={
                                "source": filename,
                                "page": i + 1,
                                "type": "pdf",
                            },
                        )
                    )
            if not chunks:
                raise DocumentLoadError(
                    f"No text could be extracted from PDF: {filename}"
                )
            return chunks
        except DocumentLoadError:
            raise
        except Exception as exc:
            raise DocumentLoadError(
                f"Failed to load PDF '{filename}': {exc}"
            ) from exc


class DOCXLoader:
    """Loader for DOCX files using python-docx."""

    def load(self, content: str | bytes, filename: str) -> list[DocumentChunk]:
        """Load DOCX and extract text paragraph by paragraph.

        Args:
            content: DOCX file content as bytes.
            filename: Original filename for metadata.

        Returns:
            Single DocumentChunk with all paragraph text combined.
        """
        try:
            import docx
        except ImportError:
            raise DocumentLoadError(
                "python-docx is required for DOCX support. Install: pip install python-docx"
            )

        if isinstance(content, str):
            content = content.encode("utf-8")

        try:
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            if not paragraphs:
                raise DocumentLoadError(
                    f"No text found in DOCX: {filename}"
                )
            return [
                DocumentChunk(
                    text="\n\n".join(paragraphs),
                    metadata={"source": filename, "page": 1, "type": "docx"},
                )
            ]
        except DocumentLoadError:
            raise
        except Exception as exc:
            raise DocumentLoadError(
                f"Failed to load DOCX '{filename}': {exc}"
            ) from exc


class DocumentLoaderFactory:
    """Factory for creating document loaders based on file extension."""

    _loaders: dict[str, type] = {
        ".txt": TextLoader,
        ".pdf": PDFLoader,
        ".docx": DOCXLoader,
    }

    @classmethod
    def get_loader(cls, filename: str) -> DocumentLoader:
        """Get appropriate loader for the given filename.

        Args:
            filename: Filename or path with extension.

        Returns:
            DocumentLoader instance.

        Raises:
            DocumentLoadError: If extension is not supported.
        """
        ext = Path(filename).suffix.lower()
        loader_cls = cls._loaders.get(ext)
        if loader_cls is None:
            supported = ", ".join(cls._loaders.keys())
            raise DocumentLoadError(
                f"Unsupported file type '{ext}'. Supported: {supported}"
            )
        return loader_cls()

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """Return list of supported file extensions."""
        return list(cls._loaders.keys())
