# Resolve — Customer Complaint Management & RCA

A working, fictional prototype for **S3K Case Study 02 / AI Services**. It gives a service team one queue for complaint intake, human-reviewed triage, ownership, SLA tracking, RCA/CAPA and approved resolution.

## Run locally

```powershell
python server.py
```

Open `http://127.0.0.1:8766/`. Python 3.10+ standard library is the only requirement. SQLite is created automatically. Set `COMPLAINT_DB` to choose a different database path.

## Try the workflow

1. Open **CC-001** to inspect the damaged-cartons example and a same-batch suggestion.
2. Create a new case. The suggested category and priority are visible, but no owner is assigned automatically.
3. In the case detail, confirm owner, category and priority as a human reviewer.
4. Submit an RCA and CAPA. Approve a customer-ready resolution with the review checkbox.
5. Inspect the audit trail and ask the status assistant about a case number.

The demo never sends customer messages. Its “AI” triage and assistant are deterministic rules over fictional records, with review checkpoints; no external LLM or customer data is used. The current demo uses an actor name field, **not production authentication**. A real deployment needs SSO, role-based authorization, attachment security, email/CRM integration, retention policies and operational monitoring.

See [CASE_STUDY.md](CASE_STUDY.md) for the discovery, KPIs, workflow, UAT and implementation plan.

## API

`GET /api/state`, `GET /api/complaints/{id}/suggestion`, `POST /api/complaints`, `POST /api/complaints/{id}/assign`, `POST /api/complaints/{id}/update`, `POST /api/complaints/{id}/approve`, `POST /api/assistant`.

All data is fictional. No hardware, paid service or API key is required.
