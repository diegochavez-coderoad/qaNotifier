import random

FAKE_DOMAIN = "example.com"
FAKE_TICKET_PREFIX = "DE"
FAKE_PEOPLE = [
    "alice.johnson",
    "brian.kim",
    "carla.mendez",
    "derek.osei",
    "elena.petrova",
    "farid.hassan",
    "grace.oconnor",
    "hiro.tanaka",
]

STATUSES = ["Passed", "In progress", "Opportunity", "Failed", "Critical"]
STATUS_WEIGHTS = [55, 15, 15, 10, 5]
TYPES = ["SEO Landing Page", "OEM Landing Page", "Blog", "Posting Case"]
REVIEWERS = ["Priya Shah", "Owen Clarke"]

COMMENTS_BY_STATUS = {
    "Opportunity": [
        "D/M | Opportunity | Styling | Element overlaps the header on mobile",
        "M | Opportunity | Layout | Content block could be reordered",
    ],
    "Failed": [
        "D/M | Failed | Link | Broken link in the footer",
        "D/M | Failed | Config | Required tracking script missing",
    ],
    "Critical": [
        "D/M | Critical | Content | Placeholder text left in production",
        "D/M | Critical | Layout | Page fails to render on mobile",
    ],
}

FIX_COMMENTS = ["Fixed", "NA: Intentional, no fix needed", None]

HEADERS = [
    "Primary",
    "CMS Link",
    "Date",
    "Date QA Completed",
    "ID / Task / Case Number",
    "Name",
    "QA Completed by:",
    "QA Status",
    "XML/HTML",
    "Type",
    "Status",
    "QA Comment",
    "QA Fix Comment",
    "QA Link",
    "Follow Up Count",
]
STRING_COLUMNS = {
    "Primary", "CMS Link", "ID / Task / Case Number", "Name", "QA Completed by:",
    "QA Status", "Type", "Status", "QA Comment", "QA Fix Comment", "QA Link",
}
BOOL_COLUMNS = {"XML/HTML"}

# Force a few people into each severity tier (see scripts/json_to_groups.py's scoring) so
# the generated file exercises "light", "medium", and "alert" categories, not just "light".
FORCED_ROWS = (
    [("alice.johnson", "Critical")] * 7  # -> alert (70 pts)
    + [("brian.kim", "Failed")] * 3  # -> medium (15 pts) ...
    + [("brian.kim", "Opportunity")] * 2  # ... + 4 pts = 19, bump one more below
    + [("brian.kim", "Failed")] * 1  # -> 20 pts total, lands exactly on "medium"
)


def build_row(counter, person, status):
    comment = random.choice(COMMENTS_BY_STATUS[status]) if status in COMMENTS_BY_STATUS else None
    fix_comment = random.choice(FIX_COMMENTS) if comment else None
    return {
        "Primary": "All info",
        "CMS Link": f"https://{person.replace('.', '')}.example.com/inventory/vehicle-{counter}.htm",
        "Date": 46200 + (counter % 30),
        "Date QA Completed": 46220 + (counter % 10),
        "ID / Task / Case Number": f"{FAKE_TICKET_PREFIX}{9000 + counter}",
        "Name": f"{person}@{FAKE_DOMAIN}",
        "QA Completed by:": random.choice(REVIEWERS),
        "QA Status": status,
        "XML/HTML": True,
        "Type": random.choice(TYPES),
        "Status": "Completed",
        "QA Comment": comment,
        "QA Fix Comment": fix_comment,
        "QA Link": f"https://chat.example.com/files/{counter}",
        "Follow Up Count": random.randint(0, 4),
    }


def build_rows(row_count):
    rows = []
    counter = 0

    for person, status in FORCED_ROWS:
        counter += 1
        rows.append(build_row(counter, person, status))

    while len(rows) < row_count:
        counter += 1
        person = random.choice(FAKE_PEOPLE)
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        rows.append(build_row(counter, person, status))

    random.shuffle(rows)
    return rows
