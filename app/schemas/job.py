import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.models.job import JobStatus
from app.schemas.certificate import RecipientIn


class JobCreate(BaseModel):
    event_name: str = Field(min_length=1, max_length=255)
    issue_date: date
    recipients: list[RecipientIn] = Field(
        min_length=1, max_length=get_settings().max_recipients_per_job
    )


class JobCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    id: uuid.UUID
    event_name: str
    issue_date: date
    status: JobStatus
    total_count: int
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None = None
    event_name: str
    issue_date: date
    status: JobStatus
    total_count: int
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime
    completed_at: datetime | None = None
