import re
from collections import Counter
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

import pymupdf
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook

CLAUSE_RE = re.compile(r"^(\d+(?:\.\d+){1,6}|\d{1,3}[.)])[.)]?\s+(.*)$")
INLINE_CLAUSE_RE = re.compile(r"(?<=[.;:])\s+(\d+(?:\.\d+){1,6})[.)]\s+")


@dataclass(frozen=True)
class Clause:
    document: str
    clause: str
    text: str
    page: int | None = None

    def render(self) -> str:
        page = f", стр. {self.page}" if self.page else ""
        return f"[{self.document}; п. {self.clause}{page}] {self.text}"


def display_name(path: Path) -> str:
    name = path.name
    return name[33:] if re.match(r"^[0-9a-f]{32}_", name) else name


def split_inline_clauses(text: str) -> list[str]:
    """Split only consecutive siblings, not arbitrary numbers or cross-references."""
    first = CLAUSE_RE.match(text)
    if not first:
        return [text]
    previous = first.group(1).rstrip(".)").split(".")
    cuts = [0]
    for match in INLINE_CLAUSE_RE.finditer(text):
        if re.search(r"\b(?:п|пп|см|разд)\.\s*$", text[: match.start(1)], re.IGNORECASE):
            continue
        number = match.group(1).split(".")
        if number[:-1] == previous[:-1] and int(number[-1]) == int(previous[-1]) + 1:
            cuts.append(match.start(1))
            previous = number
    cuts.append(len(text))
    return [text[start:end].strip() for start, end in pairwise(cuts)]


def unique_references(clauses: list[Clause]) -> list[Clause]:
    """Repeated printed numbers (e.g. appendices) must not overwrite each other."""
    totals = Counter(item.clause for item in clauses)
    seen: Counter[str] = Counter()
    result = []
    for item in clauses:
        seen[item.clause] += 1
        if totals[item.clause] > 1:
            item = replace(item, clause=f"{item.clause} [фрагмент {seen[item.clause]}]")
        result.append(item)
    return result


def _group_numbered(lines: list[tuple[str, int | None]], document: str) -> list[Clause]:
    clauses: list[Clause] = []
    current_number: str | None = None
    current_page: int | None = None
    current_parts: list[str] = []

    def flush() -> None:
        if current_number and current_parts:
            clauses.append(
                Clause(
                    document=document,
                    clause=current_number,
                    text=" ".join(current_parts).strip(),
                    page=current_page,
                )
            )

    expanded = [
        (part, page) for raw, page in lines for part in split_inline_clauses(" ".join(raw.split()))
    ]
    for line_index, (raw, page) in enumerate(expanded, 1):
        text = " ".join(raw.split())
        if not text:
            continue
        match = CLAUSE_RE.match(text)
        if match:
            flush()
            current_number = match.group(1).rstrip(".)")
            current_page = page
            current_parts = [match.group(2).strip()]
        elif current_number:
            current_parts.append(text)
        else:
            current_number = f"текст {line_index}"
            current_page = page
            current_parts = [text]
    flush()
    return unique_references(clauses)


def parse_docx(path: Path) -> list[Clause]:
    document = Document(path)
    clauses: list[Clause] = []
    paragraph_index = table_index = 0
    name = display_name(path)
    # Body order matters: a table belongs where it occurs, not at the end of a file.
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            paragraph_index += 1
            text = " ".join(block.text.split())
            if not text:
                continue
            for part in split_inline_clauses(text):
                match = CLAUSE_RE.match(part)
                reference = match.group(1).rstrip(".)") if match else f"абзац {paragraph_index}"
                # Word's automatic numbering is not in paragraph.text. Use the
                # actual paragraph locator instead of inventing a printed number.
                clauses.append(Clause(name, reference, match.group(2) if match else part))
        elif isinstance(block, Table):
            table_index += 1
            for row_index, row in enumerate(block.rows, 1):
                cells = []
                seen_cells = set()
                for cell in row.cells:
                    if cell._tc not in seen_cells:
                        cells.append(" ".join(cell.text.split()))
                        seen_cells.add(cell._tc)
                if any(cells):
                    clauses.append(
                        Clause(
                            name, f"таблица {table_index}, строка {row_index}", " | ".join(cells)
                        )
                    )
    return unique_references(clauses)


def parse_pdf(path: Path) -> list[Clause]:
    lines: list[tuple[str, int | None]] = []
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document, 1):
            lines.extend((line, page_index) for line in page.get_text().splitlines())
    return _group_numbered(lines, display_name(path))


def parse_xlsx(path: Path) -> list[Clause]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    clauses: list[Clause] = []
    for sheet in workbook.worksheets:
        for row_index, row in enumerate(sheet.iter_rows(values_only=True), 1):
            values = [
                str(value).strip() for value in row if value is not None and str(value).strip()
            ]
            if values:
                clauses.append(
                    Clause(
                        document=display_name(path),
                        clause=f"{sheet.title}!{row_index}",
                        text=" | ".join(values),
                    )
                )
    return clauses


def parse_documents(paths: list[Path]) -> list[Clause]:
    parsers = {".docx": parse_docx, ".pdf": parse_pdf, ".xlsx": parse_xlsx}
    clauses: list[Clause] = []
    names = [display_name(path).casefold() for path in paths]
    if len(names) != len(set(names)):
        raise ValueError(
            "Одинаковые имена документов в одном комплекте: переименуйте файлы для однозначных ссылок."
        )
    for path in paths:
        parsed = parsers[path.suffix.lower()](path)
        if not parsed:
            raise ValueError(
                f"Не извлечён текст: {display_name(path)}. Проверьте файл; OCR не поддерживается."
            )
        clauses.extend(parsed)
    return clauses
