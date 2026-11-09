
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form
)
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .agent import IncidentResponseAgent
from .intent import IntentClassifier
from .memory import Hindsight


# ------------------------------------------
# DATABASE CONFIGURATION
# ------------------------------------------

DB_PATH = Path(__file__).resolve().parent.parent / "runbook.db"

MAX_IMAGE_SIZE = 6 * 1024 * 1024
MAX_LOG_SIZE = 1 * 1024 * 1024
MAX_TOTAL_SIZE = 20 * 1024 * 1024


def init_db():
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                remediation_plan TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        connection.execute("""CREATE TABLE IF NOT EXISTS approvals (approval_id TEXT PRIMARY KEY, incident_id TEXT, requested_action TEXT NOT NULL, risk_level TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'pending\', created_at TEXT NOT NULL, decision_at TEXT)""")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                approval_id TEXT,
                proposed_action TEXT,
                risk_level TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.commit()
    finally:
        connection.close()


init_db()


# ------------------------------------------
# FASTAPI CONFIGURATION
# ------------------------------------------

app = FastAPI(
    title="RunBook AI",
    description="AI-powered incident response and multimodal memory platform",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------
# REQUEST MODELS
# ------------------------------------------

class IncidentRequest(BaseModel):
    description: str = Field(min_length=5, max_length=5000)


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=5, max_length=5000)
    incident_id: str | None = None


class IncidentResponse(BaseModel):
    incident_id: str
    description: str
    remediation_plan: str
    status: str


class ResolutionRequest(BaseModel):
    status: Literal["resolved", "failed"]
    resolution_details: str = Field(
        min_length=5,
        max_length=5000
    )



class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class ConversationMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=20000)
    approval_id: str | None = None
    proposed_action: str | None = None
    risk_level: str | None = None

# ------------------------------------------
# HELPER: SAVE INCIDENT TO SQLITE
# ------------------------------------------

def save_incident(
    incident_id,
    description,
    remediation_plan,
    status="analyzed"
):
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            INSERT INTO incidents
            (incident_id, description, remediation_plan, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                incident_id,
                description,
                remediation_plan,
                status
            )
        )
        connection.commit()
    finally:
        connection.close()



def save_approval(requested_action, risk_level, incident_id=None):
    approval_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """INSERT INTO approvals
            (approval_id, incident_id, requested_action, risk_level, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)""",
            (approval_id, incident_id, requested_action, risk_level, created_at)
        )
        connection.commit()
    finally:
        connection.close()
    return approval_id


# ------------------------------------------
# HELPER: PROCESS MULTIMODAL INCIDENT
# OUTSIDE THE ASYNC EVENT LOOP
# ------------------------------------------

def process_multimodal_with_agent(
    incident_description,
    image_inputs,
    log_texts
):
    agent = IncidentResponseAgent()

    return agent.handle_incident(
        incident_description=incident_description,
        image_inputs=image_inputs,
        log_texts=log_texts
    )


# ------------------------------------------
# BASIC ENDPOINTS
# ------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Welcome to RunBook AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "RunBook AI API"
    }


# ------------------------------------------
# INTELLIGENT ASSISTANT MESSAGE ENDPOINT
# ------------------------------------------

@app.post("/assistant/message")
def assistant_message(request: AssistantMessageRequest):
    message = request.message.strip()

    try:
        conversation_context = ""
        if request.incident_id:
            connection = sqlite3.connect(DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                incident = connection.execute(
                    "SELECT incident_id, description, remediation_plan, status "
                    "FROM incidents WHERE incident_id = ?",
                    (request.incident_id,)
                ).fetchone()
            finally:
                connection.close()
            if incident is None:
                raise HTTPException(status_code=404, detail="Incident not found.")
            conversation_context = (
                f"ACTIVE INCIDENT ID: {incident['incident_id']}\n"
                f"INCIDENT DESCRIPTION: {incident['description']}\n"
                f"CURRENT STATUS: {incident['status']}\n"
                f"EXISTING RUNBOOK INVESTIGATION:\n{incident['remediation_plan']}\n"
                "The user is following up on this exact incident. "
                "Use this context and do not invent evidence."
            )

        classification = IntentClassifier().classify(
            message, conversation_context=conversation_context
        )
        intent = classification["intent"]

        if intent in {"technical_question", "non_technical"}:
            return {
                "intent": intent,
                "answer": classification["answer"],
                "incident_id": request.incident_id,
                "approval_required": False
            }

        if intent == "clarification":
            return {
                "intent": intent,
                "clarification": classification["clarification"],
                "incident_id": request.incident_id,
                "approval_required": False
            }

        if intent == "action_request":
            proposed_action = classification["proposed_action"] or message
            approval_id = save_approval(
                proposed_action, classification["risk_level"],
                request.incident_id
            )
            return {
                "intent": "action_request",
                "incident_id": request.incident_id,
                "approval_id": approval_id,
                "proposed_action": proposed_action,
                "risk_level": classification["risk_level"],
                "approval_required": True,
                "approval_status": "pending",
                "execution_status": "not_executed",
                "message": "Review the proposed action. No action has been executed."
            }

        if intent != "incident":
            raise HTTPException(status_code=422, detail="Unsupported intent.")

        incident_description = (
            classification["incident_description"] or message
        )

        agent = IncidentResponseAgent()
        agent_input = incident_description

        if request.incident_id:
            agent_input = (
                f"{conversation_context}\\n"
                f"FOLLOW-UP UPDATE FROM USER:\\n{message}\\n\\n"
                "Continue the investigation of the existing incident. "
                "Incorporate the new information, distinguish confirmed facts "
                "from hypotheses, and provide the next useful investigation steps."
            )

        remediation_plan = agent.handle_incident(agent_input)

        if not remediation_plan:
            raise HTTPException(
                status_code=502,
                detail="The AI agent could not generate a remediation plan."
            )

        if request.incident_id:
            incident_id = request.incident_id
            connection = sqlite3.connect(DB_PATH)
            try:
                connection.execute(
                    "UPDATE incidents SET remediation_plan = ?, status = 'analyzed' "
                    "WHERE incident_id = ?",
                    (remediation_plan, incident_id)
                )
                connection.commit()
            finally:
                connection.close()
        else:
            incident_id = str(uuid4())
            save_incident(incident_id, incident_description, remediation_plan)

        action_requested = classification["action_requested"]
        approval_id = None
        if action_requested:
            approval_id = save_approval(
                classification["proposed_action"] or message,
                classification["risk_level"],
                incident_id
            )

        return {
            "intent": "incident",
            "incident_id": incident_id,
            "description": incident_description,
            "remediation_plan": remediation_plan,
            "historical_reflection": agent.historical_reflection,
            "reflection_facts": agent.reflection_facts,
            "status": "analyzed",
            "action_requested": action_requested,
            "approval_required": action_requested,
            "proposed_action": (
                classification["proposed_action"] or message
                if action_requested else None
            ),
            "risk_level": (
                classification["risk_level"] if action_requested else None
            ),
            "approval_id": approval_id,
            "approval_status": "pending" if action_requested else "not_required",
            "execution_status": "not_executed"
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Assistant processing failed: {str(error)}"
        )



@app.get("/incidents/{incident_id}/conversation")
def get_incident_conversation(incident_id: str):
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        incident = connection.execute(
            "SELECT incident_id FROM incidents WHERE incident_id = ?",
            (incident_id,)
        ).fetchone()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found.")

        rows = connection.execute("""
            SELECT m.message_id, m.incident_id, m.role, m.text,
                   m.approval_id, m.proposed_action, m.risk_level,
                   m.created_at, a.status AS approval_status
            FROM conversation_messages m
            LEFT JOIN approvals a ON a.approval_id = m.approval_id
            WHERE m.incident_id = ?
            ORDER BY m.rowid ASC
        """, (incident_id,)).fetchall()

        return {"messages": [dict(row) for row in rows]}
    finally:
        connection.close()


@app.post("/incidents/{incident_id}/conversation")
def save_incident_conversation_message(
    incident_id: str,
    request: ConversationMessageRequest
):
    connection = sqlite3.connect(DB_PATH)
    try:
        incident = connection.execute(
            "SELECT incident_id FROM incidents WHERE incident_id = ?",
            (incident_id,)
        ).fetchone()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found.")

        if request.approval_id:
            approval = connection.execute(
                "SELECT approval_id FROM approvals WHERE approval_id = ? AND incident_id = ?",
                (request.approval_id, incident_id)
            ).fetchone()
            if approval is None:
                raise HTTPException(status_code=400, detail="Approval does not belong to this incident.")

        message_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            INSERT INTO conversation_messages
            (message_id, incident_id, role, text, approval_id,
             proposed_action, risk_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, incident_id, request.role, request.text,
            request.approval_id, request.proposed_action,
            request.risk_level, created_at
        ))
        connection.commit()
        return {"message_id": message_id, "saved": True}
    finally:
        connection.close()


@app.get("/approvals")
def list_approvals():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT * FROM approvals ORDER BY created_at DESC"
        ).fetchall()
        return {"approvals": [dict(row) for row in rows]}
    finally:
        connection.close()


@app.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, request: ApprovalDecisionRequest):
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Approval not found.")
        if row["status"] != "pending":
            raise HTTPException(status_code=409, detail="Decision already recorded.")

        connection.execute(
            "UPDATE approvals SET status = ?, decision_at = ? "
            "WHERE approval_id = ? AND status = 'pending'",
            (request.decision, datetime.now(timezone.utc).isoformat(), approval_id)
        )
        connection.commit()
        return {
            "approval_id": approval_id,
            "approval_status": request.decision,
            "execution_status": "not_executed",
            "message": "Human decision recorded. No system operation was executed."
        }
    finally:
        connection.close()


# ------------------------------------------
# TEXT-ONLY INCIDENT ENDPOINT
# ------------------------------------------

@app.post("/incidents", response_model=IncidentResponse)
def create_incident(request: IncidentRequest):

    incident_id = str(uuid4())

    try:
        agent = IncidentResponseAgent()

        remediation_plan = agent.handle_incident(
            request.description
        )

        if not remediation_plan:
            raise HTTPException(
                status_code=502,
                detail="The AI agent could not generate a remediation plan."
            )

        save_incident(
            incident_id,
            request.description,
            remediation_plan
        )

        return IncidentResponse(
            incident_id=incident_id,
            description=request.description,
            remediation_plan=remediation_plan,
            status="analyzed"
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Incident processing failed: {str(error)}"
        )


# ------------------------------------------
# MULTIMODAL INCIDENT ENDPOINT
# ------------------------------------------

@app.post(
    "/incidents/multimodal",
    response_model=IncidentResponse
)
async def create_multimodal_incident(
    description: str = Form(default=""),
    images: list[UploadFile] = File(default=[]),
    logs: list[UploadFile] = File(default=[])
):

    image_inputs = []
    log_texts = []
    total_size = 0

    try:
        if not description.strip() and not images and not logs:
            raise HTTPException(
                status_code=400,
                detail="Provide an incident description or upload evidence."
            )

        if len(images) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 screenshots are allowed."
            )

        if len(logs) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 log files are allowed."
            )

        # Process screenshots
        for image_file in images:

            filename = image_file.filename or ""
            extension = Path(filename).suffix.lower()

            if extension not in (".png", ".jpg", ".jpeg"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image format: {filename}"
                )

            image_bytes = await image_file.read()

            if not image_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"{filename} is empty."
                )

            if len(image_bytes) > MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"{filename} exceeds the 6 MB limit."
                )

            total_size += len(image_bytes)

            if extension == ".png":
                valid_image = image_bytes.startswith(
                    b"\x89PNG\r\n\x1a\n"
                )
                mime_type = "image/png"
            else:
                valid_image = image_bytes.startswith(
                    b"\xff\xd8\xff"
                )
                mime_type = "image/jpeg"

            if not valid_image:
                raise HTTPException(
                    status_code=400,
                    detail=f"{filename} is not a valid image."
                )

            image_inputs.append(
                (mime_type, image_bytes)
            )

        # Process log files
        for log_file in logs:

            filename = log_file.filename or ""
            extension = Path(filename).suffix.lower()

            if extension not in (".txt", ".log"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported log format: {filename}"
                )

            log_bytes = await log_file.read()

            if not log_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"{filename} is empty."
                )

            if len(log_bytes) > MAX_LOG_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"{filename} exceeds the 1 MB limit."
                )

            total_size += len(log_bytes)

            log_content = log_bytes.decode(
                "utf-8",
                errors="replace"
            )

            log_texts.append(
                f"Filename: {filename}\n{log_content}"
            )

        # Check total upload size
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Total evidence upload exceeds 20 MB."
            )

        incident_description = (
            description.strip()
            if description.strip()
            else "Incident submitted using uploaded evidence."
        )

        # Run synchronous Hindsight and Groq processing
        # in a worker thread to avoid event-loop conflicts.
        remediation_plan = await run_in_threadpool(
            process_multimodal_with_agent,
            incident_description,
            image_inputs,
            log_texts
        )

        if not remediation_plan:
            raise HTTPException(
                status_code=502,
                detail="AI could not generate a remediation plan."
            )

        # Save incident to SQLite
        incident_id = str(uuid4())

        save_incident(
            incident_id,
            incident_description,
            remediation_plan
        )

        return IncidentResponse(
            incident_id=incident_id,
            description=incident_description,
            remediation_plan=remediation_plan,
            status="analyzed"
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Multimodal incident processing failed: {str(error)}"
        )

    finally:
        for uploaded_file in images + logs:
            await uploaded_file.close()


# ------------------------------------------
# INCIDENT RESOLUTION ENDPOINT
# ------------------------------------------

@app.post("/incidents/{incident_id}/resolution")
def record_resolution(
    incident_id: str,
    request: ResolutionRequest
):

    memory = None

    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row

        try:
            incident = connection.execute(
                """
                SELECT * FROM incidents
                WHERE incident_id = ?
                """,
                (incident_id,)
            ).fetchone()
        finally:
            connection.close()

        if incident is None:
            raise HTTPException(
                status_code=404,
                detail="Incident ID not found."
            )

        memory = Hindsight()

        memory.track_resolution(
            incident_id=incident_id,
            incident=incident["description"],
            status=request.status,
            resolution_details=request.resolution_details
        )

        connection = sqlite3.connect(DB_PATH)

        try:
            connection.execute(
                """
                UPDATE incidents
                SET status = ?
                WHERE incident_id = ?
                """,
                (request.status, incident_id)
            )
            connection.commit()
        finally:
            connection.close()

        return {
            "success": True,
            "incident_id": incident_id,
            "resolution_status": request.status,
            "incident_description": incident["description"],
            "message": "Incident resolution recorded successfully."
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not record resolution: {str(error)}"
        )

    finally:
        if memory is not None:
            memory.close()


# ------------------------------------------
# SWAGGER FILE UPLOAD COMPATIBILITY FIX
# ------------------------------------------

def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

    schema["openapi"] = "3.0.3"

    components = schema.get(
        "components", {}
    ).get("schemas", {})

    for component in components.values():

        properties = component.get(
            "properties", {}
        )

        for prop in properties.values():

            if prop.get("type") == "array":

                items = prop.get("items", {})

                if items.get("contentMediaType") == "application/octet-stream":
                    items.pop("contentMediaType", None)
                    items["type"] = "string"
                    items["format"] = "binary"

            elif prop.get("contentMediaType") == "application/octet-stream":

                prop.pop("contentMediaType", None)
                prop["type"] = "string"
                prop["format"] = "binary"

    app.openapi_schema = schema

    return app.openapi_schema


app.openapi = custom_openapi
