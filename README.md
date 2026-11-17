# Resolve: Customer Complaint Management and RCA

A working prototype for **S3K Internship 2026, Case Study 02: AI Services**. Resolve brings complaint intake, triage, ownership, SLA visibility, root cause analysis (RCA), corrective and preventive actions (CAPA), and final review into one queue.

**[Read the case study](CASE_STUDY.md)** · **[Download the source ZIP](downloads/s3k-complaint-management-rca.zip)**

## What the prototype covers

| Step | What happens |
| --- | --- |
| Intake | A complaint is recorded with its description and customer context |
| Triage | Rules suggest a category and priority for a person to review |
| Ownership | A reviewer confirms the responsible owner and case details |
| Investigation | The team records RCA findings and CAPA |
| Resolution | A human approves the customer-ready outcome |
| Follow-up | The audit trail and status assistant show what happened |

Suggestions are visible to reviewers; the system does not automatically assign an owner or send a customer response.

## Run locally

Requires Python 3.10 or newer. It uses only the Python standard library and SQLite.

```powershell
python server.py
```

Open [http://127.0.0.1:8766/](http://127.0.0.1:8766/). The database is created on first run. To choose another location, set the `COMPLAINT_DB` environment variable before starting the server.

## Five-minute demo

1. Open **CC-001** to inspect the damaged-cartons example and the related-case hint.
2. Create a complaint and review its suggested category and priority.
3. Confirm the owner and classification in the case detail.
4. Record the RCA and CAPA, then approve the resolution using the review checkpoint.
5. Check the audit trail and ask the assistant for a case status.

The frontend is in `index.html`, `styles.css`, `assistant.css`, and `app.js`. The HTTP API and database logic are in `server.py`. [CASE_STUDY.md](CASE_STUDY.md) explains the problem, proposed workflow, success metrics, UI, and UAT plan.

## API at a glance

`GET /api/state` · `GET /api/complaints/{id}/suggestion` · `POST /api/complaints` · `POST /api/complaints/{id}/assign` · `POST /api/complaints/{id}/update` · `POST /api/complaints/{id}/approve` · `POST /api/assistant`

## Prototype boundaries

All case data is fictional. The triage suggestions and assistant use deterministic rules, not an external AI model. The actor-name field is for the demo and is **not authentication**. There are no real customer messages or attachments. A production implementation would require SSO, role permissions, secure attachment handling, CRM or email integration, retention rules, and monitoring.
