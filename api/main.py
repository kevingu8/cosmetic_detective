import uuid
import json
import os
from datetime import datetime
from typing import List, Optional, Literal

import boto3
from dotenv import load_dotenv
from fastapi import (
    FastAPI, UploadFile, File, Form, HTTPException,
    Depends, Query, Header
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

# ---------------------------
# Env & config
# ---------------------------
load_dotenv()

API_KEY = os.getenv("API_KEY")  # must be set in .env
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")

# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Cosmetic Detective API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:19006",
        "http://127.0.0.1:19006",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Simple API-key auth (explicit 401s)
# ---------------------------
def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: API_KEY not set")
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return True

# ---------------------------
# MinIO / S3 client setup
# ---------------------------
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
)
BUCKET_NAME = "tickets"

# ---------------------------
# Database (SQLite + SQLAlchemy)
# ---------------------------
SQLITE_URL = "sqlite:///./app.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    brand = Column(String, nullable=False)
    category = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, index=True)  # submitted | in_review | resolved | need_more_info | rejected
    image_urls_json = Column(Text, nullable=False)       # JSON array of strings
    assigned_reviewer_id = Column(String, index=True, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    result = relationship("Result", uselist=False, back_populates="ticket", cascade="all, delete-orphan")
    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), unique=True, index=True, nullable=False)
    verdict = Column(String, nullable=False)   # authentic | inauthentic | undetermined
    rationale = Column(Text, nullable=True)
    reviewer_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=False)

    ticket = relationship("Ticket", back_populates="result")

class TicketEvent(Base):
    __tablename__ = "ticket_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), index=True, nullable=False)
    kind = Column(String, nullable=False)  # created | status_changed | claimed | unclaimed | result_added
    actor_id = Column(String, nullable=True)  # reviewer/user who did it
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    at = Column(DateTime, nullable=False)
    note = Column(Text, nullable=True)

    ticket = relationship("Ticket", back_populates="events")

Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# Pydantic schemas
# ---------------------------
StatusType = Literal["submitted", "in_review", "resolved", "need_more_info", "rejected"]
VerdictType = Literal["authentic", "inauthentic", "undetermined"]

ALLOWED_TRANSITIONS = {
    "submitted": {"in_review", "rejected", "need_more_info"},
    "in_review": {"resolved", "rejected", "need_more_info"},
    "need_more_info": {"in_review", "rejected"},
    "rejected": set(),
    "resolved": set(),
}

class TicketOut(BaseModel):
    ticket_id: str = Field(alias="id", example="c2af7fdc-62af-478c-9cc2-9081ea515afb")
    user_id: Optional[str] = Field(None, example="kev")
    brand: str = Field(..., example="Dior")
    category: str = Field(..., example="lipstick")
    notes: Optional[str] = Field("", example="Purchased in HK duty free")
    images: List[str] = Field(default_factory=list, example=["http://127.0.0.1:9000/tickets/<id>/1.jpeg"])
    status: StatusType = Field(..., example="submitted")
    assigned_reviewer_id: Optional[str] = Field(None, example="rev_001")
    claimed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        populate_by_name = True

class ResultOut(BaseModel):
    ticket_id: str = Field(..., example="c2af7fdc-62af-478c-9cc2-9081ea515afb")
    verdict: VerdictType = Field(..., example="authentic")
    rationale: Optional[str] = Field("", example="Packaging & batch code match")
    reviewer_id: Optional[str] = Field(None, example="rev_001")
    reviewed_at: datetime

class StatusUpdateIn(BaseModel):
    status: StatusType = Field(..., example="in_review")

class ResultIn(BaseModel):
    verdict: VerdictType = Field(..., example="authentic")
    rationale: Optional[str] = Field("", example="Hologram and font spacing are correct")
    reviewer_id: Optional[str] = Field(None, example="rev_001")

class ClaimIn(BaseModel):
    reviewer_id: str = Field(..., example="rev_001")

class EventOut(BaseModel):
    id: int
    kind: str
    actor_id: Optional[str]
    from_status: Optional[str]
    to_status: Optional[str]
    at: datetime
    note: Optional[str]

# ---------------------------
# Helpers
# ---------------------------
def record_event(
    db: Session,
    ticket_id: str,
    kind: str,
    actor_id: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    note: Optional[str] = None,
):
    e = TicketEvent(
        ticket_id=ticket_id,
        kind=kind,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        at=datetime.utcnow(),
        note=note,
    )
    db.add(e)
    db.commit()

# ---------------------------
# Health routes
# ---------------------------
@app.get("/", tags=["system"], summary="Root alive check")
def root():
    return {"status": "ok"}

@app.get("/health", tags=["system"], summary="Health check")
def health_check():
    return {"status": "ok"}

# ---------------------------
# POST /tickets  (create with uploads)
# ---------------------------
@app.post(
    "/tickets",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Create a ticket with images"
)
async def create_ticket(
    brand: str = Form(...),
    category: str = Form(...),
    notes: str = Form(""),
    images: List[UploadFile] = File(...),
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not 1 <= len(images) <= 5:
        raise HTTPException(status_code=400, detail="Must upload 1–5 images")

    ticket_id = str(uuid.uuid4())
    image_urls: List[str] = []

    for img in images:
        filename = img.filename or "image.jpg"
        key = f"{ticket_id}/{filename}"
        try:
            s3_client.upload_fileobj(img.file, BUCKET_NAME, key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        url = f"{MINIO_ENDPOINT}/{BUCKET_NAME}/{key}".replace(":9000", ":9000")  # keep as-is for local
        image_urls.append(url)

    now = datetime.utcnow()
    t = Ticket(
        id=ticket_id,
        user_id=user_id,
        brand=brand,
        category=category,
        notes=notes,
        status="submitted",
        image_urls_json=json.dumps(image_urls),
        assigned_reviewer_id=None,
        claimed_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    record_event(db, ticket_id, "created", actor_id=user_id, to_status="submitted")

    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# GET /tickets/{id}
# ---------------------------
@app.get(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Get a ticket by ID"
)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# GET /tickets  (list with optional filters)
# ---------------------------
@app.get(
    "/tickets",
    response_model=List[TicketOut],
    tags=["tickets"],
    summary="List tickets"
)
def list_tickets(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[StatusType] = Query(None, description="Filter by status"),
    unassigned: Optional[bool] = Query(None, description="Only those with no assigned reviewer"),
    reviewer_id: Optional[str] = Query(None, description="Filter by assigned reviewer"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    db: Session = Depends(get_db)
):
    q = db.query(Ticket)
    if user_id:
        q = q.filter(Ticket.user_id == user_id)
    if status:
        q = q.filter(Ticket.status == status)
    if unassigned is True:
        q = q.filter(Ticket.assigned_reviewer_id.is_(None))
    if reviewer_id:
        q = q.filter(Ticket.assigned_reviewer_id == reviewer_id)
    q = q.order_by(Ticket.created_at.desc()).limit(limit)

    items = []
    for t in q.all():
        items.append(TicketOut(
            id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
            images=json.loads(t.image_urls_json), status=t.status,
            assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
            created_at=t.created_at, updated_at=t.updated_at
        ))
    return items

# ---------------------------
# POST /tickets/{id}/claim  (requires API key)
# ---------------------------
@app.post(
    "/tickets/{ticket_id}/claim",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Claim a ticket for review"
)
def claim_ticket(
    ticket_id: str,
    payload: ClaimIn,
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t.assigned_reviewer_id and t.assigned_reviewer_id != payload.reviewer_id:
        raise HTTPException(status_code=409, detail="Ticket already claimed by another reviewer")
    prev_status = t.status
    if t.status in ("submitted", "need_more_info"):
        t.status = "in_review"
    t.assigned_reviewer_id = payload.reviewer_id
    t.claimed_at = datetime.utcnow()
    t.updated_at = datetime.utcnow()
    db.add(t)
    db.commit()
    db.refresh(t)

    record_event(db, ticket_id, "claimed", actor_id=payload.reviewer_id, from_status=prev_status, to_status=t.status)

    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# POST /tickets/{id}/unclaim  (requires API key)
# ---------------------------
@app.post(
    "/tickets/{ticket_id}/unclaim",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Unclaim a ticket"
)
def unclaim_ticket(
    ticket_id: str,
    payload: ClaimIn,
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not t.assigned_reviewer_id:
        raise HTTPException(status_code=400, detail="Ticket is not claimed")
    if t.assigned_reviewer_id != payload.reviewer_id:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can unclaim")

    t.assigned_reviewer_id = None
    t.claimed_at = None
    t.updated_at = datetime.utcnow()
    db.add(t)
    db.commit()
    db.refresh(t)

    record_event(db, ticket_id, "unclaimed", actor_id=payload.reviewer_id)

    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# PATCH /tickets/{id}/status  (requires API key, enforces transitions)
# ---------------------------
@app.patch(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Update ticket status (with transition rules)"
)
def update_status(
    ticket_id: str,
    payload: StatusUpdateIn,
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    from_status = t.status
    to_status = payload.status

    if to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Illegal transition: {from_status} → {to_status}"
        )

    t.status = to_status
    t.updated_at = datetime.utcnow()
    db.add(t)
    db.commit()
    db.refresh(t)

    record_event(db, ticket_id, "status_changed", from_status=from_status, to_status=to_status)

    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        assigned_reviewer_id=t.assigned_reviewer_id, claimed_at=t.claimed_at,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# POST /tickets/{id}/result  (requires API key)
# ---------------------------
@app.post(
    "/tickets/{ticket_id}/result",
    response_model=ResultOut,
    tags=["results"],
    summary="Create result for ticket (marks resolved)"
)
def create_result(
    ticket_id: str,
    payload: ResultIn,
    db: Session = Depends(get_db),
    _=Depends(require_api_key),
):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.result is not None:
        raise HTTPException(status_code=400, detail="Result already exists for this ticket")

    r = Result(
        ticket_id=ticket_id,
        verdict=payload.verdict,
        rationale=payload.rationale or "",
        reviewer_id=payload.reviewer_id,
        reviewed_at=datetime.utcnow(),
    )
    prev_status = t.status
    t.status = "resolved"
    t.updated_at = datetime.utcnow()

    db.add_all([r, t])
    db.commit()
    db.refresh(r)

    record_event(db, ticket_id, "result_added", actor_id=payload.reviewer_id, from_status=prev_status, to_status="resolved")

    return ResultOut(
        ticket_id=r.ticket_id, verdict=r.verdict, rationale=r.rationale,
        reviewer_id=r.reviewer_id, reviewed_at=r.reviewed_at
    )

# ---------------------------
# GET /tickets/{id}/result
# ---------------------------
@app.get(
    "/tickets/{ticket_id}/result",
    response_model=ResultOut,
    tags=["results"],
    summary="Get result for ticket"
)
def get_result(ticket_id: str, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t.result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    r = t.result
    return ResultOut(
        ticket_id=r.ticket_id, verdict=r.verdict, rationale=r.rationale,
        reviewer_id=r.reviewer_id, reviewed_at=r.reviewed_at
    )

# ---------------------------
# GET /tickets/{id}/events
# ---------------------------
@app.get(
    "/tickets/{ticket_id}/events",
    response_model=List[EventOut],
    tags=["tickets"],
    summary="List audit events for a ticket"
)
def list_events(ticket_id: str, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    events = (
        db.query(TicketEvent)
          .filter(TicketEvent.ticket_id == ticket_id)
          .order_by(TicketEvent.at.asc())
          .all()
    )
    return [
        EventOut(
            id=e.id, kind=e.kind, actor_id=e.actor_id,
            from_status=e.from_status, to_status=e.to_status,
            at=e.at, note=e.note
        ) for e in events
    ]
