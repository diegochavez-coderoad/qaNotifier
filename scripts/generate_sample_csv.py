import csv
import os
import sys
from datetime import datetime, timedelta

from scripts.table_utils import BOOL_COLUMNS, HEADERS, build_rows

EXCEL_EPOCH = datetime(1899, 12, 30)

OUTPUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "../samples/sample.csv"
ROW_COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 60


def format_value(header, value):
    if value is None:
        return ""
    if header in BOOL_COLUMNS:
        return "TRUE" if value else "FALSE"
    if header in ("Date", "Date QA Completed"):
        return (EXCEL_EPOCH + timedelta(days=value)).strftime("%Y-%m-%d")
    return value


def main():
    rows = build_rows(ROW_COUNT)

    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow(format_value(header, row.get(header)) for header in HEADERS)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
