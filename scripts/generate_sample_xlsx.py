import os
import sys
import zipfile
from xml.sax.saxutils import escape

from table_utils import BOOL_COLUMNS, HEADERS, STRING_COLUMNS, build_rows

OUTPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "../samples/sample.xlsx"
ROW_COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 60


def col_letter(index):
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def build_shared_strings(rows):
    strings = []
    index_by_value = {}

    def intern(value):
        if value not in index_by_value:
            index_by_value[value] = len(strings)
            strings.append(value)
        return index_by_value[value]

    header_indices = [intern(h) for h in HEADERS]

    row_string_indices = []
    for row in rows:
        indices = {}
        for col in STRING_COLUMNS:
            value = row.get(col)
            if value:
                indices[col] = intern(value)
        row_string_indices.append(indices)

    return strings, header_indices, row_string_indices


def cell_xml(ref, value, is_string=False, is_bool=False):
    if value is None:
        return ""
    if is_bool:
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if is_string:
        return f'<c r="{ref}" t="s"><v>{value}</v></c>'
    return f'<c r="{ref}"><v>{value}</v></c>'


def build_sheet_xml(rows, header_indices, row_string_indices):
    xml_rows = []

    header_cells = "".join(
        cell_xml(f"{col_letter(i)}1", header_indices[i], is_string=True)
        for i in range(len(HEADERS))
    )
    xml_rows.append(f'<row r="1">{header_cells}</row>')

    for row_num, (row, str_indices) in enumerate(zip(rows, row_string_indices), start=2):
        cells = []
        for i, header in enumerate(HEADERS):
            ref = f"{col_letter(i)}{row_num}"
            if header in BOOL_COLUMNS:
                cells.append(cell_xml(ref, row.get(header), is_bool=True))
            elif header in STRING_COLUMNS:
                cells.append(cell_xml(ref, str_indices.get(header), is_string=True))
            else:
                cells.append(cell_xml(ref, row.get(header)))
        xml_rows.append(f'<row r="{row_num}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        "</worksheet>"
    )


def build_shared_strings_xml(strings):
    items = "".join(f"<si><t>{escape(s)}</t></si>" for s in strings)
    count = len(strings)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{count}" uniqueCount="{count}">{items}</sst>'
    )


CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "</Types>"
)

ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)

WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
    "</workbook>"
)

WORKBOOK_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
    "</styleSheet>"
)


def main():
    rows = build_rows(ROW_COUNT)
    strings, header_indices, row_string_indices = build_shared_strings(rows)

    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        z.writestr("_rels/.rels", ROOT_RELS_XML)
        z.writestr("xl/workbook.xml", WORKBOOK_XML)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        z.writestr("xl/styles.xml", STYLES_XML)
        z.writestr("xl/sharedStrings.xml", build_shared_strings_xml(strings))
        z.writestr(
            "xl/worksheets/sheet1.xml",
            build_sheet_xml(rows, header_indices, row_string_indices),
        )

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
