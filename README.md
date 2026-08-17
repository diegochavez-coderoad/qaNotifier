# qaNotifier

AI Powered QA Notifier & Feedback/Compliance Assistant

**qaNotifier** automates QA defect notifications and team performance tracking by intelligently routing quality alerts based on severity. It monitors a designated Google Drive folder for QA reports, extracts and scores defects per developer by quantity/severity/follow-up count, sends the team lead a daily digest, and routes each developer's notification through the channel that matches how urgent their errors are:

- **Light** (severity < 10): Slack DM
- **Medium** (10 ≤ severity ≤ 20): Email, with an AI-drafted message
- **Alert** (severity > 20): AI outbound voice call (ElevenLabs ↔ Twilio), with an automatic SMS fallback — and a Slack escalation to the team lead instead of a call/text if the developer's Slack status shows them as out of office

### Requirements

- Getting n8n: There's two different approaches
  - Host an n8n instance
    - Download from https://docs.n8n.io/deploy/host-n8n/install-options/one-line-setup
    - Download Docker: https://docs.docker.com/get-started/get-docker/
  - Use the web version at [n8n.io](https://n8n.io/)
- Setup Google OAuth Authentication in n8n, with both Drive and Sheets scopes (the workflow watches a Drive folder and then reads the created spreadsheet's rows). You can follow the instructions in this Youtube video: https://www.youtube.com/watch?v=FBGtpWMTppw
- A Slack app/bot token with permission to send DMs, post to channels, and read user profiles (`users:read`/`users.profile:read` — used to detect out-of-office status before placing an alert-tier call)
- A Gmail OAuth2 credential in n8n, for medium-tier email notifications
- An Ollama model configured in n8n, for the AI notification-content and daily-digest nodes
- An ElevenLabs Conversational AI agent with a linked Twilio phone number (an API key alone isn't enough — the workflow calls ElevenLabs' `/v1/convai/twilio/outbound-call` endpoint with an `agent_id` and `agent_phone_number_id`)
- A Twilio account with:
  - Twilio Auth Token
  - Twilio Account SID
  - A Twilio phone number capable of sending SMS
- Two n8n Data Tables, matching the columns the workflows read/write:
  - **QA Notifier Errors Solutions:** a knowledge base wired in as an AI tool for the per-developer message generator
  - **Call SID proof:** logs each outbound call/SMS (`call_sid`, phone numbers, message text, status) so the "Call Webhooks" workflow can find it later

### Repo structure

```
qaNotifier/
├── n8n/
│   ├── QA Governance & Risk Mitigator.json   Main workflow — Drive trigger, per-developer
│   │                                          severity scoring/notifications, and the team
│   │                                          lead daily digest
│   └── Call Webhooks.json                    Companion workflow — Twilio/ElevenLabs call
│                                              webhooks; sends an SMS fallback whenever a
│                                              voice call doesn't land
├── prompts/
│   ├── header_image_prompt.md            Legacy: prompt for a header-image step that isn't
│   │                                      present in the current workflow
├── samples/
│   ├── sample.xlsx/                    Sample input .xlsx and its xlsx_to_json.py output
└── README.md                             This file
```

## n8n workflows

**Import:** in n8n, Workflows → Import from File. Import both workflows below — the main one hands off to the companion one for asynchronous call events.

### `n8n/QA Governance & Risk Mitigator.json`

1. **Folder File Updated** (Google Drive Trigger, polls every minute) fires when a new spreadsheet appears in the watched "QA Weekly Report" Drive folder.
2. **Read Report Rows** (Google Sheets) reads every row of "Sheet 1" from that spreadsheet.
3. From there the rows feed two independent branches:

   **A) Team lead daily digest**

   - **Code in JavaScript** drops rows whose `QA Status` is `Passed`/`In Progress`, keeps `QA Completed by:` / `QA Status` / `QA Comment`, and counts the day's `total_cases`.
   - **Message a model1** (Ollama, `qwen3.5`) asks the LLM to write a fixed-format status report for the team lead: `Date`, `Reviewed` (unique reviewers + case count), `Main issues`, `Pattern`, `At risk` (critical count + summary), and a `Status` line judging how bad the day was.
   - **Send a message** posts that report to Slack. The recipient is currently hardcoded to a test user and the message is prefixed `TEST ONLY:` — this still needs to be pointed at the real team lead / channel.

   **B) Per-developer notification & escalation**

   - **Code in JavaScript1** groups rows by developer (from the `Name` email column), keeps only bug rows (`Opportunity`/`Failed`/`Critical`), computes a `follow_up` count per case (how many times that case number repeats in the report) and an `error_severity_level` — per-error points (`Opportunity`=2, `Failed`=5, `Critical`=10) × a follow-up multiplier (×1 / ×2 / ×5) — and looks up each developer's `slack_id`/phone number from a hardcoded `USER_DIRECTORY` array in the node. (Mirrored outside the workflow in `scripts/generate_groups.js`.)
   - **Message a model** (Ollama, `qwen3.5`, with the **QA Notifier Errors Solutions** Data Table wired in as an AI tool) drafts a personalized bug-report message per developer; tone scales with severity — relaxed under 10, firmer 10–20, urgent above 20 — and lists their specific errors.
   - **Categorize by severity level** (Code node, runs in parallel off `Code in JavaScript1`) tags each developer's record with `category`: `light` (<10) / `medium` (10–20) / `alert` (>20), matching the thresholds used by the Switch node below.
   - **Enrich Message Information1** (Merge, combine-by-position) joins the drafted message back onto the categorized developer record.
   - **Switch** on `category`:
     - **light** → **Send Slack DM** — Slack DM with the message (recipient currently hardcoded to one test user rather than driven by `slack_id`).
     - **medium** → **Send a Mail** — Gmail (recipient currently hardcoded rather than driven by the developer's email).
     - **alert** → **Get information about a user** (Slack: fetch profile for `slack_id`) → **If** (checks `profile.status_text` against OOO/vacation/PTO/away patterns):
       - **out of office** → **Send Slack DM To Lead Fallback** — escalates straight to the team lead instead of calling/texting someone who's away.
       - **otherwise** → **Simplify call1** (Ollama) strips Markdown/Slack formatting and emoji so the message reads cleanly over voice/SMS, and condenses it to ≤150 words → **HTTP Request** places an outbound AI voice call through the ElevenLabs Conversational AI ↔ Twilio integration, passing `recipient_name` and `alert_message` as dynamic variables to the voice agent → **Insert row1** logs the call (`call_sid`, both phone numbers, the message text, initial status) into the **Call SID proof** Data Table so the companion workflow can find it later.

### `n8n/Call Webhooks.json`

Catches every way the outbound voice call can fail to land, and texts the same message as a fallback:

1. **Call status webhook** — if Twilio reports the call as not `completed`, send the SMS fallback.
2. **AMD webhook** — if Answering Machine Detection reports anything other than `human`, send the SMS fallback.
3. **ElevenLabs post-call webhook** — if the call never initiated, or the transcript shows voicemail was used or the recipient never meaningfully responded, send the SMS fallback.

Each path looks up the original message by `call_sid` in the **Call SID proof** Data Table before texting it via the Twilio Messages API.

## Prompts

Earlier prompt drafts, kept as versioned files but **not currently referenced by either workflow**

- **`header_image_prompt.md`** — prompt for "email header image" step.
