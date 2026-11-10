from pathlib import Path
from typing import Any
import re

class DocumentParseError(RuntimeError):
    pass

def markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks, current, current_type = [], [], "paragraph"
    def flush():
        nonlocal current, current_type
        value = "\\n".join(current).strip()
        if value:
            blocks.append({"type": current_type, "text": value})
        current, current_type = [], "paragraph"

    for line in markdown.splitlines():
        line = line.strip()
        if not line:
            flush()
        elif line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            blocks.append({"type": "heading", "level": min(level, 6),
                           "text": line[level:].strip()})
        elif re.match(r"^([-*+] |\\d+[.)] )", line):
            if current and current_type != "list":
                flush()
            current_type = "list"
            current.append(line)
        else:
            if current and current_type == "list":
                flush()
            current_type = "paragraph"
            current.append(line)
    flush()
    return blocks

def parse_document(file_path: str | Path, original_filename: str | None = None):
    path = Path(file_path)
    ext = path.suffix.lower()
    filename = original_filename or path.name
    if not path.is_file():
        raise DocumentParseError("Uploaded file not found on server.")
    try:
        if ext in {".txt", ".md"}:
            markdown = path.read_text(encoding="utf-8-sig", errors="replace")
        elif ext in {".pdf", ".docx"}:
            try:
                from docling.document_converter import DocumentConverter
            except ImportError as exc:
                raise DocumentParseError(
                    "Docling is not installed. Run pip install -r requirements.txt."
                ) from exc
            converter = DocumentConverter()
            converted = converter.convert(str(path))
            markdown = converted.document.export_to_markdown()
        else:
            raise DocumentParseError(f"Unsupported file extension: {ext}")
        markdown = markdown.strip()
        if not markdown:
            raise DocumentParseError(
                "No text extracted. File may be empty, scanned, encrypted or unsupported."
            )
        blocks = markdown_blocks(markdown)
        return {"filename": filename, "file_type": ext.lstrip("."),
                "markdown": markdown, "blocks": blocks,
                "character_count": len(markdown), "block_count": len(blocks)}
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Could not parse {filename}: {exc}") from exc
