import uuid
import json
from datetime import datetime
from typing import List, Optional, Literal

import boto3
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, String, DateTime, Text, Integer, ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Cosmetic Detective API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# MinIO / S3 client setup
# ---------------------------
s3_client = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",  # MinIO API
    aws_access_key_id="admin",             # match docker run env
    aws_secret_access_key="password123",   # match docker run env
    region_name="us-east-1"                # dummy region
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
    user_id = Column(String, index=True, nullable=True)  # optional until auth is wired
    brand = Column(String, nullable=False)
    category = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, index=True)  # submitted | in_review | resolved | need_more_info | rejected
    image_urls_json = Column(Text, nullable=False)       # store list as JSON text
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    result = relationship("Result", uselist=False, back_populates="ticket", cascade="all, delete-orphan")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), unique=True, index=True, nullable=False)
    verdict = Column(String, nullable=False)   # authentic | inauthentic | undetermined
    rationale = Column(Text, nullable=True)
    reviewer_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=False)

    ticket = relationship("Ticket", back_populates="result")

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

class TicketOut(BaseModel):
    ticket_id: str = Field(alias="id")
    user_id: Optional[str] = None
    brand: str
    category: str
    notes: Optional[str] = ""
    images: List[str]
    status: StatusType
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class ResultOut(BaseModel):
    ticket_id: str
    verdict: VerdictType
    rationale: Optional[str] = ""
    reviewer_id: Optional[str] = None
    reviewed_at: datetime

class StatusUpdateIn(BaseModel):
    status: StatusType

class ResultIn(BaseModel):
    verdict: VerdictType
    rationale: Optional[str] = ""
    reviewer_id: Optional[str] = None


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

    # upload each image to MinIO
    for img in images:
        filename = img.filename or "image.jpg"
        key = f"{ticket_id}/{filename}"
        try:
            s3_client.upload_fileobj(img.file, BUCKET_NAME, key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        url = f"http://127.0.0.1:9000/{BUCKET_NAME}/{key}"
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
        created_at=now,
        updated_at=now,
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    return TicketOut(
        id=t.id,
        user_id=t.user_id,
        brand=t.brand,
        category=t.category,
        notes=t.notes,
        images=json.loads(t.image_urls_json),
        status=t.status, created_at=t.created_at, updated_at=t.updated_at
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
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    db: Session = Depends(get_db)
):
    q = db.query(Ticket)
    if user_id:
        q = q.filter(Ticket.user_id == user_id)
    if status:
        q = q.filter(Ticket.status == status)
    q = q.order_by(Ticket.created_at.desc()).limit(limit)

    items = []
    for t in q.all():
        items.append(TicketOut(
            id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
            images=json.loads(t.image_urls_json), status=t.status,
            created_at=t.created_at, updated_at=t.updated_at
        ))
    return items

# ---------------------------
# PATCH /tickets/{id}/status
# ---------------------------
@app.patch(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    tags=["tickets"],
    summary="Update ticket status"
)
def update_status(ticket_id: str, payload: StatusUpdateIn, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # (Optional) enforce allowed transitions here
    t.status = payload.status
    t.updated_at = datetime.utcnow()
    db.add(t)
    db.commit()
    db.refresh(t)

    return TicketOut(
        id=t.id, user_id=t.user_id, brand=t.brand, category=t.category, notes=t.notes,
        images=json.loads(t.image_urls_json), status=t.status,
        created_at=t.created_at, updated_at=t.updated_at
    )

# ---------------------------
# POST /tickets/{id}/result
# ---------------------------
@app.post(
    "/tickets/{ticket_id}/result",
    response_model=ResultOut,
    tags=["results"],
    summary="Create result for ticket"
)
def create_result(ticket_id: str, payload: ResultIn, db: Session = Depends(get_db)):
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
    # when a result is posted, mark ticket resolved (simple rule)
    t.status = "resolved"
    t.updated_at = datetime.utcnow()

    db.add_all([r, t])
    db.commit()
    db.refresh(r)

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
