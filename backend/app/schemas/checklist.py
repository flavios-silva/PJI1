import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field
from app.models.checklist import ChecklistStatus, ItemStatus, ChecklistPhase


class DepartmentOut(BaseModel):
    id: int
    name: str
    display_name: str
    icon: str | None
    color: str | None
    model_config = {"from_attributes": True}


class ItemTemplateOut(BaseModel):
    id: int
    title: str
    requires_photo: bool
    order_index: int
    model_config = {"from_attributes": True}


class TemplateSummaryOut(BaseModel):
    id: int
    department_id: int
    phase: ChecklistPhase
    name: str
    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    id: int
    department_id: int
    phase: ChecklistPhase
    name: str
    items: list[ItemTemplateOut] = []
    model_config = {"from_attributes": True}


class ChecklistItemOut(BaseModel):
    id: uuid.UUID
    item_template_id: int
    status: ItemStatus
    photo_url: str | None
    notes: str | None
    completed_at: datetime | None
    item_template: ItemTemplateOut
    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    status: ItemStatus
    notes: str | None = Field(None, max_length=1000)


class DailyChecklistCreate(BaseModel):
    template_id: int
    date: date


class DailyChecklistOut(BaseModel):
    id: uuid.UUID
    template_id: int
    employee_id: uuid.UUID
    date: date
    status: ChecklistStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewer_id: uuid.UUID | None
    review_notes: str | None
    submission_notes: str | None = None
    created_at: datetime
    items: list[ChecklistItemOut] = []
    template: TemplateSummaryOut | None = None
    employee_name: str | None = None
    employee_avatar_url: str | None = None
    department_name: str | None = None
    reviewer_name: str | None = None
    progress: int = 0  # 0-100

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    department_id: int
    phase: ChecklistPhase

class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)

class TemplateItemCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    requires_photo: bool = False
    order_index: int | None = None

class TemplateItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    requires_photo: bool | None = None
    order_index: int | None = None

class ChecklistNotesUpdate(BaseModel):
    submission_notes: str | None = Field(None, max_length=2000)


class ReviewRequest(BaseModel):
    status: ChecklistStatus
    notes: str | None = Field(None, max_length=1000)


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    is_read: bool
    reference_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=80)
    icon: str | None = None
    color: str | None = None


class DepartmentUpdate(BaseModel):
    display_name: str | None = None
    icon: str | None = None
    color: str | None = None
