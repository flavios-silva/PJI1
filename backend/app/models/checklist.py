import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Text, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import enum


class ChecklistPhase(str, enum.Enum):
    ENTRADA = "ENTRADA"
    FECHAMENTO = "FECHAMENTO"


class ChecklistStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    phase: Mapped[ChecklistPhase] = mapped_column(SAEnum(ChecklistPhase), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    department: Mapped["Department"] = relationship("Department", back_populates="templates")
    items: Mapped[list["ChecklistItemTemplate"]] = relationship(
        "ChecklistItemTemplate", back_populates="template", order_by="ChecklistItemTemplate.order_index"
    )
    daily_checklists: Mapped[list["DailyChecklist"]] = relationship("DailyChecklist", back_populates="template")


class ChecklistItemTemplate(Base):
    __tablename__ = "checklist_item_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    requires_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    template: Mapped["ChecklistTemplate"] = relationship("ChecklistTemplate", back_populates="items")
    instances: Mapped[list["ChecklistItem"]] = relationship("ChecklistItem", back_populates="item_template")


class DailyChecklist(Base):
    __tablename__ = "daily_checklists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ChecklistStatus] = mapped_column(SAEnum(ChecklistStatus), default=ChecklistStatus.IN_PROGRESS)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_daily_checklists_employee_date", "employee_id", "date"),
        Index("ix_daily_checklists_status", "status"),
        Index("ix_daily_checklists_date", "date"),
        Index("ix_daily_checklists_tmpl_emp_date", "template_id", "employee_id", "date", unique=True),
    )

    template: Mapped["ChecklistTemplate"] = relationship("ChecklistTemplate", back_populates="daily_checklists")
    employee: Mapped["User"] = relationship("User", foreign_keys=[employee_id], back_populates="daily_checklists")
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_id])
    items: Mapped[list["ChecklistItem"]] = relationship("ChecklistItem", back_populates="daily_checklist", cascade="all, delete-orphan")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_checklist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_checklists.id"), nullable=False)
    item_template_id: Mapped[int] = mapped_column(ForeignKey("checklist_item_templates.id"), nullable=False)
    status: Mapped[ItemStatus] = mapped_column(SAEnum(ItemStatus), default=ItemStatus.PENDING)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    daily_checklist: Mapped["DailyChecklist"] = relationship("DailyChecklist", back_populates="items")
    item_template: Mapped["ChecklistItemTemplate"] = relationship("ChecklistItemTemplate", back_populates="instances")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id], back_populates="notifications")
