"""
Document loaders for Word (.docx), Text (.txt), and Markdown (.md) files.
Produces paragraph lists compatible with strwythura's make_chunks() interface.
"""

import pathlib
import re
import unicodedata
from typing import Optional

import chardet


class DocumentLoader:
    """
    Unified document loader that auto-detects file format
    and produces paragraphs[] compatible with strwythura pipeline.
    """

    SUPPORTED_FORMATS = {".docx", ".txt", ".md", ".markdown", ".text", ".hwp"}

    # Korean encoding fallback order
    KO_ENCODINGS = ["utf-8", "euc-kr", "cp949", "utf-16"]

    def __init__(self) -> None:
        self._loaders = {
            ".docx": self._load_docx,
            ".txt": self._load_text,
            ".text": self._load_text,
            ".md": self._load_markdown,
            ".markdown": self._load_markdown,
        }

    def load(self, file_path: str | pathlib.Path) -> list[str]:
        path = pathlib.Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        loader = self._loaders.get(suffix)

        if loader is None:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                f"Supported: {self.SUPPORTED_FORMATS}"
            )

        paragraphs = loader(path)
        return [self._scrub(p) for p in paragraphs if p and p.strip()]

    def load_directory(
        self,
        dir_path: str | pathlib.Path,
        *,
        recursive: bool = True,
    ) -> dict[str, list[str]]:
        """Load all supported files from a directory."""
        dir_path = pathlib.Path(dir_path)

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        results: dict[str, list[str]] = {}
        pattern = "**/*" if recursive else "*"

        for path in sorted(dir_path.glob(pattern)):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
                try:
                    paragraphs = self.load(path)
                    if paragraphs:
                        results[str(path)] = paragraphs
                except Exception as e:
                    print(f"[WARN] Failed to load {path}: {e}")

        return results

    def _load_docx(self, path: pathlib.Path) -> list[str]:
        from docx import Document
        from docx.oxml.text.paragraph import CT_P
        from docx.oxml.table import CT_Tbl
        from docx.table import _Cell, Table
        from docx.text.paragraph import Paragraph

        doc = Document(str(path))
        paragraphs: list[str] = []

        # Process document elements in order (paragraphs, tables, images)
        for element in doc.element.body:
            # Paragraph
            if isinstance(element, CT_P):
                para = Paragraph(element, doc)
                text = para.text.strip()

                # Check for images in paragraph
                if para.runs:
                    for run in para.runs:
                        # Extract image descriptions
                        if run.element.xpath('.//pic:cNvPr'):
                            for img in run.element.xpath('.//pic:cNvPr'):
                                img_name = img.get('name', '')
                                img_desc = img.get('descr', '')
                                if img_name or img_desc:
                                    image_text = f"[Image: {img_name or 'untitled'}]"
                                    if img_desc:
                                        image_text += f" {img_desc}"
                                    paragraphs.append(image_text)

                if text:
                    paragraphs.append(text)

            # Table
            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                table_text = self._extract_table_text(table)
                if table_text:
                    # Add spacing before/after table for better chunking
                    paragraphs.append("")  # Blank line before table
                    paragraphs.extend(table_text)
                    paragraphs.append("")  # Blank line after table

        return paragraphs

    def _extract_table_text(self, table) -> list[str]:
        """
        Extract table text preserving semantic structure.

        Creates both:
        1. Natural language description
        2. Structured row format

        Based on best practices from Unstructured.io and Docling.
        """
        if not table.rows or len(table.rows) == 0:
            return []

        rows_data = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):  # Skip empty rows
                rows_data.append(cells)

        if not rows_data:
            return []

        # Detect header row
        has_header = False
        header_row = None

        if len(rows_data) > 1:
            first_row = rows_data[0]
            # Heuristic: header if all cells are short and non-empty
            if all(c and len(c) < 50 for c in first_row):
                has_header = True
                header_row = first_row

        results = []

        # Format 1: Table summary with header context
        if has_header and len(rows_data) > 1:
            # Create natural language table description
            num_cols = len(header_row)
            num_rows = len(rows_data) - 1

            # Table introduction
            intro = f"[Table: {num_rows} rows with columns: {', '.join(header_row)}]"
            results.append(intro)

            # Format each data row as key-value pairs for better semantic understanding
            for row_idx, data_row in enumerate(rows_data[1:], 1):
                # Ensure data_row has same length as header
                padded_row = data_row + [''] * (num_cols - len(data_row))

                # Create contextual row description with clear separation
                row_parts = []
                for header, value in zip(header_row, padded_row[:num_cols]):
                    if value:  # Only include non-empty values
                        row_parts.append(f"{header}: {value}")

                if row_parts:
                    # Add row separator for clarity
                    row_text = " | ".join(row_parts)
                    # Prefix with "케이스:" or "Case:" to make each row distinct
                    results.append(f"[Row {row_idx}] {row_text}")
                    # Add blank line between rows for better chunking
                    if row_idx < len(rows_data) - 1:
                        results.append("")

        else:
            # No clear header - format as plain rows with context
            results.append(f"[Table: {len(rows_data)} rows]")
            for idx, row in enumerate(rows_data, 1):
                row_text = " | ".join(row)
                if row_text.strip("| "):
                    results.append(f"Row {idx}: {row_text}")

        return results

    def _load_text(self, path: pathlib.Path) -> list[str]:
        raw = path.read_bytes()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"

        # Korean encoding support: try detected, then fallback chain
        content = None
        for enc in [encoding] + self.KO_ENCODINGS:
            try:
                content = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            content = raw.decode("utf-8", errors="replace")

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if len(paragraphs) <= 1 and content.strip():
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            if len(lines) > 1:
                paragraphs = lines

        return paragraphs

    def _load_markdown(self, path: pathlib.Path) -> list[str]:
        # Try UTF-8 first, then Korean encodings
        content = None
        raw = path.read_bytes()
        for enc in self.KO_ENCODINGS:
            try:
                content = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if content is None:
            content = raw.decode("utf-8", errors="replace")

        # Remove code blocks
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"`[^`]+`", "", content)

        # Convert headers to plain text
        content = re.sub(r"#{1,6}\s+", "", content)

        # Convert links to just text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # Remove images
        content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", content)

        # Remove bold/italic markers
        content = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", content)

        # Remove horizontal rules
        content = re.sub(r"^[-*_]{3,}\s*$", "", content, flags=re.MULTILINE)

        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", content)

        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        return paragraphs

    @staticmethod
    def _scrub(text: str) -> str:
        """Normalize Unicode and clean whitespace, preserving Korean characters."""
        # NFC normalization preserves Korean Jamo composition (NFKD can decompose Korean)
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Replace smart quotes
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        return text
