import re
from typing import Any
from pydantic import BaseModel, Field

from config.settings import settings
from app.rag.document_parser import ParsedDocument


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    token_count: int
    page_numbers: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """
    Splits ParsedDocument content into semantic overlapping chunks,
    preserving document hierarchy, heading context, list/table integrity,
    and accurate page-level provenance.
    """

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(f"chunk_overlap ({self.chunk_overlap}) must be smaller than chunk_size ({self.chunk_size})")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Approximate token count for English financial text (~1.3 tokens per word).
        """
        if not text:
            return 0
        words = re.findall(r"\S+", text)
        return max(1, int(len(words) * 1.3))

    @staticmethod
    def _is_heading(line: str) -> bool:
        """
        Determines if a short line represents a section or topic heading.
        """
        clean = line.strip()
        if not clean or len(clean) > 120:
            return False
        # Markdown headers
        if clean.startswith("#"):
            return True
        # Ending in colon or question mark with short word count
        words = clean.split()
        if len(words) <= 10:
            if clean.endswith(":") or clean.endswith("?"):
                return True
            if clean.isupper() and len(words) <= 8:
                return True
            if clean.istitle() and len(words) <= 8:
                return True
            # Numbered section heading (e.g. "1. Overview", "2.1 Key Regulations")
            if re.match(r"^(\d+\.|\d+\.\d+|Chapter\s+\d+|Section\s+\d+)\s+", clean, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _is_list_item(line: str) -> bool:
        """
        Determines if a line is a bullet point or numbered procedure list item.
        """
        clean = line.strip()
        if not clean:
            return False
        # Bullets and symbols
        if clean[0] in ("•", "-", "*", "–", "—", ">"):
            return True
        # Numbered list patterns: 1., (a), (1), a.
        if re.match(r"^(\d+[\.\)]|\([0-9a-zA-Z]+\)|[a-zA-Z][\.\)])\s+", clean):
            return True
        return False

    def _split_into_units(self, text: str) -> list[str]:
        """
        Splits text into coherent semantic units.
        - Preserves headings by binding them to the subsequent paragraph if short.
        - Keeps lists and table rows grouped together.
        - Splits oversized paragraphs cleanly at sentence boundaries.
        """
        if not text or not text.strip():
            return []

        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        pre_processed: list[str] = []

        # Step 1: Bind isolated heading paragraphs to the following paragraph
        idx = 0
        while idx < len(raw_paragraphs):
            p = raw_paragraphs[idx]
            lines = p.split("\n")
            if len(lines) == 1 and self._is_heading(lines[0]) and (idx + 1 < len(raw_paragraphs)):
                # Prepend heading to the next paragraph to preserve semantic context
                next_p = raw_paragraphs[idx + 1]
                pre_processed.append(f"{lines[0]}\n{next_p}")
                idx += 2
            else:
                pre_processed.append(p)
                idx += 1

        # Step 2: Split large paragraphs into sentences or sub-lists if exceeding chunk_size
        units: list[str] = []
        for p in pre_processed:
            if self.estimate_tokens(p) <= self.chunk_size:
                units.append(p)
            else:
                # Check if paragraph is composed of multiple list items
                lines = [ln.strip() for ln in p.split("\n") if ln.strip()]
                has_list_items = sum(1 for ln in lines if self._is_list_item(ln)) >= 2

                if has_list_items:
                    # Group list items into chunks below chunk_size
                    curr_group: list[str] = []
                    curr_group_tokens = 0
                    for ln in lines:
                        ln_tokens = self.estimate_tokens(ln)
                        if curr_group and (curr_group_tokens + ln_tokens > self.chunk_size):
                            units.append("\n".join(curr_group))
                            curr_group = [ln]
                            curr_group_tokens = ln_tokens
                        else:
                            curr_group.append(ln)
                            curr_group_tokens += ln_tokens
                    if curr_group:
                        units.append("\n".join(curr_group))
                else:
                    # Split at sentence boundaries
                    sentences = re.split(r"(?<=[.!?])\s+", p)
                    curr_sentence_group: list[str] = []
                    curr_tokens = 0
                    for s in sentences:
                        s_clean = s.strip()
                        if not s_clean:
                            continue
                        s_tokens = self.estimate_tokens(s_clean)
                        if curr_sentence_group and (curr_tokens + s_tokens > self.chunk_size):
                            units.append(" ".join(curr_sentence_group))
                            curr_sentence_group = [s_clean]
                            curr_tokens = s_tokens
                        else:
                            curr_sentence_group.append(s_clean)
                            curr_tokens += s_tokens
                    if curr_sentence_group:
                        units.append(" ".join(curr_sentence_group))

        return units

    def chunk_document(self, document: ParsedDocument) -> list[DocumentChunk]:
        """
        Chunks a ParsedDocument into DocumentChunks while strictly maintaining
        accurate page provenance, heading context, and overlap continuity.
        """
        # Build list of atomic units with accurate page numbers
        units_with_pages: list[tuple[str, int]] = []

        if document.pages:
            for page in document.pages:
                page_units = self._split_into_units(page.text)
                for u in page_units:
                    if u.strip():
                        units_with_pages.append((u.strip(), page.page_number))
        else:
            units = self._split_into_units(document.full_text)
            for u in units:
                if u.strip():
                    units_with_pages.append((u.strip(), 1))

        if not units_with_pages:
            return []

        chunks: list[DocumentChunk] = []
        # current_unit_tuples holds (text, page_number) tuples
        current_unit_tuples: list[tuple[str, int]] = []
        current_tokens = 0
        chunk_idx = 0

        i = 0
        while i < len(units_with_pages):
            unit_text, unit_page = units_with_pages[i]
            unit_tokens = self.estimate_tokens(unit_text)

            # Check if adding this unit exceeds chunk_size
            if current_unit_tuples and (current_tokens + unit_tokens > self.chunk_size):
                chunk_text = "\n\n".join(t for t, _ in current_unit_tuples)
                page_numbers = sorted(list({p for _, p in current_unit_tuples}))

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}_chunk_{chunk_idx}",
                        doc_id=document.doc_id,
                        chunk_index=chunk_idx,
                        text=chunk_text,
                        token_count=self.estimate_tokens(chunk_text),
                        page_numbers=page_numbers,
                        metadata={
                            **document.metadata,
                            "file_name": document.file_name,
                            "file_type": document.file_type,
                            "total_pages": document.total_pages,
                        },
                    )
                )
                chunk_idx += 1

                # Exact overlap rewind: iterate backwards over (text, page) tuples
                overlap_tuples: list[tuple[str, int]] = []
                overlap_tokens = 0

                for prev_text, prev_page in reversed(current_unit_tuples):
                    u_tok = self.estimate_tokens(prev_text)
                    if overlap_tokens + u_tok <= self.chunk_overlap:
                        overlap_tuples.insert(0, (prev_text, prev_page))
                        overlap_tokens += u_tok
                    else:
                        break

                current_unit_tuples = overlap_tuples
                current_tokens = overlap_tokens

            current_unit_tuples.append((unit_text, unit_page))
            current_tokens += unit_tokens
            i += 1

        # Emit the final remaining chunk
        if current_unit_tuples:
            chunk_text = "\n\n".join(t for t, _ in current_unit_tuples)
            page_numbers = sorted(list({p for _, p in current_unit_tuples}))

            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document.doc_id}_chunk_{chunk_idx}",
                    doc_id=document.doc_id,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    token_count=self.estimate_tokens(chunk_text),
                    page_numbers=page_numbers,
                    metadata={
                        **document.metadata,
                        "file_name": document.file_name,
                        "file_type": document.file_type,
                        "total_pages": document.total_pages,
                    },
                )
            )

        return chunks
