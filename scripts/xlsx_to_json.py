import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

XLSX_PATH = sys.argv[1] if len(sys.argv) > 1 else "../samples/excel_to_json/sample.xlsx"
OUTPUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "../samples/excel_to_json/output.json"


def column_letters(cell_ref):
    return re.match(r"[A-Z]+", cell_ref).group()


def load_shared_strings(z):
    tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in si.findall(".//m:t", NS))
        for si in tree.findall("m:si", NS)
    ]


def load_rows(z, shared_strings):
    tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in tree.find("m:sheetData", NS).findall("m:row", NS):
        cells = {}
        for c in row.findall("m:c", NS):
            v_el = c.find("m:v", NS)
            if v_el is None:
                continue
            col = column_letters(c.get("r"))
            cell_type = c.get("t")
            if cell_type == "s":
                cells[col] = shared_strings[int(v_el.text)]
            elif cell_type == "b":
                cells[col] = v_el.text == "1"
            else:
                cells[col] = v_el.text
        rows.append(cells)
    return rows


def extract_display_name(email_value):
    local_part = email_value.split("@")[0]
    return local_part.replace(".", " ").strip()


def is_fixed(fix_comment):
    return bool(fix_comment) and "fixed" in fix_comment.lower()


def parse_follow_up(value):
    if value in (None, ""):
        return 0
    return int(value)


def main():
    with zipfile.ZipFile(XLSX_PATH) as z:
        shared_strings = load_shared_strings(z)
        rows = load_rows(z, shared_strings)

    header_row = rows[0]
    header_to_col = {text: col for col, text in header_row.items()}

    name_col = header_to_col["Name"]
    id_col = header_to_col["ID / Task / Case Number"]
    comment_col = header_to_col["QA Comment"]
    fix_col = header_to_col["QA Fix Comment"]
    status_col = header_to_col["QA Status"]
    follow_up_col = header_to_col.get("Follow Up Count")

    groups = {}
    for row in rows[1:]:
        name_value = row.get(name_col)
        if not name_value:
            continue

        display_name = extract_display_name(name_value)
        error_entry = {
            "id": row.get(id_col, ""),
            "status": row.get(status_col, ""),
            "follow_up": parse_follow_up(row.get(follow_up_col) if follow_up_col else None),
            "error_message": row.get(comment_col) or "No comments",
            "fixed": is_fixed(row.get(fix_col, "")),
        }
        groups.setdefault(display_name, []).append(error_entry)

    report = [
        {
            "name": name,
            "slack_id": "Not Available For Now",
            "phone_number": "Not Available For Now",
            "errors_found": len(errors),
            "error_severity_level": len(errors) * 10,
            "errors": errors,
        }
        for name, errors in groups.items()
    ]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=4)

    print(f"Wrote {len(report)} people to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
