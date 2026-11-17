"""Fictional complaint-management prototype. Python standard library only."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get("COMPLAINT_DB", ROOT / "complaints.sqlite3"))
FILES = {"/", "/index.html", "/styles.css", "/assistant.css", "/app.js"}
OWNERS = {"Quality", "Production", "Logistics", "Customer Service"}
STATUSES = {"New", "Investigating", "Pending approval", "Resolved"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def audit(db, complaint_id: int, action: str, actor: str, detail: str = ""):
    db.execute(
        "INSERT INTO audit(complaint_id,action,actor,detail,at) VALUES(?,?,?,?,?)",
        (complaint_id, action, actor, detail, iso(now())),
    )


def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS complaints (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          customer TEXT NOT NULL, batch TEXT NOT NULL, channel TEXT NOT NULL,
          description TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL,
          owner TEXT, status TEXT NOT NULL, due_at TEXT NOT NULL,
          rca TEXT NOT NULL DEFAULT '', capa TEXT NOT NULL DEFAULT '',
          resolution TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, approved_by TEXT
        );
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          complaint_id INTEGER NOT NULL REFERENCES complaints(id),
          action TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL,
          at TEXT NOT NULL
        );
        """)
        if db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]:
            return
        samples = [
            ("Aster Foods", "BX-204", "Email", "Eight cartons arrived damaged. Urgent replacement requested.", "Packaging", "High", "Quality", "Investigating", -1),
            ("Riverline Retail", "BX-198", "Phone", "Shipment was late and the tracking update was missing.", "Delivery", "Medium", "Logistics", "Investigating", 2),
            ("Luma Supply", "BX-201", "Excel", "Label on outer carton does not match invoice.", "Documentation", "Medium", "Production", "Pending approval", 1),
            ("Northstar Stores", "BX-190", "Email", "Two cartons crushed on arrival.", "Packaging", "High", "Quality", "Resolved", -5),
            ("Aster Foods", "BX-207", "Phone", "Seal appears weak on several packages.", "Packaging", "Medium", None, "New", 3),
            ("Cedar Wholesale", "BX-212", "Email", "Received fewer units than ordered.", "Quantity", "Medium", "Customer Service", "Investigating", 2),
        ]
        for customer, batch, channel, description, category, priority, owner, status, due_offset in samples:
            created = iso(now() - timedelta(days=4))
            due = iso(now() + timedelta(days=due_offset))
            cur = db.execute("""INSERT INTO complaints
                (customer,batch,channel,description,category,priority,owner,status,due_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (customer, batch, channel, description, category, priority, owner, status, due, created, created))
            audit(db, cur.lastrowid, "captured", "Demo seed", "Fictional sample case")


def suggestion(description: str, batch: str, db, exclude_id: int | None = None):
    text = description.lower()
    if any(word in text for word in ("damage", "crush", "seal", "carton")):
        category, owner = "Packaging", "Quality"
    elif any(word in text for word in ("late", "shipment", "delivery", "tracking")):
        category, owner = "Delivery", "Logistics"
    elif any(word in text for word in ("invoice", "label", "document")):
        category, owner = "Documentation", "Production"
    else:
        category, owner = "Other", "Customer Service"
    priority = "High" if any(word in text for word in ("urgent", "damaged", "stopped", "safety")) else "Medium"
    matches = [dict(row) for row in db.execute(
        "SELECT id,customer,batch,status,category FROM complaints WHERE batch=? AND id!=? ORDER BY id DESC LIMIT 4",
        (batch.upper(), exclude_id or -1),
    )]
    return {"category": category, "priority": priority, "suggested_owner": owner,
            "similar_cases": matches, "disclaimer": "Rule-based suggestion for review; no autonomous routing or decision."}


def serialize(row):
    item = dict(row)
    item["overdue"] = item["status"] != "Resolved" and item["due_at"] < iso(now())
    return item


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("Complaint demo:", fmt % args)

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 16_384:
            raise ValueError("Invalid request size")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with connect() as db:
                complaints = [serialize(row) for row in db.execute("SELECT * FROM complaints ORDER BY updated_at DESC,id DESC")]
                history = [dict(row) for row in db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 20")]
                total = len(complaints)
                metrics = {"open": sum(c["status"] != "Resolved" for c in complaints),
                           "overdue": sum(c["overdue"] for c in complaints),
                           "unassigned": sum(not c["owner"] for c in complaints),
                           "resolved": sum(c["status"] == "Resolved" for c in complaints)}
            return self.send_json({"complaints": complaints, "audit": history, "metrics": metrics,
                                   "sample_total": total, "baseline": {"first_response_hours": 48,
                                   "resolution_days": 9, "missed_target_percent": 20}})
        if path.startswith("/api/complaints/") and path.endswith("/suggestion"):
            match = re.fullmatch(r"/api/complaints/(\d+)/suggestion", path)
            if not match:
                return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            with connect() as db:
                row = db.execute("SELECT * FROM complaints WHERE id=?", (int(match[1]),)).fetchone()
                if not row:
                    return self.send_json({"error": "Complaint not found"}, HTTPStatus.NOT_FOUND)
                result = suggestion(row["description"], row["batch"], db, row["id"])
            return self.send_json(result)
        if path.startswith("/api/"):
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        if path not in FILES:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_json()
            if path == "/api/complaints":
                customer = str(data.get("customer", "")).strip()[:120]
                batch = str(data.get("batch", "")).strip().upper()[:40]
                description = str(data.get("description", "")).strip()[:2000]
                channel = str(data.get("channel", "Email")).strip()[:30]
                if not customer or not batch or len(description) < 12 or channel not in {"Email", "Phone", "Excel"}:
                    raise ValueError("Customer, batch, channel and a description of at least 12 characters are required")
                with connect() as db:
                    advice = suggestion(description, batch, db)
                    stamp = iso(now())
                    cur = db.execute("""INSERT INTO complaints
                        (customer,batch,channel,description,category,priority,owner,status,due_at,created_at,updated_at)
                        VALUES(?,?,?,?,?,? ,NULL,'New',?,?,?)""",
                        (customer, batch, channel, description, advice["category"], advice["priority"],
                         iso(now() + timedelta(days=3)), stamp, stamp))
                    audit(db, cur.lastrowid, "captured", "Customer Service", "Suggested classification awaits review")
                return self.send_json({"id": cur.lastrowid, "suggestion": advice}, HTTPStatus.CREATED)
            if path == "/api/assistant":
                match = re.search(r"\b(?:CC-)?(\d{1,5})\b", str(data.get("question", "")))
                if not match:
                    return self.send_json({"answer": "Please include a complaint number, for example CC-101. I only provide recorded status."})
                with connect() as db:
                    row = db.execute("SELECT * FROM complaints WHERE id=?", (int(match[1]),)).fetchone()
                if not row:
                    return self.send_json({"answer": "I could not find that complaint in this fictional demo."})
                return self.send_json({"answer": f"CC-{row['id']:03d} is {row['status'].lower()}. Owner: {row['owner'] or 'not assigned yet'}. Target: {row['due_at'][:10]}. This is recorded status, not a promised resolution."})
            match = re.fullmatch(r"/api/complaints/(\d+)/(assign|update|approve)", path)
            if not match:
                return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            complaint_id, action = int(match[1]), match[2]
            actor = str(data.get("actor", "Demo reviewer")).strip()[:80] or "Demo reviewer"
            with connect() as db:
                row = db.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
                if not row:
                    return self.send_json({"error": "Complaint not found"}, HTTPStatus.NOT_FOUND)
                if action == "assign":
                    owner = str(data.get("owner", ""))
                    category = str(data.get("category", ""))[:80]
                    priority = str(data.get("priority", ""))
                    if owner not in OWNERS or priority not in {"Low", "Medium", "High", "Critical"} or not category:
                        raise ValueError("Review owner, category and priority")
                    db.execute("UPDATE complaints SET owner=?,category=?,priority=?,status='Investigating',updated_at=? WHERE id=?",
                               (owner, category, priority, iso(now()), complaint_id))
                    audit(db, complaint_id, "human_assignment", actor, f"{owner}; {category}; {priority}")
                elif action == "update":
                    rca = str(data.get("rca", "")).strip()[:2000]
                    capa = str(data.get("capa", "")).strip()[:2000]
                    if not row["owner"] or len(rca) < 15 or len(capa) < 15:
                        raise ValueError("Assign an owner and enter RCA and CAPA of at least 15 characters")
                    db.execute("UPDATE complaints SET rca=?,capa=?,status='Pending approval',updated_at=? WHERE id=?",
                               (rca, capa, iso(now()), complaint_id))
                    audit(db, complaint_id, "rca_capa_submitted", actor, "Awaiting human approval")
                else:
                    resolution = str(data.get("resolution", "")).strip()[:2000]
                    if row["status"] != "Pending approval" or not row["rca"] or not row["capa"] or len(resolution) < 15:
                        raise ValueError("Human approval requires submitted RCA/CAPA and a resolution of at least 15 characters")
                    if data.get("reviewed") is not True:
                        raise ValueError("Reviewer confirmation is required")
                    db.execute("UPDATE complaints SET resolution=?,status='Resolved',approved_by=?,updated_at=? WHERE id=?",
                               (resolution, actor, iso(now()), complaint_id))
                    audit(db, complaint_id, "human_approved", actor, "Resolution approved for customer communication")
            return self.send_json({"id": complaint_id, "ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


if __name__ == "__main__":
    initialize()
    port = int(os.environ.get("PORT", "8766"))
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    print(f"Complaint demo listening on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
