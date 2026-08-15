FAKE_SLACK_ID = "U0FAKE0001"
FAKE_PHONE_NUMBER = "+1-555-0100"

STATUS_POINTS = {
    "Opportunity": 2,
    "Failed": 5,
    "Critical": 10,
}


def follow_up_multiplier(follow_up):
    if follow_up == 0:
        return 1
    if follow_up == 1:
        return 2
    return 5


def error_score(error_entry):
    points = STATUS_POINTS.get(error_entry["status"], 0)
    return points * follow_up_multiplier(error_entry["follow_up"])


def categorize(severity):
    if severity > 50:
        return "alert"
    if severity >= 20:
        return "medium"
    return "light"


def parse_follow_up(value):
    if value in (None, ""):
        return 0
    return int(value)


def excel_serial_to_date(serial):
    # Pure-arithmetic Excel-serial -> Gregorian date, no imports (Howard Hinnant's
    # civil_from_days algorithm) — n8n's Python task runner blocks all stdlib imports
    # by default, including `datetime`.
    unix_days = int(serial) - 25569
    z = unix_days + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    y = y + 1 if m <= 2 else y
    return f"{y:04d}-{m:02d}-{d:02d}"


def format_date(value):
    if value in (None, ""):
        return None
    return excel_serial_to_date(value)


groups = {}
emails = {}
for item in _items:
    row = item["json"]
    name_value = row.get("Name")
    if not name_value:
        continue

    display_name = name_value.split("@")[0].replace(".", " ").strip()
    emails.setdefault(display_name, name_value)
    fix_comment = row.get("QA Fix Comment") or ""

    error_entry = {
        "id": row.get("ID / Task / Case Number", ""),
        "status": row.get("QA Status", ""),
        "follow_up": parse_follow_up(row.get("Follow Up Count")),
        "error_message": row.get("QA Comment") or "No comments",
        "fixed": "fixed" in fix_comment.lower(),
        "date": format_date(row.get("Date")),
        "reviewed_by": row.get("QA Completed by:", ""),
    }
    groups.setdefault(display_name, []).append(error_entry)

report = []
for name, errors in groups.items():
    severity = sum(error_score(e) for e in errors)
    report.append({"json": {
        "name": name,
        "email": emails[name],
        "slack_id": FAKE_SLACK_ID,
        "phone_number": FAKE_PHONE_NUMBER,
        "errors_found": len(errors),
        "error_severity_level": severity,
        "category": categorize(severity),
        "errors": errors,
    }})

return report
