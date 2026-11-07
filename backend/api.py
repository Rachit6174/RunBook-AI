
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import IncidentResponseAgent

DB = "runbook_dashboard.db"

app = FastAPI(title="RunBook AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IncidentInput(BaseModel):
    service: str
    severity: str
    description: str


class ResolutionInput(BaseModel):
    incident_id: str
    outcome: str
    details: str


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


# Initialize database when the application starts
@app.on_event("startup")
def initialize_database():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                remediation_plan TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS resolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


@app.get("/api/stats")
def stats():
    with connect() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM incidents"
        ).fetchone()[0]

        open_count = db.execute(
            "SELECT COUNT(*) FROM incidents WHERE status='Open'"
        ).fetchone()[0]

        resolved = db.execute(
            "SELECT COUNT(*) FROM resolutions WHERE outcome='resolved'"
        ).fetchone()[0]

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": resolved
    }


@app.get("/api/incidents")
def incidents():
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC"
        ).fetchall()

    return {"incidents": [dict(row) for row in rows]}


@app.post("/api/incidents")
def report_incident(data: IncidentInput):
    incident_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    try:
        agent = IncidentResponseAgent()
        plan = agent.handle_incident(
            f"Service: {data.service}. Severity: {data.severity}. "
            f"Incident: {data.description}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    with connect() as db:
        db.execute(
            """
            INSERT INTO incidents
            (incident_id, service, severity, description,
             remediation_plan, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                data.service,
                data.severity,
                data.description,
                plan,
                "Open",
                now,
                now
            )
        )

    return {
        "incident_id": incident_id,
        "remediation_plan": plan,
        "status": "Open"
    }


@app.post("/api/resolutions")
def record_resolution(data: ResolutionInput):
    if data.outcome not in ("resolved", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Invalid outcome"
        )

    now = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        incident = db.execute(
            "SELECT * FROM incidents WHERE incident_id=?",
            (data.incident_id,)
        ).fetchone()

        if not incident:
            raise HTTPException(
                status_code=404,
                detail="Incident not found"
            )

        db.execute(
            """
            INSERT INTO resolutions
            (incident_id, outcome, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                data.incident_id,
                data.outcome,
                data.details,
                now
            )
        )

        db.execute(
            """
            UPDATE incidents
            SET status=?, updated_at=?
            WHERE incident_id=?
            """,
            (
                "Resolved" if data.outcome == "resolved" else "Open",
                now,
                data.incident_id
            )
        )

    return {"message": "Resolution recorded successfully"}
