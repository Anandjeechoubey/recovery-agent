# Email Confirmation Feature

## Overview

When a debt resolution workflow concludes, two things happen automatically:

1. **Deal confirmation message in chat** — if the borrower agrees to a deal during the resolution stage, a confirmation message is posted in the chat summarising exactly what was agreed to (amount, payment terms, deadline).
2. **Workflow summary email** — once the entire workflow is complete (any outcome), an email is sent to the borrower's email address summarising the conversation and outcome.

---

## Configuration

Add the following to your `.env`:

```env
EMAIL_FROM=your-gmail@gmail.com
GOOGLE_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

- `EMAIL_FROM` — the Gmail address used as the sender.
- `GOOGLE_APP_PASSWORD` — a [Google App Password](https://myaccount.google.com/apppasswords) (not your regular Gmail password). Required because standard password auth is disabled for SMTP.

Email is silently skipped (with a warning log) if either value is missing or if the borrower has no email address on file.

---

## How It Works

### 1. Deal Confirmation Chat Message

**Triggered:** in `run_resolution` (voice path) and `_run_resolution_chat` (chat/simulated path) immediately after `deal_agreed` is detected.

**What it does:**
- Calls `_generate_deal_confirmation(conversation, borrower)` which sends the full transcript to the LLM and asks it to produce a concise confirmation (≤80 words) covering:
  - The specific settlement amount or monthly payment/installments
  - Payment deadline or start date
  - Note that written confirmation will follow
- The message is posted to the chat as an `agent` message so the borrower sees it before the workflow closes.
- Falls back to a generic template if the LLM call fails.

### 2. Workflow Summary Email

**Triggered:** from `CollectionsWorkflow` via the `send_email_summary` Temporal activity, called before every workflow return point:
- `deal_agreed` → outcome label `Agreement Reached`
- `hardship_requested` → outcome label `Hardship Program Referral`
- `resolved` / `escalate` / other → corresponding label

**What it does:**
- Compiles a transcript of all completed stages (assessment, resolution, final notice).
- Sends the transcript and outcome to the LLM to generate a professional plain-text email body (≤200 words) that:
  - States the outcome in the first sentence
  - Summarises agreed terms if a deal was reached
  - Lists next steps for the borrower
- Sends the email via Gmail SMTP SSL (port 465) to `borrower.email`.
- Subject line format: `Your Account Summary — <Outcome> | Account ...<last4>`
- Falls back to a generic template if the LLM call fails.

---

## Files Changed

| File | Change |
|---|---|
| `src/email_sender.py` | New — Gmail SMTP utility (`send_email`, `_smtp_send`) |
| `src/config.py` | Added `email_from` and `google_app_password` settings |
| `src/workflow/activities.py` | Added `_generate_deal_confirmation`, `send_email_summary` activity; wired confirmation into resolution paths |
| `src/workflow/collections_workflow.py` | Calls `send_email_summary` before every return |
| `src/api/app.py` | Registered `send_email_summary` with the embedded Temporal worker |
| `src/workflow/worker.py` | Registered `send_email_summary` with the standalone worker |

---

## Outcome → Email Subject Mapping

| Workflow outcome | Email subject label |
|---|---|
| `agreement` | Agreement Reached |
| `resolved` | Account Resolved |
| `hardship_requested` | Hardship Program Referral |
| `escalate` | Escalated — No Resolution |
| `no_response` | No Response |
