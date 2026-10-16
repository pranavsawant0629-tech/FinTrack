import re
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from pypdf import PdfReader

import logging

logger = logging.getLogger(__name__)

class PageContent(BaseModel):
    page_number: int
    text: str


class ParsedDocument(BaseModel):
    doc_id: str
    file_name: str
    file_path: str
    file_type: str
    total_pages: int
    full_text: str
    pages: list[PageContent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentParser:
    """
    Parses and cleans raw financial documents (PDF, TXT, Markdown)
    into structured ParsedDocument representations with page provenance.
    """

    # Targeted font-encoding glyph repair for documents with custom embedded font mappings (e.g. SEBI igrbrochure.pdf)
    _SEBI_FONT_GLYPH_MAP = {
        # Core Latin alphabet corruption
        "\u0176": "n",  # Ŷ -> n
        "\u018c": "r",  # ƌ -> r
        "\u0110": "c",  # Đ -> c
        "\u0175": "m",  # ŵ -> m
        "\u01c0": "v",  # ǀ -> v
        "\u010f": "b",  # ď -> b
        "\u01c1": "w",  # ǁ -> w
        "\u01c7": "y",  # Ǉ -> y
        "\u01c6": "x",  # ǆ -> x
        "\u018b": "q",  # Ƌ -> q
        # Greek numeric digits verified in font encoding (0-9)
        "\u03ec": "0",  # Ϭ -> 0
        "\u03ed": "1",  # ϭ -> 1
        "\u03ee": "2",  # Ϯ -> 2
        "\u03ef": "3",  # ϯ -> 3
        "\u03f0": "4",  # ϰ -> 4
        "\u03f1": "5",  # ϱ -> 5
        "\u03f2": "6",  # ϲ -> 6
        "\u03f3": "7",  # ϳ -> 7
        "\u03f4": "8",  # ϴ -> 8
        "\u03f5": "9",  # ϵ -> 9
        # Verified punctuation in font encoding
        "\u037e": "(",  # ; -> (
        "\u037f": ")",  # Ϳ -> )
        "\u035a": "'",  # ͚ -> '
        "\u035b": "'",  # ͛ -> '
    }

    @classmethod
    def detect_corruption_indicators(cls, text: str) -> dict[str, Any]:
        """
        Lightweight ingestion safeguard: analyzes extracted text for abnormal proportions
        of unusual Unicode ranges (e.g. Latin Extended, Greek, Private Use Area) that indicate
        unrepaired PDF font-subset or CMap encoding corruption.
        """
        if not text:
            return {"is_corrupted": False, "unusual_count": 0, "unusual_ratio": 0.0, "sample_chars": []}

        unusual_chars = []
        for ch in text:
            code = ord(ch)
            if code <= 127 or ch in "\u20b9\u2018\u2019\u201c\u201d\u2010\u2013\u2014\u2022\u2023\u2026\u00a0":
                continue
            # Latin Extended, Greek/Coptic, or Private Use Area indicating font glyph mapping issues
            if (0x0100 <= code <= 0x024F) or (0x0370 <= code <= 0x03FF) or (0xE000 <= code <= 0xF8FF):
                unusual_chars.append(ch)

        unusual_count = len(unusual_chars)
        unusual_ratio = unusual_count / max(1, len(text))
        is_corrupted = (unusual_count >= 10 and unusual_ratio > 0.005)

        return {
            "is_corrupted": is_corrupted,
            "unusual_count": unusual_count,
            "unusual_ratio": round(unusual_ratio, 4),
            "sample_chars": sorted(list(set(unusual_chars)))[:10],
        }

    @classmethod
    def repair_font_encoding(cls, text: str, file_name: str = "") -> str:
        """
        Repairs systematic font-encoding corruption from custom embedded PDF font mappings.
        Targeted specifically to verified glyph mappings without affecting standard documents.
        """
        if not text:
            return ""

        # Only apply if document has the verified font corruption signature or matches filename
        has_font_signature = "\u0176" in text or "\u018c" in text or "\u0110" in text
        if not has_font_signature and "igrbrochure" not in file_name.lower():
            return text

        for glyph, replacement in cls._SEBI_FONT_GLYPH_MAP.items():
            text = text.replace(glyph, replacement)

        # In igrbrochure's embedded font, capital 'R' was mapped to left single quote (U+2018)
        if "igrbrochure" in file_name.lower() or has_font_signature:
            text = text.replace("\u2018", "R")

        return text

    @classmethod
    def clean_text(cls, text: str, file_name: str = "") -> str:
        """
        Cleans and normalizes extracted text:
        - Repairs systematic PDF font-encoding glyph corruption if present.
        - Normalizes Unicode spaces and control characters.
        - Fixes broken hyphenated words at line breaks.
        - Reduces multiple blank lines to double newlines.
        - Strips extraneous trailing whitespace.
        """
        if not text:
            return ""

        # Apply targeted font repair if document exhibits corrupted embedded font encoding
        text = cls.repair_font_encoding(text, file_name=file_name)

        # Normalize carriage returns and non-breaking spaces
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\u00a0", " ").replace("\u200b", "")

        # Fix hyphenated words broken across lines (e.g. 'inves-\ntor' -> 'investor')
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

        # Replace excessive whitespace within lines (tabs, multiple spaces)
        text = re.sub(r"[ \t]+", " ", text)

        # Normalize multiple newlines (preserve paragraphs with at most 2 newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def parse_pdf(self, file_path: str | Path, extra_metadata: dict[str, Any] | None = None) -> ParsedDocument:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        reader = PdfReader(str(path))
        pages: list[PageContent] = []
        cleaned_page_texts: list[str] = []

        for idx, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            cleaned = self.clean_text(raw_text, file_name=path.name)
            if cleaned:
                pages.append(PageContent(page_number=idx + 1, text=cleaned))
                cleaned_page_texts.append(cleaned)

        full_text = "\n\n".join(cleaned_page_texts)

        # Corruption detection safeguard
        corruption_check = self.detect_corruption_indicators(full_text)
        if corruption_check["is_corrupted"]:
            logger.warning(
                f"Potential font-encoding corruption detected in [{path.name}]: "
                f"{corruption_check['unusual_count']} unusual glyphs ({corruption_check['unusual_ratio']:.2%}). "
                f"Samples: {corruption_check['sample_chars']}"
            )

        metadata = {
            "source_type": "pdf",
            "extracted_pages": len(pages),
            "has_corruption_warning": corruption_check["is_corrupted"],
            **(extra_metadata or {})
        }

        return ParsedDocument(
            doc_id=path.stem,
            file_name=path.name,
            file_path=str(path),
            file_type="pdf",
            total_pages=len(reader.pages),
            full_text=full_text,
            pages=pages,
            metadata=metadata
        )

    def parse_text(self, file_path: str | Path, extra_metadata: dict[str, Any] | None = None) -> ParsedDocument:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {path}")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        cleaned = self.clean_text(raw_text)
        page = PageContent(page_number=1, text=cleaned)

        metadata = {
            "source_type": path.suffix.lstrip("."),
            **(extra_metadata or {})
        }

        return ParsedDocument(
            doc_id=path.stem,
            file_name=path.name,
            file_path=str(path),
            file_type=path.suffix.lstrip("."),
            total_pages=1,
            full_text=cleaned,
            pages=[page],
            metadata=metadata
        )

    def parse_file(self, file_path: str | Path, extra_metadata: dict[str, Any] | None = None) -> ParsedDocument:
        path = Path(file_path).resolve()
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self.parse_pdf(path, extra_metadata=extra_metadata)
        elif suffix in [".txt", ".md", ".markdown"]:
            return self.parse_text(path, extra_metadata=extra_metadata)
        else:
            raise ValueError(f"Unsupported document format: {suffix}. Supported: .pdf, .txt, .md")
