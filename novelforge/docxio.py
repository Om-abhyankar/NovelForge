"""
Word document reading and writing.

Two shapes of document exist in a NovelForge project:

  * **Field sheets** - character bibles, location profiles, plot threads.
    A heading per section, then a two-column table: field name on the left,
    your answer on the right. Tables parse back reliably even after you have
    edited them in Word, which is why they are used instead of "Label: value"
    paragraphs.

  * **Prose documents** - scenes and chapters, in standard manuscript format.

Everything is saved through atomic.save_via_atomic so a crash or a OneDrive
lock can never leave a truncated document behind.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .atomic import save_via_atomic

# --------------------------------------------------------------------------
# Palette used inside generated documents (print-friendly)
# --------------------------------------------------------------------------

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x6E, 0x6E, 0x6E)
ACCENT = RGBColor(0x6B, 0x46, 0x22)
SHADE_HEADER = "EFE7D9"
SHADE_FIELD = "F7F3EB"

# Paragraphs the tool generates rather than the writer are marked with these
# style names, so reading a document back can skip them without guessing.
# Guessing from position and formatting used to eat a legitimately centred
# bold opening line - an epigraph, a letter heading, a chapter title.
STYLE_SCENE_TITLE = "NF Scene Title"
STYLE_SCENE_NOTE = "NF Scene Note"
GENERATED_STYLES = {STYLE_SCENE_TITLE, STYLE_SCENE_NOTE}

# A field sheet's left column width; the right column takes the remainder.
LABEL_WIDTH = Inches(2.15)
VALUE_WIDTH = Inches(4.35)


# ==========================================================================
# Low-level OOXML helpers
# ==========================================================================


def _set_style_font(style, name: str, size: Optional[int] = None,
                    bold: Optional[bool] = None,
                    italic: Optional[bool] = None,
                    color: Optional[RGBColor] = None) -> None:
    """Apply a font to a style, including the east-Asian and complex-script slots."""
    font = style.font
    font.name = name
    if size is not None:
        font.size = Pt(size)
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic
    if color is not None:
        font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(slot), name)


def add_field(paragraph, instruction: str, placeholder: str = "") -> None:
    """
    Insert a Word field code (PAGE, NUMPAGES, TOC ...).

    Word evaluates the field when the document opens, which is how page
    numbers and a table of contents stay correct without us computing them.
    """
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    if placeholder:
        text = OxmlElement("w:t")
        text.text = placeholder
        run._r.append(text)
    run._r.append(end)


def request_field_update(doc: Document) -> None:
    """Ask Word to refresh all fields on open (needed for the TOC to populate)."""
    settings = doc.settings.element
    existing = settings.find(qn("w:updateFields"))
    if existing is None:
        existing = OxmlElement("w:updateFields")
        settings.append(existing)
    existing.set(qn("w:val"), "true")


def set_page_numbering(section, start: Optional[int] = None,
                       restart: bool = False) -> None:
    sect_pr = section._sectPr
    existing = sect_pr.find(qn("w:pgNumType"))
    if existing is None:
        existing = OxmlElement("w:pgNumType")
        sect_pr.append(existing)
    if restart and start is None:
        start = 1
    if start is not None:
        existing.set(qn("w:start"), str(start))


def shade_cell(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def repeat_as_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))


def add_bookmark(paragraph, name: str, bookmark_id: int) -> None:
    """Named anchor so compiled documents can link back to a chapter."""
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def prevent_widows(paragraph, keep_with_next: bool = False) -> None:
    fmt = paragraph.paragraph_format
    fmt.widow_control = True
    if keep_with_next:
        fmt.keep_with_next = True


# ==========================================================================
# Document factories
# ==========================================================================


def sheet_document(margin: float = 0.9) -> Document:
    """
    A reference document - character sheet, world bible, outline.

    Single spaced, no first-line indent, tighter margins than a manuscript
    because these are working documents rather than submissions.
    """
    doc = Document()

    normal = doc.styles["Normal"]
    _set_style_font(normal, "Calibri", 11, color=INK)
    pf = normal.paragraph_format
    pf.space_after = Pt(4)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.08
    pf.first_line_indent = Pt(0)

    for level, size in ((1, 20), (2, 13), (3, 11)):
        try:
            style = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        _set_style_font(style, "Calibri Light", size, bold=(level > 1),
                        color=ACCENT if level == 1 else INK)
        style.paragraph_format.space_before = Pt(14 if level > 1 else 0)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True

    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.top_margin = Inches(margin)
        section.bottom_margin = Inches(margin)
        section.left_margin = Inches(margin)
        section.right_margin = Inches(margin)

    return doc


def manuscript_document(font: str = "Times New Roman", size: int = 12,
                        line_spacing: float = 2.0, margin: float = 1.0,
                        first_line_indent: float = 0.5) -> Document:
    """
    A document in standard manuscript format.

    US Letter, one-inch margins, double spaced, half-inch first-line indent,
    no extra space between paragraphs. This is what agents and editors expect.
    """
    doc = Document()

    normal = doc.styles["Normal"]
    _set_style_font(normal, font, size, color=INK)
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    pf.line_spacing = line_spacing
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    pf.first_line_indent = Inches(first_line_indent)
    pf.widow_control = True

    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.top_margin = Inches(margin)
        section.bottom_margin = Inches(margin)
        section.left_margin = Inches(margin)
        section.right_margin = Inches(margin)

    return doc


# ==========================================================================
# Paragraph helpers
# ==========================================================================


def add_title_block(doc: Document, title: str, subtitle: str = "",
                    kicker: str = "") -> None:
    """The masthead at the top of a reference sheet."""
    if kicker:
        p = doc.add_paragraph()
        run = p.add_run(kicker.upper())
        run.font.size = Pt(8)
        run.font.bold = True
        run.font.color.rgb = MUTED
        run.font.name = "Calibri"
        p.paragraph_format.space_after = Pt(0)

    heading = doc.add_heading(title, level=1)
    heading.paragraph_format.space_after = Pt(2)

    if subtitle:
        p = doc.add_paragraph()
        run = p.add_run(subtitle)
        run.italic = True
        run.font.size = Pt(10)
        run.font.color.rgb = MUTED
        p.paragraph_format.space_after = Pt(10)


def add_note(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    p.paragraph_format.space_after = Pt(8)


def add_divider(doc: Document) -> None:
    p = doc.add_paragraph()
    pr = p._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D6CBB8")
    borders.append(bottom)
    pr.append(borders)
    p.paragraph_format.space_after = Pt(8)


def add_checklist(doc: Document, items: Sequence[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run("☐  ").font.size = Pt(11)   # ballot box
        p.add_run(item)
        p.paragraph_format.space_after = Pt(2)


# ==========================================================================
# Field sheets
# ==========================================================================

# A section is (heading, [(field_name, hint), ...])
Section = Tuple[str, Sequence[Tuple[str, str]]]


def _field_table(doc: Document, fields: Sequence[Tuple[str, str]],
                 values: Optional[Dict[str, str]] = None):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False

    for name, hint in fields:
        row = table.add_row()
        keep_row_together(row)
        label_cell, value_cell = row.cells[0], row.cells[1]
        label_cell.width = LABEL_WIDTH
        value_cell.width = VALUE_WIDTH
        shade_cell(label_cell, SHADE_FIELD)

        label_p = label_cell.paragraphs[0]
        label_run = label_p.add_run(name)
        label_run.bold = True
        label_run.font.size = Pt(10)
        label_p.paragraph_format.space_after = Pt(0)

        if hint:
            hint_p = label_cell.add_paragraph()
            hint_run = hint_p.add_run(hint)
            hint_run.italic = True
            hint_run.font.size = Pt(8)
            hint_run.font.color.rgb = MUTED
            hint_p.paragraph_format.space_after = Pt(0)

        existing = (values or {}).get(name, "")
        if existing:
            for i, line in enumerate(str(existing).split("\n")):
                p = value_cell.paragraphs[0] if i == 0 else value_cell.add_paragraph()
                p.add_run(line).font.size = Pt(10)
        else:
            value_cell.paragraphs[0].add_run("").font.size = Pt(10)

    return table


def write_field_sheet(path: Path | str, title: str, sections: Sequence[Section],
                      subtitle: str = "", kicker: str = "", note: str = "",
                      values: Optional[Dict[str, str]] = None) -> Path:
    """Create (or overwrite) a field sheet. Existing values can be carried over."""
    doc = sheet_document()
    add_title_block(doc, title, subtitle, kicker)
    if note:
        add_note(doc, note)
        add_divider(doc)

    for heading, fields in sections:
        if heading:
            doc.add_heading(heading, level=2)
        _field_table(doc, fields, values)

    return save_via_atomic(path, doc.save)


def read_field_sheet(path: Path | str) -> Dict[str, str]:
    """
    Pull field values back out of a sheet the user may have edited in Word.

    Keys are the left column's first paragraph; the hint line is ignored.
    """
    path = Path(path)
    if not path.exists():
        return {}
    try:
        doc = Document(str(path))
    except Exception:
        return {}

    values: Dict[str, str] = {}
    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) < 2:
                continue
            paras = [p.text.strip() for p in cells[0].paragraphs if p.text.strip()]
            if not paras:
                continue
            key = paras[0]
            value_lines = [p.text.strip() for p in cells[1].paragraphs]
            value = "\n".join(line for line in value_lines if line).strip()
            # A later duplicate key should not wipe an earlier filled answer.
            if key in values and not value:
                continue
            values[key] = value
    return values


# ==========================================================================
# Prose documents
# ==========================================================================


def _ensure_generated_styles(doc: Document, font: str, size: int) -> None:
    """Create the marker styles used to tag tool-generated paragraphs."""
    from docx.enum.style import WD_STYLE_TYPE

    for name in (STYLE_SCENE_TITLE, STYLE_SCENE_NOTE):
        try:
            doc.styles[name]
            continue
        except KeyError:
            pass
        try:
            style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        except Exception:
            continue
        style.base_style = doc.styles["Normal"]
        style.hidden = False
        style.quick_style = False
        _set_style_font(style, font, size)
        fmt = style.paragraph_format
        fmt.first_line_indent = Pt(0)
        if name == STYLE_SCENE_NOTE:
            fmt.line_spacing = 1.0


def write_prose(path: Path | str, title: str, body: str,
                font: str = "Times New Roman", size: int = 12,
                line_spacing: float = 2.0, margin: float = 1.0,
                first_line_indent: float = 0.5,
                synopsis: str = "", show_title: bool = True) -> Path:
    """Write a scene or chapter as a standard-manuscript-format document."""
    doc = manuscript_document(font, size, line_spacing, margin, first_line_indent)
    _ensure_generated_styles(doc, font, size)

    if show_title and title:
        p = doc.add_paragraph()
        try:
            p.style = doc.styles[STYLE_SCENE_TITLE]
        except KeyError:
            pass
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_after = Pt(size * 2)
        run = p.add_run(title)
        run.bold = True

    if synopsis:
        p = doc.add_paragraph()
        try:
            p.style = doc.styles[STYLE_SCENE_NOTE]
        except KeyError:
            pass
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(size)
        run = p.add_run(f"[Synopsis: {synopsis}]")
        run.italic = True
        run.font.size = Pt(max(9, size - 2))
        run.font.color.rgb = MUTED

    for block in split_paragraphs(body):
        para = doc.add_paragraph()
        if block == "#":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.first_line_indent = Pt(0)
            para.add_run("#")
        else:
            para.add_run(block)

    return save_via_atomic(path, doc.save)


def _is_generated(para, index: int) -> bool:
    """
    True for a paragraph this tool wrote rather than the author.

    Style names are authoritative. The positional fallback exists only for
    documents written before the styles were introduced, and is deliberately
    narrow: index 0 alone, and only when centred AND bold, which is exactly
    what the old writer produced.
    """
    text = para.text.strip()
    if not text:
        return False
    if text.startswith("[Synopsis:") and text.endswith("]"):
        return True
    try:
        if para.style is not None and para.style.name in GENERATED_STYLES:
            return True
    except (AttributeError, KeyError):
        pass
    if index == 0 and text != "#" and \
            para.alignment == WD_ALIGN_PARAGRAPH.CENTER:
        styled = False
        try:
            styled = para.style is not None and \
                para.style.name not in GENERATED_STYLES and \
                para.style.name != "Normal"
        except (AttributeError, KeyError):
            styled = False
        if not styled and any(r.bold for r in para.runs if r.text.strip()):
            return True
    return False


def read_prose(path: Path | str) -> str:
    """
    Read a prose document back as plain text with blank-line paragraph breaks.

    Returns "" both for a missing file and for an unreadable one; callers that
    must tell those apart should use `prose_readable` first.
    """
    path = Path(path)
    if not path.exists():
        return ""
    try:
        doc = Document(str(path))
    except Exception:
        return ""

    blocks: List[str] = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text or _is_generated(para, i):
            continue
        blocks.append(text)
    return "\n\n".join(blocks)


def prose_readable(path: Path | str) -> bool:
    """
    Whether a document can be opened at all.

    Used before any operation that would replace content based on what was
    read: an unreadable file must never be treated as an empty one.
    """
    path = Path(path)
    if not path.exists():
        return False
    try:
        Document(str(path))
        return True
    except Exception:
        return False


def read_paragraphs_with_format(path: Path | str) -> List[dict]:
    """
    Read prose preserving run-level italic/bold, for the compile step.

    Returns a list of {"alignment": str, "runs": [{"text", "bold", "italic", ...}]}.
    """
    path = Path(path)
    if not path.exists():
        return []
    try:
        doc = Document(str(path))
    except Exception:
        return []

    out: List[dict] = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text or _is_generated(para, i):
            continue
        centred = para.alignment == WD_ALIGN_PARAGRAPH.CENTER
        runs = [
            {
                "text": run.text,
                "bold": run.bold,
                "italic": run.italic,
                "underline": run.underline,
                "strike": run.font.strike,
                "small_caps": run.font.small_caps,
                "superscript": run.font.superscript,
                "subscript": run.font.subscript,
            }
            for run in para.runs
            if run.text
        ]
        if not runs:
            runs = [{"text": text, "bold": None, "italic": None, "underline": None,
                     "strike": None, "small_caps": None, "superscript": None,
                     "subscript": None}]
        out.append({"centred": centred, "runs": runs})
    return out


def clone_runs(spec: dict, paragraph) -> None:
    """Re-create formatted runs from read_paragraphs_with_format into a paragraph."""
    for run_spec in spec["runs"]:
        run = paragraph.add_run(run_spec["text"])
        run.bold = run_spec.get("bold")
        run.italic = run_spec.get("italic")
        run.underline = run_spec.get("underline")
        if run_spec.get("strike"):
            run.font.strike = True
        if run_spec.get("small_caps"):
            run.font.small_caps = True
        if run_spec.get("superscript"):
            run.font.superscript = True
        if run_spec.get("subscript"):
            run.font.subscript = True


# ==========================================================================
# Tables of arbitrary data (timeline, trackers, submission log)
# ==========================================================================


def add_data_table(doc: Document, headers: Sequence[str],
                   rows: Sequence[Sequence[str]],
                   widths: Optional[Sequence[float]] = None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = widths is None

    header_row = table.rows[0]
    repeat_as_header(header_row)
    for idx, name in enumerate(headers):
        cell = header_row.cells[idx]
        shade_cell(cell, SHADE_HEADER)
        p = cell.paragraphs[0]
        run = p.add_run(str(name))
        run.bold = True
        run.font.size = Pt(9)
        if widths:
            cell.width = Inches(widths[idx])

    for row_values in rows:
        row = table.add_row()
        keep_row_together(row)
        for idx in range(len(headers)):
            value = str(row_values[idx]) if idx < len(row_values) else ""
            cell = row.cells[idx]
            if widths:
                cell.width = Inches(widths[idx])
            for j, line in enumerate(value.split("\n")):
                p = cell.paragraphs[0] if j == 0 else cell.add_paragraph()
                p.add_run(line).font.size = Pt(9)
                p.paragraph_format.space_after = Pt(0)
    return table


# ==========================================================================
# Text utilities
# ==========================================================================


def split_paragraphs(text: str) -> List[str]:
    """
    Split editor text into Word paragraphs. Every newline starts a new one.

    An earlier version treated a single newline as a soft wrap and joined the
    lines with a space, which silently destroyed deliberate line breaks - fatal
    for verse, epigraphs, letters, lists and song lyrics. In a word processor
    pressing Enter makes a new paragraph, so that is what happens here.
    Runs of blank lines collapse, because they carry no additional meaning
    once each block is its own paragraph.
    """
    if not text:
        return []
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in normalised.split("\n") if line.strip()]


def count_in_document(path: Path | str, pattern) -> int:
    """How many times a pattern occurs in a document, body and tables."""
    try:
        doc = Document(str(path))
    except Exception:
        return 0
    total = 0
    for paragraph in _all_paragraphs(doc):
        for run in paragraph.runs:
            total += len(pattern.findall(run.text))
    return total


def _all_paragraphs(doc: Document):
    """Every paragraph in the body and inside every table cell."""
    for paragraph in doc.paragraphs:
        yield paragraph
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def replace_in_document(path: Path | str, pattern, replacement: str) -> int:
    """
    Replace inside a Word document without flattening it.

    Done run by run rather than by rewriting the file from plain text, so
    italics, bold and any styling the writer applied in Word survive. Field
    sheets are covered too, because their content lives in table cells.

    The one thing this cannot see is a match split across two runs - Word
    splits runs at every formatting change and sometimes at a spell-check
    boundary, so "Ada" could in principle be stored as "A" + "da". That is
    rare in practice and the alternative, rebuilding every paragraph, would
    lose the formatting this exists to protect.

    Returns how many replacements were made; 0 leaves the file untouched.
    """
    from .atomic import save_via_atomic

    path = Path(path)
    try:
        doc = Document(str(path))
    except Exception as exc:
        raise OSError(f"{path.name} could not be opened: {exc}") from exc

    total = 0
    for paragraph in _all_paragraphs(doc):
        for run in paragraph.runs:
            if not run.text:
                continue
            new_text, count = pattern.subn(replacement, run.text)
            if count:
                run.text = new_text
                total += count
    if total:
        save_via_atomic(path, doc.save)
    return total


def word_count(text: str) -> int:
    """
    Count words the way writers and publishers do: whitespace-delimited tokens.

    A token needs at least one alphanumeric character, so a lone em dash or a
    scene-break hash is not counted as a word.
    """
    if not text:
        return 0
    return sum(1 for tok in text.split() if any(ch.isalnum() for ch in tok))


def docx_word_count(path: Path | str) -> int:
    return word_count(read_prose(path))


def docx_mtime(path: Path | str) -> float:
    path = Path(path)
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
