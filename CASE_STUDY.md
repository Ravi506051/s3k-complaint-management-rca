# Case 02 — Customer Complaint Management & Root Cause Analysis

## Problem and current process

The fictional manufacturer receives about 120 complaints monthly by email, phone and Excel. Customer Service manually transcribes the issue, forwards it to Quality, Production or Logistics, follows up across inboxes and communicates a resolution. The Quality lead also wants to see recurring defects and whether corrective actions worked. The baseline in the brief is 48 hours to first response, nine days to resolution and 20% past target date.

The main stakeholders are the customer, Customer Service agent and manager, Quality lead, Production and Logistics owners, and IT/integration team. Intake creates duplicate records; routing happens without a visible owner or clock; and RCA/CAPA outcomes are scattered, so recurring packaging defects can be missed.

## Three management KPIs

| KPI | Definition | Baseline / proposed target | Why it matters |
| --- | --- | --- | --- |
| First human response time | Hours from intake to an acknowledged customer response | 48 h / under 8 h | Shows whether customers receive timely ownership, regardless of AI triage speed. |
| Approved resolution time | Days from intake to human-approved resolution | 9 d / under 5 d | Measures the complete cross-department process. |
| Target-date miss rate | Open or resolved cases past their agreed target / total cases | 20% / under 10% | Exposes backlog and accountability gaps. |

Targets are hypotheses for discovery, not measured outcomes from this prototype.

## Discovery questions

1. Which channels and systems are authoritative for an incoming complaint, and who creates the official case number?
2. What categories, severity rules and customer-specific SLAs already exist? Who may change them?
3. Which evidence is required for a batch complaint, and how are attachments stored and retained?
4. When should Quality, Production or Logistics own the investigation, and what happens during handoffs?
5. Who approves RCA, CAPA and customer-facing resolution, and what constitutes sufficient evidence?
6. How should near-duplicates across email, phone and Excel be reviewed without silently merging different issues?
7. What data may an assistant expose to a customer or employee, and what must remain internal?

## Future workflow and human controls

1. Capture a structured case from a channel adapter. Validate customer, batch, description and timestamps. Preserve the source message as an audit reference in a production version.
2. Suggest a category, priority and likely owner. Surface same-batch cases as **potential** duplicates. A service lead confirms routing; an algorithm cannot silently close or merge a case.
3. Start an owner-visible target clock. Notify the owner on assignment and escalate nearing or missed deadlines. The demo shows overdue state; actual email/SMS integration is future work.
4. The department investigates and records evidence-based root cause and corrective/preventive action (CAPA). A Quality reviewer approves the final resolution. Only an approved outcome may become customer-facing.
5. Provide a status assistant grounded in recorded case fields. It returns case status and target date, never invents a replacement promise. Keep a searchable audit history of assignment, RCA/CAPA and approval.

AI must not autonomously assign liability, promise replacement, send a resolution, merge cases, approve CAPA or expose one customer's private records to another. A production assistant needs authorization checks and source citations on every answer.

## UI mockup and prompts

The working `index.html` is the UI mockup. It presents operational KPIs, a searchable case queue, case detail, reviewable triage suggestion, RCA/CAPA forms, a human approval action and an activity log. The starting prompt to the coding assistant was: “Build a complaint operations dashboard for a fictional manufacturer, using the brief's damaged-cartons example. Make owner, due date and next action visible. Keep AI suggestions subordinate to human review.” I refined it to require SQLite persistence, visible same-batch hints, guarded approval and a recorded status assistant.

Design choices: a restrained service-operations palette, one dominant queue, explicit overdue labels and a detail view that follows the real handoff order. The interface calls its model a **rule-based demo** and labels fictional data.

## UAT scenarios

| Scenario | Steps | Expected outcome |
| --- | --- | --- |
| Duplicate / misclassification | Create a second BX-204 case and inspect suggested similar cases; change category/priority during human assignment. | Duplicate is surfaced for review, never auto-merged; reviewed values and actor appear in the audit trail. |
| Bypassed approval | Attempt to approve a new or investigating case before entering RCA/CAPA, or omit reviewer confirmation. | API rejects the action; no “Resolved” status or customer-ready outcome is recorded. |
| Missed target | Inspect CC-001 with an elapsed due date, then filter or open it. | Overdue flag remains visible to the owner and manager; status assistant does not invent a completion date. |

## Implementation path and limits

The prototype uses Python `ThreadingHTTPServer`, SQLite and browser JavaScript. A production version would use authenticated service APIs, role checks, a durable managed database, attachment storage with malware scanning, CRM/mail ingestion, scheduled SLA escalation, observability and an approved knowledge base for retrieval. Evaluate suggestions against labelled historical cases for precision, recall, fairness across complaint types and reviewer override rates before any live use.

This repository was developed with OpenAI Codex from Ravi Kumar Rao's request to build the additional case-study projects. The fictional workflow and design are demonstrative. It is not evidence of a production deployment or of the candidate personally coding every component. Human review remains necessary before any interview or submission claim.
