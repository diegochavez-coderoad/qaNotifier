# qaNotifier

AI Powered QA Notifier & Feedback/Compliance Assistant

**qaNotifier** automates QA defect notifications and team performance tracking by intelligently routing quality alerts based on severity. It monitors a designated folder for QA reports, extracts and scores defects by quantity/severity/follow-up count, then routes notifications through appropriate channels:

- **Light**: Minor issues → Slack notification
- **Medium**: Multiple critical issues → Email with AI-generated header
- **Alert**: High-severity, repeat issues → Escalation protocol via voice call (AI generated text to speech)

### Requirements

- Download Docker: https://docs.docker.com/get-started/get-docker/
- Download n8n: https://docs.n8n.io/deploy/host-n8n/install-options/one-line-setup
- Setup Google Oauth Authentication in n8n: For that you can follow the instructions in this Youtube video https://www.youtube.com/watch?v=FBGtpWMTppw
- An Ollama model configured in n8n, for the AI notification-content nodes

### Repo structure

```
qaNotifier/
├── n8n/
│   └── qaNotifier.json                   Exported n8n workflow — import this to get the whole
│                                          Drive-watching + notification pipeline in one shot
├── scripts/
│   ├── xlsx_to_json.py                   Standalone: .xlsx -> flat rows (JSON)
│   ├── generate_sample_xlsx.py           Generates a synthetic sample .xlsx for testing
│   ├── json_to_groups.py                 n8n Code node source ("Categorize reviewees")
│   └── daily_report_node.py              n8n Code node source ("Get daily report")
├── prompts/
│   ├── header_image_prompt.md            Prompt for the "Get email header" AI node
│   └── email_body_prompt_template.md     Prompt for the "Get email body" AI node
├── samples/
│   ├── excel_to_json/                    Sample input .xlsx and its xlsx_to_json.py output
│   └── json_to_group/                    Sample input/output for json_to_groups.py, plus
│                                          contact_map.json (fake slack_id/phone_number per
│                                          person, see "Known limitations")
└── README.md                             This file
```

## n8n workflows: 

**Import:** in n8n, Workflows → Import from File 

`n8n/extractData.json`: activates the workflow on excel uploads to a google drive folder called `qaNotifier`, this downloads the file, turns it into a json categorized by error level so that it is ready to send to either slack/gmail/voice call

## Scripts

### Utility Scripts
- **`xlsx_to_json.py`** — parses a raw `.xlsx` (zip + XML, no dependencies) into a flat
  list of row objects, then groups them by person. Kept as a utility; n8n does not use it.
- **`generate_sample_xlsx.py`** — writes a synthetic sample `.xlsx` by hand, so `samples/`
  never needs real customer data. **Never point this repo's samples at a real exported
  report.**

### n8n Code

- **`json_to_groups.py`** → "Categorize reviewees" node. Groups extracted rows by person,
  scores each person's `error_severity_level` from `QA Status` × a follow-up multiplier, and
  assigns a `category` (`light`/`medium`/`alert`) used for downstream routing.
- **`daily_report_node.py`** → "Get daily report" node. Reads the grouped output above and
  produces a plain-text daily digest (`Reviewed`, `Main issues`, `Queues`).

## Prompts

LLM prompts used by the workflow's Ollama nodes, kept as versioned files:

- **`header_image_prompt.md`** → "Get email header" node. Prompt for generating an urgent email header image.
- **`email_body_prompt_template.md`** → "Get email body" node. Prompt for generating the notification email
