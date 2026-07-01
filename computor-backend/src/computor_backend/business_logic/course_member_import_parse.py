"""Parse uploaded course-member files (CSV / JSON / XLSX / Excel-XML) into rows.

The header aliases mirror the VS Code client-side parsers so the same student
list exports work everywhere. Pure parsing — no database access, no imports.
"""
import csv
import io
import json
import logging
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional, Tuple

from computor_types.course_member_import import CourseMemberImportRow

logger = logging.getLogger(__name__)

# Canonical field name <- header alias (lowercased, trimmed). Union of the
# space/hyphen (CSV/XLSX/XML) and underscore (JSON) variants used by the
# TypeScript parsers, so a header resolves regardless of source format.
_HEADER_ALIASES = {
    "email": "email", "e-mail": "email", "e_mail": "email", "mail": "email",
    "vorname": "given_name", "given name": "given_name", "given_name": "given_name",
    "givenname": "given_name", "firstname": "given_name", "first name": "given_name",
    "first_name": "given_name",
    "familienname": "family_name", "family name": "family_name", "family_name": "family_name",
    "familyname": "family_name", "lastname": "family_name", "last name": "family_name",
    "last_name": "family_name", "nachname": "family_name",
    "matrikelnummer": "student_id", "student id": "student_id", "student_id": "student_id",
    "studentid": "student_id", "matr.-nr.": "student_id", "matr._nr.": "student_id",
    "gruppe": "course_group_title", "group": "course_group_title", "course group": "course_group_title",
    "course_group": "course_group_title", "course_group_title": "course_group_title",
    "role": "course_role_id", "course role": "course_role_id", "course_role": "course_role_id",
    "course_role_id": "course_role_id",
    "incoming": "incoming",
    "kennzahl": "study_id", "study id": "study_id", "study_id": "study_id", "studyid": "study_id",
    "studien-id": "study_id", "studien_id": "study_id",
    "studium": "study_name", "study": "study_name", "study name": "study_name",
    "study_name": "study_name",
    "semester": "semester", "semester im studium": "semester", "semester_im_studium": "semester",
    "anmeldedatum": "registration_date", "registration date": "registration_date",
    "registration_date": "registration_date",
    "anmerkung": "notes", "notes": "notes", "note": "notes", "bemerkung": "notes",
}


def _normalize_header(header: Optional[str]) -> str:
    key = (header or "").strip().lower()
    return _HEADER_ALIASES.get(key, key)


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _build_row(get: Callable[[str], Optional[str]]) -> Optional[CourseMemberImportRow]:
    """Build a row from a field-getter; None if the row has no email."""
    email = get("email")
    if not email:
        return None
    semester: Optional[int] = None
    raw_semester = get("semester")
    if raw_semester:
        try:
            semester = int(str(raw_semester).strip())
        except (ValueError, TypeError):
            semester = None
    return CourseMemberImportRow(
        email=email,
        given_name=get("given_name"),
        family_name=get("family_name"),
        student_id=get("student_id"),
        course_group_title=get("course_group_title"),
        course_role_id=get("course_role_id"),
        incoming=get("incoming"),
        study_id=get("study_id"),
        study_name=get("study_name"),
        semester=semester,
        registration_date=get("registration_date"),
        notes=get("notes"),
    )


def _rows_from_table(headers: List, data_rows: List[List]) -> List[CourseMemberImportRow]:
    columns: dict = {}
    for idx, header in enumerate(headers):
        canon = _normalize_header(header if isinstance(header, str) else str(header) if header is not None else "")
        if canon and canon not in columns:
            columns[canon] = idx
    rows: List[CourseMemberImportRow] = []
    for values in data_rows:
        def get(field, values=values):
            idx = columns.get(field)
            if idx is None or idx >= len(values):
                return None
            return _clean(values[idx])
        row = _build_row(get)
        if row:
            rows.append(row)
    return rows


def _decode_text(data: bytes) -> str:
    # utf-8-sig strips a BOM if present (common in Excel CSV exports).
    return data.decode("utf-8-sig", errors="replace")


def _parse_csv(data: bytes) -> List[CourseMemberImportRow]:
    text = _decode_text(data)
    lines = text.splitlines()
    first = next((ln for ln in lines if ln.strip()), "")
    counts = {d: first.count(d) for d in (",", ";", "\t")}
    delimiter = max(counts, key=counts.get) if any(counts.values()) else ","
    reader = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter)
              if any((c or "").strip() for c in r)]
    if len(reader) < 2:
        return []
    return _rows_from_table(reader[0], reader[1:])


def _extract_array(obj) -> List:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("members", "data", "students", "users", "items", "records"):
            if isinstance(obj.get(key), list):
                return obj[key]
        for value in obj.values():
            if isinstance(value, list):
                return value
    return []


def _parse_json(data: bytes) -> List[CourseMemberImportRow]:
    obj = json.loads(_decode_text(data))
    rows: List[CourseMemberImportRow] = []
    for item in _extract_array(obj):
        if not isinstance(item, dict):
            continue
        normalized = {_normalize_header(str(k)): v for k, v in item.items()}
        row = _build_row(lambda field, n=normalized: _clean(n.get(field)))
        if row:
            rows.append(row)
    return rows


def _parse_xlsx(data: bytes) -> List[CourseMemberImportRow]:
    import pandas as pd

    frame = pd.read_excel(io.BytesIO(data), header=None, dtype=str, engine="openpyxl")
    frame = frame.fillna("")
    grid = [[str(c) for c in row] for row in frame.values.tolist()]
    grid = [r for r in grid if any(c.strip() for c in r)]
    if len(grid) < 2:
        return []
    return _rows_from_table(grid[0], grid[1:])


def _parse_xml(data: bytes) -> List[CourseMemberImportRow]:
    """Excel 2003 'XML Spreadsheet' — Workbook > Worksheet > Table > Row > Cell > Data."""
    try:
        root = ET.fromstring(_decode_text(data))
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}")

    def lname(el) -> str:
        return el.tag.rsplit("}", 1)[-1]

    worksheet = next((el for el in root.iter() if lname(el) == "Worksheet"), None)
    if worksheet is None:
        raise ValueError("Invalid Excel XML: no Worksheet element")
    table = next((el for el in worksheet.iter() if lname(el) == "Table"), None)
    if table is None:
        raise ValueError("Invalid Excel XML: no Table element")

    def cell_values(row_el) -> List[str]:
        values: List[str] = []
        for cell in (c for c in row_el if lname(c) == "Cell"):
            data_el = next((d for d in cell if lname(d) == "Data"), None)
            text = data_el.text if data_el is not None else cell.text
            values.append(text or "")
        return values

    grid = [cell_values(r) for r in table if lname(r) == "Row"]
    grid = [r for r in grid if any((c or "").strip() for c in r)]
    if len(grid) < 2:
        return []
    return _rows_from_table(grid[0], grid[1:])


def _detect_format(filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("csv", "tsv", "txt"):
        return "csv"
    if ext == "json":
        return "json"
    if ext in ("xlsx", "xls"):
        return "xlsx"
    if ext == "xml":
        return "xml"
    head = data[:512].lstrip()
    if head[:2] == b"PK" or head[:4] == b"\xd0\xcf\x11\xe0":
        return "xlsx"
    if head[:5] == b"<?xml" or b"Workbook" in head:
        return "xml"
    if head[:1] in (b"{", b"["):
        return "json"
    return "csv"


def parse_course_member_file(filename: str, data: bytes) -> Tuple[List[CourseMemberImportRow], str]:
    """Parse an uploaded member file into rows. Returns (rows, detected_format).

    Raises ValueError on an unsupported/invalid file.
    """
    fmt = _detect_format(filename or "", data)
    parsers = {
        "csv": _parse_csv,
        "json": _parse_json,
        "xlsx": _parse_xlsx,
        "xml": _parse_xml,
    }
    parser = parsers.get(fmt)
    if parser is None:
        raise ValueError("Unsupported file format. Use CSV, JSON, XLSX or Excel XML.")
    try:
        return parser(data), fmt
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface a clean message to the client
        logger.warning("Failed to parse %s member file: %s", fmt, exc)
        raise ValueError(f"Failed to parse {fmt.upper()} file: {exc}")
