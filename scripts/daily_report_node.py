TERMINAL_STATUSES = {"Passed", "Completed"}

# "Pattern" still has no reliable structured signal to derive it from (unlike "Main issues"
# below) — left as a manual constant. Edit before each run until it's wired to a real input.
PATTERN = "Exclude copywritter content, Links with Error 404, Sitemap not enabled"
AT_RISK_NOTE = "missing content and links"


def join_names(names):
    if not names:
        return "None"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


# _items here are the grouped per-person report from "Categorize reviewees"
# (json_to_groups.py) — each person's `errors` list carries per-case fields
# (status, error_message, fixed, date, reviewed_by), which is what this node reads.
people = [item["json"] for item in _items]
all_errors = [error for person in people for error in person.get("errors", [])]

reviewers = []
seen_reviewers = set()
for error in all_errors:
    reviewer = error.get("reviewed_by")
    if reviewer and reviewer not in seen_reviewers:
        seen_reviewers.add(reviewer)
        reviewers.append(reviewer)

critical_at_risk = [
    error for error in all_errors
    if error.get("status") == "Critical" and not error.get("fixed")
]
pending = [error for error in all_errors if error.get("status") not in TERMINAL_STATUSES]

critical_messages = [
    error.get("error_message", "") for error in all_errors
    if error.get("status") == "Critical" and error.get("error_message") not in (None, "", "No comments")
]
main_issues = "; ".join(critical_messages) if critical_messages else "No critical issues found"

at_risk_line = f"At risk: {len(critical_at_risk)} Critical"
if AT_RISK_NOTE:
    at_risk_line += f": ({AT_RISK_NOTE})"

report = "\n".join([
    f"Reviewed: {join_names(reviewers)} / {len(all_errors)} cases",
    f"Main issues: {main_issues}",
    # f"Pattern: {PATTERN}",
    # at_risk_line,
    f"Queues: {len(pending)} Cases Pending",
])

return [{"json": {"report": report}}]
