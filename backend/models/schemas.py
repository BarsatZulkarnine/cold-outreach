import json
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship, DeclarativeBase
from pydantic import BaseModel


class Base(DeclarativeBase):
    pass


# ─── SQLAlchemy Models ───────────────────────────────────────────────────────

class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)           # "google_maps" | "linkedin"
    company_name = Column(String, nullable=False)
    company_website = Column(String, nullable=True)
    company_size = Column(String, nullable=True)      # e.g. "11-50"
    tech_stack = Column(Text, nullable=True)          # JSON list stored as text
    contact_name = Column(String, nullable=True)
    contact_title = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    has_open_roles = Column(Boolean, default=False)
    open_role_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="discovered")
    # status flow: discovered → message_generated → approved → sent → replied → meeting → rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="target", cascade="all, delete-orphan")

    def get_tech_stack(self) -> list:
        if not self.tech_stack:
            return []
        try:
            return json.loads(self.tech_stack)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tech_stack(self, stack: list):
        self.tech_stack = json.dumps(stack)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    channel = Column(String, nullable=False)          # "email" | "linkedin"
    subject = Column(String, nullable=True)           # email only
    body = Column(Text, nullable=False)
    status = Column(String, default="pending_approval")
    # status: pending_approval | approved | sent | rejected
    generated_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    scheduled_send_at = Column(DateTime, nullable=True)  # scheduled delivery time (email only)
    opened = Column(Boolean, default=False)           # email only
    replied = Column(Boolean, default=False)
    follow_up_sent = Column(Boolean, default=False)
    follow_up_sent_at = Column(DateTime, nullable=True)

    target = relationship("Target", back_populates="messages")


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class TargetBase(BaseModel):
    source: str
    company_name: str
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    linkedin_url: Optional[str] = None
    has_open_roles: bool = False
    open_role_url: Optional[str] = None
    notes: Optional[str] = None
    status: str = "discovered"


class TargetCreate(TargetBase):
    pass


class TargetUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    linkedin_url: Optional[str] = None
    has_open_roles: Optional[bool] = None
    open_role_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    company_size: Optional[str] = None


class TargetOut(TargetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    target_id: int
    channel: str
    subject: Optional[str] = None
    body: str
    status: str = "pending_approval"


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    body: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    replied: Optional[bool] = None
    opened: Optional[bool] = None


class MessageOut(MessageBase):
    id: int
    generated_at: datetime
    sent_at: Optional[datetime] = None
    scheduled_send_at: Optional[datetime] = None
    opened: bool
    replied: bool
    follow_up_sent: bool
    follow_up_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TargetWithMessages(TargetOut):
    messages: list[MessageOut] = []


class StatsOut(BaseModel):
    total_discovered: int
    emails_sent: int
    linkedin_sent: int
    replied: int
    meetings: int
    reply_rate: float
    by_status: dict


class GenerateMessageRequest(BaseModel):
    channel: str  # "email" | "linkedin"


class BatchGenerateRequest(BaseModel):
    target_ids: list[int]
    channel: str


class ApproveMessageRequest(BaseModel):
    body: str
    subject: Optional[str] = None


class BatchSendRequest(BaseModel):
    message_ids: list[int]


class DiscoverMapsRequest(BaseModel):
    queries: Optional[list[str]] = None
    max_per_query: int = 20


class DiscoverLinkedInRequest(BaseModel):
    search_query: str
    max_results: int = 15
